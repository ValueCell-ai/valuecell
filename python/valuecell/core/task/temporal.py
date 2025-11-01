from datetime import datetime, timedelta
from typing import Optional

from loguru import logger

from valuecell.core.task.models import ScheduleConfig


def calculate_next_execution_delay(schedule_config: ScheduleConfig) -> Optional[float]:
    """Calculate the delay in seconds until the next scheduled execution.

    Args:
        schedule_config: ScheduleConfig with interval_minutes or daily_time.

    Returns:
        Delay in seconds until next execution, or None if no schedule configured.
    """
    if not schedule_config:
        return None

    now = datetime.now()

    # Interval-based scheduling
    if schedule_config.interval_minutes:
        return schedule_config.interval_minutes * 60

    # Daily time-based scheduling
    if schedule_config.daily_time:
        try:
            # Parse HH:MM format
            target_hour, target_minute = map(int, schedule_config.daily_time.split(":"))

            # Create target datetime for today
            target_time = now.replace(
                hour=target_hour, minute=target_minute, second=0, microsecond=0
            )

            # If target time has passed today, schedule for tomorrow
            if target_time <= now:
                target_time += timedelta(days=1)

            # Calculate delay in seconds
            delay = (target_time - now).total_seconds()
            return delay
        except (ValueError, AttributeError) as e:
            logger.error(
                f"Invalid daily_time format: {schedule_config.daily_time}, error: {e}"
            )
            return None

    return None
