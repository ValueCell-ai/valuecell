from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from ..models import HistoryRecord, TradeDigest

# Contracts for history recording and digest building (module-local abstract interfaces).


class HistoryRecorder(ABC):
    """Persists important checkpoints for later analysis and digest building."""

    @abstractmethod
    def record(self, record: HistoryRecord) -> None:
        """Persist a single history record."""
        raise NotImplementedError


class DigestBuilder(ABC):
    """Builds TradeDigest from historical records (incremental or batch)."""

    @abstractmethod
    def build(self, records: List[HistoryRecord]) -> TradeDigest:
        """Construct a digest object from given history records."""
        raise NotImplementedError
