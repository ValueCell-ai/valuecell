from typing import List

from valuecell.agents.common.trading.models import HistoryRecord

from .interfaces import BaseHistoryRecorder


class InMemoryHistoryRecorder(BaseHistoryRecorder):
    """In-memory recorder storing history records."""

    def __init__(self, history_limit: int = 200) -> None:
        self.records: List[HistoryRecord] = []
        self.history_limit = history_limit

    def record(self, record: HistoryRecord) -> None:
        self.records.append(record)
        if len(self.records) > self.history_limit:
            self.records = self.records[-self.history_limit :]

    def get_records(self) -> List[HistoryRecord]:
        return self.records
