from typing import List

from ..models import HistoryRecord
from .interfaces import HistoryRecorder


class InMemoryHistoryRecorder(HistoryRecorder):
    """In-memory recorder storing history records."""

    def __init__(self) -> None:
        self.records: List[HistoryRecord] = []

    def record(self, record: HistoryRecord) -> None:
        self.records.append(record)
