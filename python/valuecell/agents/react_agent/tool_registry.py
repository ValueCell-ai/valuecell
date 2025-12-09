from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any, Optional, Type

from loguru import logger
from pydantic import BaseModel, create_model


CallableType = Callable[..., Any]


class ToolDefinition(BaseModel):
    """Describe a callable tool with metadata for planning and execution."""

    tool_id: str
    name: str
    description: str
    args_schema: Type[BaseModel] | None
    func: CallableType
    is_agent: bool = False

    class Config:
        arbitrary_types_allowed = True


class ToolRegistry:
    """Registry that keeps tool metadata and offers unified execution."""

    def __init__(self) -> None:
        self._registry: dict[str, ToolDefinition] = {}

    def register(
        self,
        tool_id: str,
        func: CallableType,
        description: str,
        *,
        args_schema: Type[BaseModel] | None = None,
        name: Optional[str] = None,
        is_agent: bool = False,
    ) -> None:
        """Register a callable tool with optional schema reflection."""
        if tool_id in self._registry:
            raise ValueError(f"Tool '{tool_id}' already registered")

        schema = args_schema or self._infer_schema(func)
        tool_name = name or tool_id.replace("_", " ").title()
        definition = ToolDefinition(
            tool_id=tool_id,
            name=tool_name,
            description=description,
            args_schema=schema,
            func=func,
            is_agent=is_agent,
        )
        self._registry[tool_id] = definition
        logger.info("Tool registered: {tool_id}", tool_id=tool_id)

    def get_tool(self, tool_id: str) -> ToolDefinition:
        """Return the tool definition or raise if missing."""
        try:
            return self._registry[tool_id]
        except KeyError as exc:
            raise ValueError(f"Tool '{tool_id}' not found") from exc

    async def execute(
        self,
        tool_id: str,
        tool_args: dict[str, Any] | None = None,
        *,
        runtime_args: dict[str, Any] | None = None,
    ) -> Any:
        """Execute a registered tool with validated arguments."""
        tool_def = self.get_tool(tool_id)
        args = tool_args or {}
        params = self._validate_args(tool_def.args_schema, args)
        if runtime_args:
            params.update(self._filter_runtime_args(tool_def.func, runtime_args))

        result = await self._call(tool_def.func, params)
        return result

    def list_tools(self) -> list[ToolDefinition]:
        """Return registered tools sorted by identifier."""
        return [self._registry[k] for k in sorted(self._registry.keys())]

    def get_prompt_context(self) -> str:
        """Generate a planner-friendly summary of available tools."""
        lines: list[str] = ["Available Tools:"]

        def _json_type_to_py(t: Any, prop: dict) -> str:
            # Map JSON schema types to concise Python-like types
            if isinstance(t, list):
                # e.g., ["string","null"] -> Optional[str]
                non_null = [x for x in t if x != "null"]
                if len(non_null) == 1:
                    return f"Optional[{_json_type_to_py(non_null[0], prop)}]"
                return "Any"
            if t == "string":
                return "str"
            if t == "integer":
                return "int"
            if t == "number":
                return "float"
            if t == "boolean":
                return "bool"
            if t == "object":
                return "dict"
            if t == "array":
                items = prop.get("items") or {}
                item_type = items.get("type")
                if not item_type and items.get("anyOf"):
                    # try first anyOf type
                    ao = items.get("anyOf")[0]
                    item_type = ao.get("type")
                py_item = _json_type_to_py(item_type or "any", items)
                return f"List[{py_item}]"
            if t == "null":
                return "None"
            return "Any"

        for tool in self.list_tools():
            # Tool header
            lines.append(f"- {tool.tool_id}: {tool.description}")

            # Build concise signature from args_schema when available
            if tool.args_schema:
                try:
                    schema = tool.args_schema.model_json_schema()
                    props = schema.get("properties", {})
                except Exception:
                    props = {}

                if not props:
                    lines.append("  Arguments: ()")
                    continue

                parts: list[str] = []
                for name, prop in props.items():
                    ptype = prop.get("type")
                    # handle 'anyOf' at property level (e.g., [string, null])
                    if not ptype and prop.get("anyOf"):
                        # pick first non-null
                        types = [p.get("type") for p in prop.get("anyOf")]
                        ptype = types if types else None

                    py_type = _json_type_to_py(ptype or "any", prop)
                    default = prop.get("default")
                    if default is not None:
                        # represent strings with quotes, others as-is
                        if isinstance(default, str):
                            parts.append(f"{name}: {py_type} = '{default}'")
                        else:
                            parts.append(f"{name}: {py_type} = {default}")
                    else:
                        parts.append(f"{name}: {py_type}")

                sig = ", ".join(parts)
                lines.append(f"  Arguments: ({sig})")
            else:
                lines.append("  Arguments: ()")

        return "\n".join(lines)

    @staticmethod
    def _validate_args(
        schema: Type[BaseModel] | None, args: dict[str, Any]
    ) -> dict[str, Any]:
        if schema is None:
            return dict(args)
        validated = schema(**args)
        return validated.model_dump()

    @staticmethod
    def _filter_runtime_args(func: CallableType, runtime_args: dict[str, Any]) -> dict[str, Any]:
        try:
            signature = inspect.signature(func)
        except (TypeError, ValueError):
            return dict(runtime_args)

        accepted: dict[str, Any] = {}
        for key, value in runtime_args.items():
            if key in signature.parameters:
                accepted[key] = value
        return accepted

    @staticmethod
    async def _call(func: CallableType, params: dict[str, Any]) -> Any:
        try:
            result = func(**params)
        except TypeError:
            if params:
                result = func(params)
            else:
                result = func()
        return await ToolRegistry._maybe_await(result)

    @staticmethod
    async def _maybe_await(value: Any) -> Any:
        if inspect.isawaitable(value):
            return await value
        return value

    @staticmethod
    def _infer_schema(func: CallableType) -> Type[BaseModel] | None:
        try:
            signature = inspect.signature(func)
        except (TypeError, ValueError):
            return None

        fields: dict[str, tuple[type[Any], Any]] = {}
        for name, param in signature.parameters.items():
            if name in {"self", "cls"}:
                continue
            if param.kind in {inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD}:
                return None
            annotation = (
                param.annotation
                if param.annotation is not inspect.Signature.empty
                else Any
            )
            default = (
                param.default
                if param.default is not inspect.Signature.empty
                else ...
            )
            fields[name] = (annotation, default)

        if not fields:
            return None

        model_name = f"{func.__name__.capitalize()}Args"
        return create_model(model_name, **fields)


registry = ToolRegistry()

__all__ = ["ToolDefinition", "ToolRegistry", "registry"]
