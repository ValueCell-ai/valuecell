import os
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from valuecell.agents.common.trading.models import LLMModelConfig
from valuecell.config import manager as config_manager
from valuecell.server.api import auth
from valuecell.server.api.auth import get_current_user
from valuecell.server.api.routers import models


class ConfigLoaderStub:
    def __init__(self) -> None:
        self.provider = {
            "connection": {
                "api_key_env": "TEST_PROVIDER_API_KEY",
                "base_url": "https://provider.example/v1",
            }
        }

    def clear_cache(self) -> None:
        pass

    def load_config(self) -> dict:
        return {}

    def load_provider_config(self, provider: str) -> dict:
        return self.provider if provider == "test-provider" else {}


class ConfigManagerStub:
    primary_provider = "test-provider"

    def __init__(self, loader: ConfigLoaderStub) -> None:
        self.loader = loader
        self._config = {}

    def get_provider_config(self, provider: str):
        if provider != "test-provider":
            return None
        return SimpleNamespace(
            api_key=os.getenv("TEST_PROVIDER_API_KEY"),
            base_url="https://provider.example/v1",
            default_model="test-model",
            models=[{"id": "test-model", "name": "Test Model"}],
            name=provider,
        )


class AuthClientStub:
    def __init__(self, response: httpx.Response) -> None:
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args) -> None:
        pass

    async def get(self, *_args, **_kwargs) -> httpx.Response:
        return self.response


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch, tmp_path) -> FastAPI:
    loader = ConfigLoaderStub()
    manager = ConfigManagerStub(loader)
    monkeypatch.setattr(models, "get_config_loader", lambda: loader)
    monkeypatch.setattr(models, "get_config_manager", lambda: manager)
    monkeypatch.setattr(models, "get_system_env_path", lambda: tmp_path / ".env")
    config_dir = tmp_path / "configs"
    (config_dir / "providers").mkdir(parents=True)
    monkeypatch.setattr(models, "CONFIG_DIR", config_dir)
    monkeypatch.setenv("TEST_PROVIDER_API_KEY", "configured-provider-key")

    app = FastAPI()
    app.include_router(models.create_models_router(), prefix="/api/v1")
    return app


@pytest.fixture
def client(app: FastAPI):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def authenticated_client(app: FastAPI):
    app.dependency_overrides[get_current_user] = lambda: {"id": "test-user"}
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("get", "/api/v1/models/providers/test-provider", None),
        (
            "put",
            "/api/v1/models/providers/test-provider/config",
            {"api_key": "replacement-provider-key"},
        ),
    ],
)
def test_provider_credentials_require_authentication(
    client: TestClient, method: str, path: str, payload: dict | None
) -> None:
    response = client.request(method, path, json=payload)

    assert response.status_code == 401
    assert os.environ["TEST_PROVIDER_API_KEY"] == "configured-provider-key"


def test_provider_detail_masks_configured_credentials(
    authenticated_client: TestClient,
) -> None:
    response = authenticated_client.get("/api/v1/models/providers/test-provider")

    assert response.status_code == 200
    assert response.json()["data"]["api_key"] == "********"
    assert "configured-provider-key" not in response.text


def test_active_bearer_session_authorizes_provider_detail(
    app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    response = httpx.Response(200, json={"data": {"id": "test-user"}})
    monkeypatch.setattr(
        auth.httpx,
        "AsyncClient",
        lambda **_kwargs: AuthClientStub(response),
    )

    with TestClient(app) as test_client:
        result = test_client.get(
            "/api/v1/models/providers/test-provider",
            headers={"Authorization": "Bearer active-session"},
        )

    assert result.status_code == 200
    assert result.json()["data"]["api_key"] == "********"


def test_invalid_bearer_session_cannot_update_provider(
    app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    response = httpx.Response(401, json={"detail": "Unauthorized"})
    monkeypatch.setattr(
        auth.httpx,
        "AsyncClient",
        lambda **_kwargs: AuthClientStub(response),
    )

    with TestClient(app) as test_client:
        result = test_client.put(
            "/api/v1/models/providers/test-provider/config",
            headers={"Authorization": "Bearer expired-session"},
            json={"api_key": "replacement-provider-key"},
        )

    assert result.status_code == 401
    assert os.environ["TEST_PROVIDER_API_KEY"] == "configured-provider-key"


def test_authenticated_provider_update_succeeds_without_echoing_credentials(
    authenticated_client: TestClient, tmp_path
) -> None:
    response = authenticated_client.put(
        "/api/v1/models/providers/test-provider/config",
        json={"api_key": "replacement-provider-key"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["api_key"] == "********"
    assert "replacement-provider-key" not in response.text
    assert os.environ["TEST_PROVIDER_API_KEY"] == "replacement-provider-key"
    assert "TEST_PROVIDER_API_KEY=replacement-provider-key" in (
        tmp_path / ".env"
    ).read_text(encoding="utf-8")


def test_masked_provider_key_round_trip_preserves_configured_credential(
    authenticated_client: TestClient,
) -> None:
    response = authenticated_client.put(
        "/api/v1/models/providers/test-provider/config",
        json={"api_key": "********", "base_url": "https://updated.example/v1"},
    )

    assert response.status_code == 200
    assert os.environ["TEST_PROVIDER_API_KEY"] == "configured-provider-key"


def test_default_model_response_masks_configured_credentials(
    client: TestClient, tmp_path
) -> None:
    (tmp_path / "configs" / "providers" / "test-provider.yaml").write_text(
        "models:\n  - id: test-model\n    name: Test Model\n",
        encoding="utf-8",
    )

    response = client.put(
        "/api/v1/models/providers/test-provider/default-model",
        json={"model_id": "test-model"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["api_key"] == "********"
    assert "configured-provider-key" not in response.text


def test_masked_provider_key_uses_configured_credential_for_strategy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loader = ConfigLoaderStub()
    manager = ConfigManagerStub(loader)
    monkeypatch.setattr(config_manager, "get_config_manager", lambda: manager)
    monkeypatch.setenv("TEST_PROVIDER_API_KEY", "configured-provider-key")

    config = LLMModelConfig(
        provider="test-provider",
        model_id="test-model",
        api_key="********",
    )

    assert config.api_key == "configured-provider-key"
