"""Planner: create execution plans from user input.

This module implements the ExecutionPlanner which uses an LLM-based
planning agent to convert a user request into a structured
`ExecutionPlan` consisting of `Task` objects. The planner supports
Human-in-the-Loop flows by emitting `UserInputRequest` objects (backed by
an asyncio.Event) when the planner requires clarification.

The planner is intentionally thin: it delegates reasoning to an AI agent
and performs JSON parsing/validation of the planner's output.
"""

import asyncio
from datetime import datetime
from typing import Callable, List, Optional

from a2a.types import AgentCard
from agno.agent import Agent
from agno.db.in_memory import InMemoryDb
from loguru import logger

import valuecell.utils.model as model_utils_mod
from valuecell.core.agent.connect import RemoteConnections
from valuecell.core.task.models import Task, TaskStatus
from valuecell.core.types import UserInput
from valuecell.utils import generate_uuid
from valuecell.utils.env import agent_debug_mode_enabled
from valuecell.utils.uuid import generate_conversation_id

from .models import ExecutionPlan, PlannerInput, PlannerResponse
from .prompts import (
    PLANNER_EXPECTED_OUTPUT,
    PLANNER_INSTRUCTION,
)


class UserInputRequest:
    """
    Represents a request for user input during plan creation or execution.

    This class uses asyncio.Event to enable non-blocking waiting for user responses
    in the Human-in-the-Loop workflow.
    """

    def __init__(self, prompt: str):
        """Create a new request object for planner-driven user input.

        Args:
            prompt: Human-readable prompt describing the information needed.
        """
        self.prompt = prompt
        self.response: Optional[str] = None
        self.event = asyncio.Event()

    async def wait_for_response(self) -> str:
        """Block until a response is provided and return it.

        This is an awaitable helper designed to be used by planner code that
        wants to pause execution until the external caller supplies the
        requested value via `provide_response`.
        """
        await self.event.wait()
        return self.response

    def provide_response(self, response: str):
        """Supply the user's response and wake any waiter.

        Args:
            response: The text provided by the user to satisfy the prompt.
        """
        self.response = response
        self.event.set()


