import os
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Optional, Union

from fastmcp import FastMCP
from pydantic import BaseModel, Field

# --- Constants ---
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_TIMEZONE = "Asia/Shanghai"

# Constants for time calculations
SECONDS_IN_MINUTE = 60
SECONDS_IN_HOUR = 3600
SECONDS_IN_DAY = 86400
SECONDS_IN_MONTH = 2629800  # Approximate: 30.4375 days
SECONDS_IN_YEAR = 31557600  # Approximate: 365.25 days


# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# --- MCP Server Setup ---
mcp = FastMCP(
    name="Timer MCP Server",
    instructions="An MCP server for time-related operations like timezone conversion and timestamp calculations.",
    host="0.0.0.0",
    port=8000,
)

# --- Helper Functions ---
def get_valid_timezone(tz_name: Optional[str]) -> ZoneInfo:
    """Returns a valid ZoneInfo object, defaulting to Shanghai if invalid."""
    if not tz_name:
        return ZoneInfo(DEFAULT_TIMEZONE)
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        logging.warning(f"Invalid timezone '{tz_name}' provided. Defaulting to '{DEFAULT_TIMEZONE}'.")
        return ZoneInfo(DEFAULT_TIMEZONE)

def to_int(value: Union[int, str], name: str) -> int:
    """Converts a value to an integer, raising a descriptive error if it fails."""
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            raise ValueError(f"Invalid integer value for '{name}': '{value}'")
    return value

# --- Pydantic Models ---
class TimeDifferenceResult(BaseModel):
    time_difference: int = Field(description="The input time difference in seconds.")
    years: float
    months: float
    days: float
    hours: float
    minutes: float
    seconds: float

# --- MCP Tools ---

@mcp.tool()
async def get_current_time(timezone: Optional[str] = None):
    """
    Gets the current time in the specified timezone.
    :param timezone: IANA timezone name (e.g., 'America/New_York'). Defaults to 'Asia/Shanghai'.
    """
    tz = get_valid_timezone(timezone)
    now_utc = datetime.now(ZoneInfo("UTC"))
    now_local = now_utc.astimezone(tz)
    
    return {
        "timestamp": int(now_local.timestamp()),
        "timezone": str(tz),
        "current_time": now_local.strftime(TIME_FORMAT),
    }

@mcp.tool()
async def convert_timestamp_to_time(timestamp: Union[int, str], timezone: Optional[str] = None):
    """
    Converts a Unix timestamp to a formatted time string in the specified timezone.
    :param timestamp: The Unix timestamp to convert (can be int or string).
    :param timezone: IANA timezone name. Defaults to 'Asia/Shanghai'.
    """
    ts = to_int(timestamp, "timestamp")
    tz = get_valid_timezone(timezone)
    dt_object = datetime.fromtimestamp(ts, tz)
    
    return {
        "timezone": str(tz),
        "time": dt_object.strftime(TIME_FORMAT),
    }

@mcp.tool()
async def convert_time_to_timestamp(time: str, timezone: Optional[str] = None):
    """
    Converts a formatted time string to a Unix timestamp in the specified timezone.
    :param time: The time string to convert (format: YYYY-MM-DD HH:MM:SS).
    :param timezone: IANA timezone name. Defaults to 'Asia/Shanghai'.
    """
    tz = get_valid_timezone(timezone)
    try:
        dt_object = datetime.strptime(time, TIME_FORMAT)
        dt_object_tz = dt_object.replace(tzinfo=tz)
        return {
            "timezone": str(tz),
            "timestamp": int(dt_object_tz.timestamp()),
        }
    except ValueError:
        raise ValueError(f"Time data '{time}' does not match format '{TIME_FORMAT}'")

@mcp.tool()
async def time_difference(start_timestamp: Union[int, str], end_timestamp: Union[int, str]):
    """
    Calculates the difference in seconds between two Unix timestamps.
    :param start_timestamp: The starting Unix timestamp (can be int or string).
    :param end_timestamp: The ending Unix timestamp (can be int or string).
    """
    start_ts = to_int(start_timestamp, "start_timestamp")
    end_ts = to_int(end_timestamp, "end_timestamp")
    difference = end_ts - start_ts
    return {"time_difference": difference}

@mcp.tool()
async def time_difference_caculate(time_difference: Union[int, str], mode: str = 'p') -> TimeDifferenceResult:
    """
    Calculates the time length (years, months, etc.) from a time difference in seconds.
    :param time_difference: The time difference in seconds (can be int or string).
    :param mode: 'p' for progressive calculation, 's' for separate calculation. Defaults to 'p'.
    """
    diff = to_int(time_difference, "time_difference")

    if mode.lower() not in ['p', 's']:
        logging.warning(f"Invalid mode '{mode}' provided. Defaulting to 'p' (progressive).")
        mode = 'p'

    if mode == 's':
        # Separate calculation
        return TimeDifferenceResult(
            time_difference=diff,
            years=diff / SECONDS_IN_YEAR,
            months=diff / SECONDS_IN_MONTH,
            days=diff / SECONDS_IN_DAY,
            hours=diff / SECONDS_IN_HOUR,
            minutes=diff / SECONDS_IN_MINUTE,
            seconds=float(diff)
        )
    else:
        # Progressive calculation
        remaining_seconds = abs(diff)
        
        years, remaining_seconds = divmod(remaining_seconds, SECONDS_IN_YEAR)
        months, remaining_seconds = divmod(remaining_seconds, SECONDS_IN_MONTH)
        days, remaining_seconds = divmod(remaining_seconds, SECONDS_IN_DAY)
        hours, remaining_seconds = divmod(remaining_seconds, SECONDS_IN_HOUR)
        minutes, seconds = divmod(remaining_seconds, SECONDS_IN_MINUTE)

        sign = -1 if diff < 0 else 1
        return TimeDifferenceResult(
            time_difference=diff,
            years=float(years * sign),
            months=float(months * sign),
            days=float(days * sign),
            hours=float(hours * sign),
            minutes=float(minutes * sign),
            seconds=float(seconds * sign)
        )

