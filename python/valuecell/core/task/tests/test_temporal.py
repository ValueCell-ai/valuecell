from datetime import datetime as real_datetime

import pytest

from valuecell.core.task.models import ScheduleConfig
from valuecell.core.task.temporal import calculate_next_execution_delay


def test_no_schedule_returns_none():
    assert calculate_next_execution_delay(None) is None


def test_interval_minutes_converted_to_seconds():
    cfg = ScheduleConfig(interval_minutes=5)
    assert calculate_next_execution_delay(cfg) == 300


@pytest.mark.parametrize(
    "current_time,daily_time,expected",
    [
        (real_datetime(2025, 1, 1, 8, 0, 0), "09:30", 5400),
        (real_datetime(2025, 1, 1, 20, 0, 0), "07:15", 11 * 3600 + 15 * 60),
    ],
)
def test_daily_time_calculations(
    current_time: real_datetime,
    daily_time: str,
    expected: int,
    monkeypatch: pytest.MonkeyPatch,
):
    class FixedDatetime(real_datetime):
        @classmethod
        def now(cls):
            return current_time

    monkeypatch.setattr("valuecell.core.task.temporal.datetime", FixedDatetime)

    cfg = ScheduleConfig(daily_time=daily_time)
    delay = calculate_next_execution_delay(cfg)

    assert int(delay) == expected


def test_invalid_daily_time_returns_none(monkeypatch: pytest.MonkeyPatch):
    class FixedDatetime(real_datetime):
        @classmethod
        def now(cls):
            return real_datetime(2025, 1, 1, 8, 0, 0)

    monkeypatch.setattr("valuecell.core.task.temporal.datetime", FixedDatetime)

    cfg = ScheduleConfig(daily_time="bad-input")
    assert calculate_next_execution_delay(cfg) is None