class ExecutionPlanner:
    """
    Creates execution plans by analyzing user input and determining appropriate agent tasks.

    This planner uses AI to understand user requests and break them down into
    executable tasks that can be handled by specific agents. It supports
    Human-in-the-Loop interactions when additional clarification is needed.
    """

    def __init__(
        self,
        agent_connections: RemoteConnections,
    ):
        self.agent_connections = agent_connections
        # Lazy initialize agent to avoid startup failures when API keys are missing
        self.agent = None

    def _get_or_init_agent(self) -> Optional[Agent]:
        """Create the planning agent on first use.

        Returns the initialized Agent or None if initialization fails.
        """
        if self.agent is not None:
            return self.agent

        try:
            # Fetch model via utils module reference so tests can monkeypatch it reliably
            model = model_utils_mod.get_model_for_agent("super_agent")
            self.agent = Agent(
                model=model,
                tools=[
                    # TODO: enable UserControlFlowTools when stable
                    # UserControlFlowTools(),
                    self.tool_get_agent_description,
                    self.tool_get_enabled_agents,
                ],
                debug_mode=agent_debug_mode_enabled(),
                instructions=[PLANNER_INSTRUCTION],
                # output format
                markdown=False,
                output_schema=PlannerResponse,
                expected_output=PLANNER_EXPECTED_OUTPUT,
                use_json_mode=model_utils_mod.model_should_use_json_mode(model),
                # context
                db=InMemoryDb(),
                add_datetime_to_context=True,
                add_history_to_context=True,
                num_history_runs=5,
                read_chat_history=True,
                enable_session_summaries=True,
            )
            return self.agent
        except Exception as exc:
            logger.exception("Failed to initialize planner agent: %s", exc)
            self.agent = None
            return None

    async def create_plan(
        self,
        user_input: UserInput,
        user_input_callback: Callable,
        thread_id: str,
    ) -> ExecutionPlan:
        """
        Create an execution plan from user input.

        This method orchestrates the planning agent run and returns a
        validated `ExecutionPlan` instance. The optional `user_input_callback`
        is called whenever the planner requests clarification; the callback
        should accept a `UserInputRequest` and arrange for the user's answer to
        be provided (typically by calling `UserInputRequest.provide_response`).

        Args:
            user_input: The user's request to be planned.
            user_input_callback: Async callback invoked with
                `UserInputRequest` instances when clarification is required.

        Returns:
            ExecutionPlan: A structured plan with tasks for execution.
        """
        conversation_id = user_input.meta.conversation_id
        plan = ExecutionPlan(
            plan_id=generate_uuid("plan"),
            conversation_id=conversation_id,
            user_id=user_input.meta.user_id,
            orig_query=user_input.query,  # Store the original query
            created_at=datetime.now().isoformat(),
        )

        # Analyze input and create appropriate tasks
        tasks, guidance_message = await self._analyze_input_and_create_tasks(
            user_input,
            conversation_id,
            user_input_callback,
            thread_id,
        )
        plan.tasks = tasks
        plan.guidance_message = guidance_message

        return plan

    async def _analyze_input_and_create_tasks(
        self,
        user_input: UserInput,
        conversation_id: str,
        user_input_callback: Callable,
        thread_id: str,
    ) -> tuple[List[Task], Optional[str]]:
        """
        Analyze user input and produce a list of `Task` objects.

        The planner delegates reasoning to an LLM agent which must output a
        JSON document conforming to `PlannerResponse`. If the planner pauses to
        request user input, the provided `user_input_callback` will be
        invoked for each requested field.

        Args:
            user_input: The original user input to analyze.
            conversation_id: Conversation this planning belongs to.
            user_input_callback: Async callback used for Human-in-the-Loop.

        Returns:
            A tuple of (list of Task objects, optional guidance message).
            If plan is inadequate, returns empty list with guidance message.
        """
        # Execute planning with the agent (lazy init)
        agent = self._get_or_init_agent()
        if agent is None:
            return [], (
                "Planner is unavailable: failed to initialize model/provider. "
                "Please configure a valid API key or provider settings and retry."
            )

        # Be robust if model attributes are unavailable
        try:
            model = agent.model
            model_description = f"{model.id} (via {model.provider})"
        except Exception:
            model_description = "unknown model/provider"
        try:
            run_response = agent.run(
                PlannerInput(
                    target_agent_name=user_input.target_agent_name,
                    query=user_input.query,
                ),
                session_id=conversation_id,
                user_id=user_input.meta.user_id,
            )
        except Exception as exc:
            logger.exception("Planner run failed: %s", exc)
            return [], (
                f"Planner encountered an error during execution: {exc}. "
                f"Please check the capabilities of your model `{model_description}` and try again later."
            )

        # Handle user input requests through Human-in-the-Loop workflow
        while run_response.is_paused:
            for tool in run_response.tools_requiring_user_input:
                input_schema = tool.user_input_schema

                for field in input_schema:
                    # Use callback for async user input
                    # TODO: prompt options if available
                    request = UserInputRequest(field.description)
                    await user_input_callback(request)
                    user_value = await request.wait_for_response()
                    field.value = user_value

            # Continue agent execution with updated inputs
            run_response = agent.continue_run(
                # TODO: rollback to `run_id=run_response.run_id` when bug fixed by Agno
                run_response=run_response,
                updated_tools=run_response.tools,
            )

            if not run_response.is_paused:
                break

        # Parse planning result and create tasks
        plan_raw = run_response.content
        if not isinstance(plan_raw, PlannerResponse):
            return (
                [],
                (
                    f"Planner produced a malformed response: `{plan_raw}`. "
                    f"Please check the capabilities of your model `{model_description}` and try again later."
                ),
            )
        logger.info(f"Planner produced plan: {plan_raw}")

        # Check if plan is inadequate or has no tasks
        guidance_message = plan_raw.guidance_message or plan_raw.reason
        if not plan_raw.adequate or not plan_raw.tasks:
            # Use guidance_message from planner, or fall back to reason
            logger.info(f"Planner needs user guidance: {guidance_message}")
            return [], guidance_message  # Return empty task list with guidance

        planable_cards = self.agent_connections.get_planable_agent_cards()
        planable_agent_names = set(planable_cards.keys())
        invalid_agents = {
            t.agent_name
            for t in plan_raw.tasks
            if t.agent_name not in planable_agent_names
        }
        if invalid_agents:
            available_agents = (
                ", ".join(sorted(planable_agent_names))
                if planable_agent_names
                else "none"
            )
            invalid_list = ", ".join(sorted(invalid_agents))
            guidance_message = (
                "Planner selected unsupported agent(s):"
                f" {invalid_list}."
                f" Maybe the chosen model `{model_description}` hallucinated."
            )
            logger.warning(
                "Planner proposed unsupported agents: %s (available: %s)",
                invalid_list,
                available_agents,
            )
            return [], guidance_message

        # Create tasks from planner response
        tasks = []
        for t in plan_raw.tasks:
            tasks.append(
                self._create_task(
                    t,
                    user_input.meta.user_id,
                    conversation_id=user_input.meta.conversation_id,
                    thread_id=thread_id,
                    handoff_from_super_agent=(not user_input.target_agent_name),
                )
            )

        return tasks, guidance_message  # Return tasks with no guidance message

    def _create_task(
        self,
        task_brief,
        user_id: str,
        conversation_id: str | None = None,
        thread_id: str | None = None,
        handoff_from_super_agent: bool = False,
    ) -> Task:
        """
        Create a new task for the specified agent.

        Args:
            conversation_id: Conversation this task belongs to
            user_id: User who requested this task
            agent_name: Name of the agent to execute the task
            query: Query/prompt for the agent
            pattern: Execution pattern (once or recurring)
            schedule_config: Schedule configuration for recurring tasks

        Returns:
            Task: Configured task ready for execution.
        """
        # task_brief is a _TaskBrief model instance

        # Reuse parent thread_id across subagent handoff.
        # When handing off from Super Agent, a NEW conversation_id is created for the subagent,
        # but we PRESERVE the parent thread_id to correlate the entire flow as one interaction.
        if handoff_from_super_agent:
            conversation_id = generate_conversation_id()
            # Do NOT override thread_id here (keep the parent's thread_id per Spec A)

        return Task(
            conversation_id=conversation_id,
            thread_id=thread_id,
            user_id=user_id,
            agent_name=task_brief.agent_name,
            status=TaskStatus.PENDING,
            title=task_brief.title,
            query=task_brief.query,
            pattern=task_brief.pattern,
            schedule_config=task_brief.schedule_config,
            handoff_from_super_agent=handoff_from_super_agent,
        )

    def tool_get_agent_description(self, agent_name: str) -> str:
        """
        Get the capabilities description of a specified agent by name.

        This function returns capability information for agents that can be used
        in the planning process to determine if an agent is suitable for a task.

        Args:
            agent_name: The name of the agent whose capabilities are to be retrieved

        Returns:
            str: A description of the agent's capabilities and supported operations.
        """
        if card := self.agent_connections.get_agent_card(agent_name):
            if isinstance(card, AgentCard):
                return agentcard_to_prompt(card)
            if isinstance(card, dict):
                return str(card)
            return agentcard_to_prompt(card)

        return "The requested agent could not be found or is not available."

    def tool_get_enabled_agents(self) -> str:
        map_agent_name_to_card = self.agent_connections.get_planable_agent_cards()
        parts = []
        for agent_name, card in map_agent_name_to_card.items():
            parts.append(f"<{agent_name}>")
            parts.append(agentcard_to_prompt(card))
            parts.append((f"</{agent_name}>\n"))
        return "\n".join(parts)


def agentcard_to_prompt(card: AgentCard):
    """Convert an AgentCard to an LLM-friendly prompt string.

    Args:
        card: The AgentCard object or JSON structure describing an agent.

    Returns:
        A formatted string suitable for inclusion in the planner's instructions.
    """

    # Start with basic agent information
    prompt = f"# Agent: {card.name}\n\n"

    # Add description
    prompt += f"**Description:** {card.description}\n\n"

    # Add skills section
    if card.skills:
        prompt += "## Available Skills\n\n"

        for i, skill in enumerate(card.skills, 1):
            prompt += f"### {i}. {skill.name} (`{skill.id}`)\n\n"
            prompt += f"**Description:** {skill.description}\n\n"

            # Add examples if available
            if skill.examples:
                prompt += "**Examples:**\n"
                for example in skill.examples:
                    prompt += f"- {example}\n"
                prompt += "\n"

            # Add tags if available
            if skill.tags:
                tags_str = ", ".join([f"`{tag}`" for tag in skill.tags])
                prompt += f"**Tags:** {tags_str}\n\n"

            # Add separator between skills (except for the last one)
            if i < len(card.skills):
                prompt += "---\n\n"

    return prompt.strip()
