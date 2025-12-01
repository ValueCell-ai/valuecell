"""Service façade for the super agent orchestration stage."""

from __future__ import annotations

from typing import AsyncIterator

from valuecell.core.types import UserInput

from .core import SuperAgent, SuperAgentOutcome


class SuperAgentService:
    """Thin wrapper to expose SuperAgent behaviour as a service."""

    def __init__(self, super_agent: SuperAgent | None = None) -> None:
        self._super_agent = super_agent or SuperAgent()

    @property
    def name(self) -> str:
        return self._super_agent.name

    async def run(
        self, user_input: UserInput
    ) -> AsyncIterator[str | SuperAgentOutcome]:
        async for item in self._super_agent.run(user_input):
            yield item
