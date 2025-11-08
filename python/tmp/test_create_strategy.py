from fastapi.testclient import TestClient

from valuecell.server.api.app import create_app

app = create_app()
client = TestClient(app)

payload = {
    "llm_model_config": {
        "provider": "openrouter",
        "model_id": "gpt-4o-mini",
        "api_key": "dummy-key",
    },
    "exchange_config": {
        "exchange_id": "virtual",
        "trading_mode": "virtual",
    },
    "trading_config": {
        "strategy_name": "Demo Strategy",
        "initial_capital": 10000,
        "max_leverage": 1.0,
        "max_positions": 5,
        "symbols": ["BTC-USD", "ETH-USD"],
        "decide_interval": 60,
    },
}

res = client.post("/api/v1/strategies/create", json=payload)
print("status:", res.status_code)
print("body:", res.text)
