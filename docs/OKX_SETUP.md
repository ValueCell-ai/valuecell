# OKX Setup Guide

Use this checklist to enable the Auto Trading agent to route spot orders through OKX. Start with the paper environment before touching mainnet funds.

## 1. Create API Credentials
- Log in to the OKX console → *API* → *Create V5 API key*.
- Enable **Trade** permission. Withdrawals are not required for trading.
- Record the **API Key**, **Secret Key**, and **Passphrase** immediately; you will not be able to view the secret again.
- For paper trading, toggle the **Demo trading** switch when generating the key (or set `flag=0` by using the paper environment).

## 2. Configure Environment Variables
Add the following entries to `.env` (or export them before launching):

```bash
AUTO_TRADING_EXCHANGE=okx
OKX_NETWORK=paper            # change to mainnet after validation
OKX_API_KEY=your_api_key
OKX_API_SECRET=your_secret
OKX_API_PASSPHRASE=your_passphrase
OKX_ALLOW_LIVE_TRADING=false
OKX_MARGIN_MODE=cash         # use cross / isolated for margin derivatives
OKX_USE_SERVER_TIME=false    # set true if you see timestamp drift errors
```

## 3. Launch the Stack
- Install dependencies: `uv sync --group dev` and `bun install --cwd frontend` (first run only).
- Start services with paper overrides:

  ```bash
  ./start.sh --exchange okx --network paper
  ```

- This propagates the environment into `python/scripts/launch.py`, ensuring the Auto Trading agent connects with paper credentials.

## 4. Validate Paper Trading
1. Trigger the Auto Trading agent via the UI (http://localhost:1420) or CLI and request trades such as “Trade BTC-USD with 5000 USD on OKX”.
2. Watch the logs under `logs/<timestamp>/AutoTradingAgent.log` for entries like `exchange=okx` and `status=filled`.
3. Open https://www.okx.com/paper/account/trade to confirm the orders appear in the simulated environment.
4. Run the OKX unit tests locally: `uv run python -m pytest valuecell/agents/auto_trading_agent/tests/test_okx_exchange.py`.

## 5. Promote to Mainnet (Optional and High Risk)
- Flip `OKX_NETWORK=mainnet` and `OKX_ALLOW_LIVE_TRADING=true` only after paper validation and formal approval.
- Restart with `./start.sh --exchange okx --network mainnet --allow-live-trading`.
- Monitor fills and balances continuously; revert the toggle if behaviour is unexpected.

## 6. Safety Best Practices
- Store secrets in a vault (1Password, AWS Secrets Manager, etc.) and inject them at runtime instead of committing to disk.
- Rotate keys periodically and whenever you suspect compromise.
- Set conservative order sizes (`risk_per_trade`) and verify instrument availability (`BTC-USDT`, `ETH-USDT`, etc.) before relying on automation.
- Archive trading logs for audit purposes and switch the system back to paper mode when not actively monitoring.
