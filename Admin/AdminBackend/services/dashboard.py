from sqlalchemy import func, cast, Date
from datetime import datetime, timedelta
from collections import defaultdict
from database.models import Event
from logger import logger

def get_dashboard_data(db, start_date=None, end_date=None):
    """
    Returns total hits per app in a date range, including apps with 0 hits.
    """

    # Parse input dates or set defaults
    try:
        if end_date:
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        else:
            end_date = datetime.utcnow().date()

        if start_date:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        else:
            start_date = end_date - timedelta(days=6)
    except ValueError:
        raise ValueError("Dates must be in YYYY-MM-DD format")

    # Fetch all distinct app names
    all_apps = [row[0] for row in db.query(Event.app_name).distinct().all()]

    # Query actual hit counts grouped by app_name
    results = db.query(
        Event.app_name,
        func.count().label("total_hits")
    ).filter(
        cast(Event.timestamp, Date) >= start_date,
        cast(Event.timestamp, Date) <= end_date
    ).group_by(Event.app_name).all()

    # Build a lookup map
    hits_map = defaultdict(lambda: 0)
    for row in results:
        hits_map[row.app_name] = row.total_hits

    # Construct final response with 0 where missing
    apps_data = []
    for app in all_apps:
        apps_data.append({
            "app_name": app,
            "total_hits": hits_map[app]
        })

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "apps": apps_data
    }
