import asyncio
import json
import logging
from datetime import datetime
from uuid import uuid4

import click
import httpx
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    MessageSendParams,
    SendMessageRequest,
)
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH
from dateutil.relativedelta import relativedelta
from src.utils.analysts import ANALYST_ORDER

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)  # Get a logger instance


async def _main(tickers, initial_cash, model_provider, model_name, selected_analysts):
    base_url = "http://localhost:10001"
    print(f"{tickers=}")

    async with httpx.AsyncClient() as httpx_client:
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)

        try:
            logger.info("Attempting to fetch public agent card from: " f"{base_url}{AGENT_CARD_WELL_KNOWN_PATH}")
            agent_card = await resolver.get_agent_card()
            logger.info("Successfully fetched public agent card:")
            # logger.info(agent_card.model_dump_json(indent=2, exclude_none=True))

        except Exception as e:
            logger.error(f"Critical error fetching public agent card: {e}", exc_info=True)
            raise RuntimeError("Failed to fetch the public agent card. Cannot continue.") from e

        client = A2AClient(httpx_client=httpx_client, agent_card=agent_card)
        logger.info("A2AClient initialized.")

        end_date = datetime.now().strftime("%Y-%m-%d")
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
        start_date = (end_date_obj - relativedelta(months=3)).strftime("%Y-%m-%d")
        portfolio = {
            "cash": initial_cash,  # Initial cash amount
            "margin_requirement": 0,  # Initial margin requirement
            "margin_used": 0.0,  # total margin usage across all short positions
            "positions": {
                ticker: {
                    "long": 0,  # Number of shares held long
                    "short": 0,  # Number of shares held short
                    "long_cost_basis": 0.0,  # Average cost basis for long positions
                    "short_cost_basis": 0.0,  # Average price at which shares were sold short
                    "short_margin_used": 0.0,  # Dollars of margin used for this ticker's short
                }
                for ticker in tickers
            },
            "realized_gains": {
                ticker: {
                    "long": 0.0,  # Realized gains from long positions
                    "short": 0.0,  # Realized gains from short positions
                }
                for ticker in tickers
            },
        }
        paramas = {
            "tickers": tickers,
            "start_date": start_date,
            "end_date": end_date,
            "portfolio": portfolio,
            "model_name": model_name,
            "model_provider": model_provider,
            "selected_analysts": selected_analysts,
        }

        payload = {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": json.dumps(paramas)}],
                "messageId": uuid4().hex,
                "contextId": uuid4().hex,
            },
        }
        request = SendMessageRequest(id=str(uuid4()), params=MessageSendParams(**payload))

        response = await client.send_message(request, http_kwargs={"timeout": None})
        print(response.model_dump(mode="json", exclude_none=True))


@click.command()
@click.option("--tickers", "tickers", default="AAPL")
@click.option("--initial-cash", "initial_cash", default=10000.00)
@click.option("--model-provider", "model_provider", default="OpenRouter")
@click.option("--model-name", "model_name", default="openai/gpt-4o-mini")
@click.option("--analysts", "analysts", default="all")
def main(tickers, initial_cash, model_provider, model_name, analysts) -> None:
    supported_analysts = [name for name, _ in sorted(ANALYST_ORDER.items(), key=lambda x: x[1])]
    tickers = [ticker.strip().upper() for ticker in tickers.split(",")]
    if analysts == "all":
        analysts = [name for name, _ in supported_analysts]
    else:
        analysts = [name.strip() for name in analysts.split(",")]
        for name in analysts:
            if name not in supported_analysts:
                raise ValueError(f"Unknown analyst name: {name}. Supported analysts: {supported_analysts}")

    asyncio.run(_main(tickers, initial_cash, model_provider, model_name, analysts))


if __name__ == "__main__":
    main()
