import os
import logging
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Optional

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
async def convert_timestamp_to_time(timestamp: int, timezone: Optional[str] = None):
    """
    Converts a Unix timestamp to a formatted time string in the specified timezone.
    :param timestamp: The Unix timestamp to convert.
    :param timezone: IANA timezone name. Defaults to 'Asia/Shanghai'.
    """
    tz = get_valid_timezone(timezone)
    dt_object = datetime.fromtimestamp(timestamp, tz)
    
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
async def time_difference(start_timestamp: int, end_timestamp: int):
    """
    Calculates the difference in seconds between two Unix timestamps.
    :param start_timestamp: The starting Unix timestamp.
    :param end_timestamp: The ending Unix timestamp.
    """
    difference = end_timestamp - start_timestamp
    return {"time_difference": difference}

@mcp.tool()
async def time_difference_caculate(time_difference: int, mode: str = 'p') -> TimeDifferenceResult:
    """
    Calculates the time length (years, months, etc.) from a time difference in seconds.
    :param time_difference: The time difference in seconds.
    :param mode: 'p' for progressive calculation, 's' for separate calculation. Defaults to 'p'.
    """
    if mode.lower() not in ['p', 's']:
        logging.warning(f"Invalid mode '{mode}' provided. Defaulting to 'p' (progressive).")
        mode = 'p'

    if mode == 's':
        # Separate calculation
        return TimeDifferenceResult(
            time_difference=time_difference,
            years=time_difference / SECONDS_IN_YEAR,
            months=time_difference / SECONDS_IN_MONTH,
            days=time_difference / SECONDS_IN_DAY,
            hours=time_difference / SECONDS_IN_HOUR,
            minutes=time_difference / SECONDS_IN_MINUTE,
            seconds=float(time_difference)
        )
    else:
        # Progressive calculation
        remaining_seconds = abs(time_difference)
        
        years, remaining_seconds = divmod(remaining_seconds, SECONDS_IN_YEAR)
        months, remaining_seconds = divmod(remaining_seconds, SECONDS_IN_MONTH)
        days, remaining_seconds = divmod(remaining_seconds, SECONDS_IN_DAY)
        hours, remaining_seconds = divmod(remaining_seconds, SECONDS_IN_HOUR)
        minutes, seconds = divmod(remaining_seconds, SECONDS_IN_MINUTE)

        sign = -1 if time_difference < 0 else 1
        return TimeDifferenceResult(
            time_difference=time_difference,
            years=float(years * sign),
            months=float(months * sign),
            days=float(days * sign),
            hours=float(hours * sign),
            minutes=float(minutes * sign),
            seconds=float(seconds * sign)
        )

@mcp.tool()
async def get_day_of_week(timestamp: int):
    """
    Calculates the day of the week from a Unix timestamp.
    :param timestamp: The Unix timestamp to calculate the day of the week from.
    """
    # The timezone doesn't affect the day of the week calculation from a UTC timestamp
    dt_object = datetime.fromtimestamp(timestamp, ZoneInfo("UTC"))
    day_name = dt_object.strftime('%A') # %A gives the full weekday name (e.g., Monday)
    
    return {
        "timestamp": timestamp,
        "day_of_week": day_name,
    }

if __name__ == "__main__":
    mcp.run(transport='sse')
