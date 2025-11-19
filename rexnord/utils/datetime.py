from datetime import datetime
import pytz

def get_formatted_timestamp(timezone_str: str = "UTC", fmt: str = "%Y-%m-%d %H:%M:%S %p %Z") -> str:
    """
    Returns a formatted timestamp in the specified timezone.

    Args:
        timezone_str (str): Timezone name (e.g., 'UTC', 'Asia/Kolkata', 'US/Pacific')
        fmt (str): Format string (default = 'YYYY-MM-DD HH:MM:SS AM/PM TZ')

    Returns:
        str: Formatted datetime string in the specified timezone
    """
    try:
        tz = pytz.timezone(timezone_str)
    except pytz.UnknownTimeZoneError:
        tz = pytz.utc  # fallback to UTC if invalid

    now = datetime.now(pytz.utc).astimezone(tz)  # Always start from UTC
    return now.strftime(fmt)
