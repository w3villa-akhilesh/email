import os
from datetime import datetime
from pytz import timezone, UTC
from dotenv import load_dotenv
from logger import logger

load_dotenv()

TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")

def to_ist(dt: datetime) -> str:
    """
    Convert a datetime object to the timezone specified in env (default Asia/Kolkata) and return as 'YYYY-MM-DDTHH:MM:SS' string.
    If the datetime is naive, assume UTC.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = UTC.localize(dt)
    dt_tz = dt.astimezone(timezone(TIMEZONE))
    return dt_tz.strftime('%Y-%m-%dT%H:%M:%S')

def to_ist_range(dt1, dt2):
    """
    Convert two datetime objects to the timezone specified in env (default Asia/Kolkata) and return as tuple of 'YYYY-MM-DD HH:MM:SS' strings.
    If the datetime is naive, assume UTC.
    """
    def convert(dt):
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = UTC.localize(dt)
        dt_tz = dt.astimezone(timezone(TIMEZONE))
        return dt_tz.strftime('%Y-%m-%d %H:%M:%S')
    return convert(dt1), convert(dt2)