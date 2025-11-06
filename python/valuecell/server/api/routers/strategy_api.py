"""Aggregated Strategy API router.

Unifies strategy-related endpoints under a single registration point,
while keeping logical sub-routers separated for clarity.
"""

from fastapi import APIRouter

from .strategy import create_strategy_router
from .strategy_agent import create_strategy_agent_router


def create_strategy_api_router() -> APIRouter:
    router = APIRouter()

    # Include core strategy endpoints (prefix: /strategies)
    router.include_router(create_strategy_router())

    # Include StrategyAgent endpoints (prefix: /strategies)
    router.include_router(create_strategy_agent_router())

    return router
