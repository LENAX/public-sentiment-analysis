from datetime import datetime
from uuid import UUID
from typing import Optional, Union
from pydantic import BaseModel, validator


class Schedule(BaseModel):
    """ Describes the schedule of a job

    Args:
        year (int|str) – 4-digit year
        month (int|str) – month (1-12)
        day (int|str) – day of month (1-31)
        week (int|str) – ISO week (1-53)
        day_of_week (int|str) – number or name of weekday (0-6 or mon,tue,wed,thu,fri,sat,sun)
        hour (int|str) – hour (0-23)
        minute (int|str) – minute (0-59)
        second (int|str) – second (0-59)
        start_date (datetime|str) – earliest possible date/time to trigger on (inclusive)
        end_date (datetime|str) – latest possible date/time to trigger on (inclusive)
        timezone (datetime.tzinfo|str) – time zone to use for the date/time calculations (defaults to scheduler timezone)
        jitter (int|None) – delay the job execution by jitter seconds at most
    """
    year: Union[int, str]
    month: Union[int, str]
    day: Union[int, str]
    week: Union[int, str]
    day_of_week: Union[int, str]
    hour: Union[int, str]
    minute: Union[int, str]
    second: Union[int, str]
    start_date: Union[int, str]
    end_date: Union[int, str]