@mcp.tool()
async def get_day_of_week(timestamp: Union[int, str], timezone: Optional[str] = None):
    """
    Calculates the day of the week from a Unix timestamp in the specified timezone.
    :param timestamp: The Unix timestamp to calculate the day of the week from (can be int or string).
    :param timezone: IANA timezone name. Defaults to 'Asia/Shanghai'.
    """
    ts = to_int(timestamp, "timestamp")
    tz = get_valid_timezone(timezone)
    dt_object = datetime.fromtimestamp(ts, tz)
    day_name = dt_object.strftime('%A')  # %A gives the full weekday name (e.g., Monday)

    return {
        "timestamp": ts,
        "timezone": str(tz),
        "day_of_week": day_name,
    }

@mcp.tool()
async def get_weekday_timestamps_for_week(timestamp: Union[int, str], timezone: Optional[str] = None):
    """
    Calculates the timestamps for Monday through Sunday of the week containing the given timestamp.
    :param timestamp: The reference Unix timestamp (can be int or string).
    :param timezone: IANA timezone name. Defaults to 'Asia/Shanghai'.
    """
    ts = to_int(timestamp, "timestamp")
    tz = get_valid_timezone(timezone)
    start_date = datetime.fromtimestamp(ts, tz)
    
    # Monday is 0 and Sunday is 6. Calculate the Monday of the current week.
    days_from_monday = start_date.weekday()
    monday_of_week = start_date - timedelta(days=days_from_monday)
    monday_of_week = monday_of_week.replace(hour=0, minute=0, second=0, microsecond=0)

    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    week_timestamps = {}

    for i, day_name in enumerate(weekdays):
        current_day = monday_of_week + timedelta(days=i)
        week_timestamps[day_name] = {
            "timestamp": int(current_day.timestamp()),
            "date": current_day.strftime(TIME_FORMAT)
        }

    return {
        "reference_timestamp": ts,
        "timezone": str(tz),
        "week_timestamps": week_timestamps
    }

@mcp.tool()
async def time_until_next_date(target: Union[int, str], timezone: Optional[str] = None):
    """
    Calculates the time remaining until the next specified day of the month or day of the week.
    :param target: The target day of the month (1-31) or day of the week (e.g., "Saturday").
    :param timezone: IANA timezone name. Defaults to 'Asia/Shanghai'.
    """
    tz = get_valid_timezone(timezone)
    now = datetime.now(tz)

    weekdays = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, 
        "friday": 4, "saturday": 5, "sunday": 6
    }

    # Check if target is a weekday name
    if isinstance(target, str) and target.lower() in weekdays:
        target_weekday_name = target.lower()
        target_weekday = weekdays[target_weekday_name]
        current_weekday = now.weekday()

        days_ahead = (target_weekday - current_weekday + 7) % 7
        
        next_date = (now + timedelta(days=days_ahead)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # If the calculated date is in the past (e.g., target is today but time has passed),
        # move to the next week's occurrence.
        if next_date < now:
            next_date += timedelta(days=7)
        
        time_remaining = next_date - now
        
        return {
            "target_day": target.capitalize(),
            "timezone": str(tz),
            "next_occurrence_time": next_date.strftime(TIME_FORMAT),
            "time_remaining_seconds": int(time_remaining.total_seconds())
        }

    # Original logic for day of the month
    try:
        day = to_int(target, "target_day")
    except ValueError:
        raise ValueError(f"Invalid target: '{target}'. Must be a day of the month (1-31) or a weekday name.")

    if not 1 <= day <= 31:
        raise ValueError("Target day must be between 1 and 31.")

    # Determine the year and month for the next occurrence
    next_year = now.year
    next_month = now.month
    
    try:
        # Try to create the date in the current month
        next_date = now.replace(day=day, hour=0, minute=0, second=0, microsecond=0)
        if now >= next_date:
            # If it's in the past, move to the next month
            next_month += 1
            if next_month > 12:
                next_month = 1
                next_year += 1
    except ValueError:
        # This happens if the day is invalid for the current month (e.g., 31 in Feb)
        # Move to the next month
        next_month += 1
        if next_month > 12:
            next_month = 1
            next_year += 1

    # Loop until we find a valid month for the target day
    while True:
        try:
            next_date = datetime(next_year, next_month, day, tzinfo=tz)
            break
        except ValueError:
            next_month += 1
            if next_month > 12:
                next_month = 1
                next_year += 1

    time_remaining = next_date - now
    
    return {
        "target_day": day,
        "timezone": str(tz),
        "next_occurrence_time": next_date.strftime(TIME_FORMAT),
        "time_remaining_seconds": int(time_remaining.total_seconds())
    }

if __name__ == "__main__":
    mcp.run(transport='sse')
