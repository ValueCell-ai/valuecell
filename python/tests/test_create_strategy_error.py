import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from valuecell.server.api.app import create_app
from valuecell.server.db.connection import get_db
from valuecell.server.db.repositories.strategy_repository import StrategyRepository

# Sample request data
sample_request_data = {
    "llm_model_config": {
        "provider": "openai",
        "model_id": "gpt-4",
        "use_tools": True,
        "tools_module": "valuecell.tools",
    },
    "exchange_config": {
        "exchange_id": "binance_paper_trade",
        "trading_mode": "spot",
    },
    "trading_config": {
        "strategy_name": "Error Test Strategy",
        "budget": 1000.0,
    },
}


# Create a mock database session
@pytest.fixture
def db_session_mock():
    db = MagicMock(spec=Session)
    return db


# Override the get_db dependency
def override_get_db():
    try:
        db = db_session_mock()
        yield db
    finally:
        pass


app = create_app()
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@patch("valuecell.server.api.routers.strategy_agent.get_strategy_repository")
@patch(
    "valuecell.server.api.routers.strategy_agent.AgentOrchestrator.process_user_input"
)
def test_create_strategy_with_unexpected_error(
    mock_process_user_input, mock_get_strategy_repository, db_session_mock
):
    """
    Test that when an unexpected exception occurs, a strategy with 'error' status is created.
    """
    # Mock the repository
    mock_repo = MagicMock(spec=StrategyRepository)
    mock_get_strategy_repository.return_value = mock_repo

    # Mock the orchestrator to raise an exception
    mock_process_user_input.side_effect = Exception("Unexpected orchestrator failure")

    # Make the request
    response = client.post("/api/v1/strategies/create", json=sample_request_data)

    # Assertions
    assert response.status_code == 200
    response_json = response.json()
    assert response_json["status"] == "error"
    assert response_json["strategy_id"] != "unknown"

    # Verify that upsert_strategy was called with the correct parameters
    mock_repo.upsert_strategy.assert_called_once()
    args, kwargs = mock_repo.upsert_strategy.call_args
    assert kwargs["status"] == "error"
    assert kwargs["name"] == "Error Test Strategy"
    assert "Unexpected orchestrator failure" in kwargs["description"]
    assert kwargs["metadata"]["error"] == "Unexpected orchestrator failure"


if __name__ == "__main__":
    pytest.main([__file__])
