import json
from pathlib import Path

import httpx
import pytest
import yaml

from valuecell.adapters.models.factory import (
    MiniMaxProvider,
    ModelFactory,
)
from valuecell.config.manager import ProviderConfig
from valuecell.server.api.routers.models import _resolve_minimax_probe_endpoint


def _provider_yaml() -> dict:
    config_path = Path(__file__).parents[4] / "configs" / "providers" / "minimax.yaml"
    return yaml.safe_load(config_path.read_text(encoding="utf-8"))


def _provider_config(
    base_url: str,
    default_model: str = "MiniMax-M3.1-Flash",
) -> ProviderConfig:
    config = _provider_yaml()
    return ProviderConfig(
        name="minimax",
        enabled=True,
        api_key="test-api-key",
        base_url=base_url,
        default_model=default_model,
        models=config["models"],
        parameters={},
    )


def test_minimax_provider_is_registered() -> None:
    assert ModelFactory._providers["minimax"] is MiniMaxProvider


@pytest.mark.parametrize(
    "base_url",
    [
        "https://api.minimax.io/v1",
        "https://api.minimaxi.com/v1",
    ],
)
def test_openai_compatible_flash_boundary_preserves_effort_and_content(
    base_url: str,
) -> None:
    model = MiniMaxProvider(_provider_config(base_url)).create_model()
    captured_payloads: list[dict] = []

    def capture(request: httpx.Request) -> httpx.Response:
        captured_payloads.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 0,
                "model": model.id,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "ok"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 1,
                    "completion_tokens": 1,
                    "total_tokens": 2,
                },
            },
        )

    model.client_params = {
        "http_client": httpx.Client(transport=httpx.MockTransport(capture)),
    }
    client = model.get_client()
    try:
        client.chat.completions.create(
            model=model.id,
            messages=[
                {
                    "role": "user",
                    "content": [{"type": "text", "text": "hello"}],
                }
            ],
            **model.get_request_params(),
        )
    finally:
        client.close()

    assert captured_payloads == [
        {
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": "hello"}],
                }
            ],
            "model": "MiniMax-M3.1-Flash",
            "reasoning_effort": "max",
        }
    ]


@pytest.mark.parametrize(
    "base_url",
    [
        "https://api.minimax.io/anthropic",
        "https://api.minimaxi.com/anthropic",
    ],
)
def test_anthropic_flash_boundary_sends_output_effort(base_url: str) -> None:
    model = MiniMaxProvider(_provider_config(base_url)).create_model()
    captured_requests: list[tuple[str, dict]] = []

    def capture(request: httpx.Request) -> httpx.Response:
        captured_requests.append((str(request.url), json.loads(request.content)))
        return httpx.Response(
            200,
            json={
                "id": "message-id",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": "ok"}],
                "model": model.id,
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 1, "output_tokens": 1},
            },
        )

    model.client_params = {
        "http_client": httpx.Client(transport=httpx.MockTransport(capture)),
    }
    client = model.get_client()
    try:
        client.messages.create(
            model=model.id,
            max_tokens=1,
            messages=[{"role": "user", "content": "hello"}],
            **model.get_request_params(),
        )
    finally:
        client.close()

    assert captured_requests == [
        (
            f"{base_url}/v1/messages",
            {
                "model": "MiniMax-M3.1-Flash",
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "hello"}],
                "output_config": {"effort": "max"},
            },
        )
    ]


def test_explicit_m3_preserves_multimodal_inputs_without_flash_effort() -> None:
    model = MiniMaxProvider(
        _provider_config(
            "https://api.minimax.io/v1",
            default_model="MiniMax-M3",
        )
    ).create_model()

    assert model.id == "MiniMax-M3"
    assert "reasoning_effort" not in model.get_request_params()

    captured_payloads: list[dict] = []

    def capture(request: httpx.Request) -> httpx.Response:
        captured_payloads.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-m3",
                "object": "chat.completion",
                "created": 0,
                "model": model.id,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "ok"},
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    model.client_params = {
        "http_client": httpx.Client(transport=httpx.MockTransport(capture)),
    }
    client = model.get_client()
    try:
        client.chat.completions.create(
            model=model.id,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "describe this"},
                        {
                            "type": "image_url",
                            "image_url": {"url": "data:image/png;base64,fixture"},
                        },
                    ],
                }
            ],
            **model.get_request_params(),
        )
    finally:
        client.close()

    assert captured_payloads[0]["model"] == "MiniMax-M3"
    assert captured_payloads[0]["messages"][0]["content"][1]["type"] == "image_url"
    assert "reasoning_effort" not in captured_payloads[0]


def test_provider_yaml_contains_target_models_and_endpoints() -> None:
    config = _provider_yaml()
    models = {model["id"]: model for model in config["models"]}

    assert config["default_model"] == "MiniMax-M3.1-Flash"
    assert [model["id"] for model in config["models"][:2]] == [
        "MiniMax-M3.1-Flash",
        "MiniMax-M3",
    ]
    assert config["endpoints"] == {
        "global_en": {
            "openai_base_url": "https://api.minimax.io/v1",
            "anthropic_base_url": "https://api.minimax.io/anthropic",
            "docs_root": "https://platform.minimax.io/docs",
        },
        "cn_zh": {
            "openai_base_url": "https://api.minimaxi.com/v1",
            "anthropic_base_url": "https://api.minimaxi.com/anthropic",
            "docs_root": "https://platform.minimaxi.com/docs",
        },
    }
    assert models["MiniMax-M3.1-Flash"]["context_length"] == 1000000
    assert models["MiniMax-M3.1-Flash"]["max_output_tokens"] == 524288
    assert models["MiniMax-M3.1-Flash"]["thinking"] == ["adaptive"]
    assert models["MiniMax-M3.1-Flash"]["request"] == {
        "reasoning_effort": "max",
        "anthropic_request_params": {"output_config": {"effort": "max"}},
    }
    assert models["MiniMax-M3.1-Flash"]["pricing_usd_per_million_tokens"] == {
        "input": 0.15,
        "output": 0.6,
        "cache_read": 0.015,
        "cache_write": None,
    }
    assert models["MiniMax-M3"]["context_length"] == 1000000
    assert models["MiniMax-M3"]["supported_inputs"] == ["text", "image", "video"]
    assert models["MiniMax-M3"]["thinking"] == ["adaptive", "disabled"]
    assert models["MiniMax-M2.7"]["context_length"] == 204800
    assert models["MiniMax-M2.7"]["thinking"] == ["always_on"]


@pytest.mark.parametrize(
    ("base_url", "expected"),
    [
        (
            "https://api.minimax.io/v1",
            ("https://api.minimax.io/v1/chat/completions", "openai_like"),
        ),
        (
            "https://api.minimaxi.com/v1",
            ("https://api.minimaxi.com/v1/chat/completions", "openai_like"),
        ),
        (
            "https://api.minimax.io/anthropic",
            ("https://api.minimax.io/anthropic/v1/messages", "anthropic"),
        ),
        (
            "https://api.minimaxi.com/anthropic",
            ("https://api.minimaxi.com/anthropic/v1/messages", "anthropic"),
        ),
    ],
)
def test_minimax_probe_endpoints(base_url: str, expected: tuple[str, str]) -> None:
    assert _resolve_minimax_probe_endpoint(base_url) == expected
