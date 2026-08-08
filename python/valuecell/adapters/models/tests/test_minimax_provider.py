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


def _provider_config(base_url: str) -> ProviderConfig:
    return ProviderConfig(
        name="minimax",
        enabled=True,
        api_key="test-api-key",
        base_url=base_url,
        default_model="MiniMax-M3",
        models=[],
        parameters={},
    )


def _provider_yaml() -> dict:
    config_path = Path(__file__).parents[4] / "configs" / "providers" / "minimax.yaml"
    return yaml.safe_load(config_path.read_text(encoding="utf-8"))


def test_minimax_provider_is_registered() -> None:
    assert ModelFactory._providers["minimax"] is MiniMaxProvider


@pytest.mark.parametrize(
    "base_url",
    [
        "https://api.minimax.io/v1",
        "https://api.minimaxi.com/v1",
    ],
)
def test_openai_compatible_base_urls_are_preserved(base_url: str) -> None:
    model = MiniMaxProvider(_provider_config(base_url)).create_model()

    assert model.id == "MiniMax-M3"
    assert model.base_url == base_url


@pytest.mark.parametrize(
    "base_url",
    [
        "https://api.minimax.io/anthropic",
        "https://api.minimaxi.com/anthropic",
    ],
)
def test_anthropic_client_appends_messages_path(base_url: str) -> None:
    model = MiniMaxProvider(_provider_config(base_url)).create_model()
    captured_urls: list[str] = []

    def capture(request: httpx.Request) -> httpx.Response:
        captured_urls.append(str(request.url))
        return httpx.Response(
            200,
            json={
                "id": "message-id",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": "ok"}],
                "model": "MiniMax-M3",
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 1, "output_tokens": 1},
            },
        )

    model.client_params = {
        **(model.client_params or {}),
        "http_client": httpx.Client(transport=httpx.MockTransport(capture)),
    }
    client = model.get_client()
    try:
        client.messages.create(
            model="MiniMax-M3",
            max_tokens=1,
            messages=[{"role": "user", "content": "hello"}],
        )
    finally:
        client.close()

    assert captured_urls == [f"{base_url}/v1/messages"]


def test_provider_yaml_contains_target_models_and_endpoints() -> None:
    config = _provider_yaml()
    models = {model["id"]: model for model in config["models"]}

    assert config["default_model"] == "MiniMax-M3"
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
    assert models["MiniMax-M3"]["context_length"] == 1000000
    assert models["MiniMax-M3"]["supported_inputs"] == ["text", "image", "video"]
    assert models["MiniMax-M3"]["thinking"] == ["adaptive", "disabled"]
    assert models["MiniMax-M3"]["pricing_usd_per_million_tokens"] == {
        "input": 0.6,
        "output": 2.4,
        "cache_read": 0.12,
        "cache_write": None,
    }
    assert models["MiniMax-M2.7"]["context_length"] == 204800
    assert models["MiniMax-M2.7"]["thinking"] == ["always_on"]
    assert models["MiniMax-M2.7"]["pricing_usd_per_million_tokens"] == {
        "input": 0.3,
        "output": 1.2,
        "cache_read": 0.06,
        "cache_write": 0.375,
    }


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
