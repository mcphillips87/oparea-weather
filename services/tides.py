import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from services.http import get


def get_tide_predictions(station, days=7, days_back=0):
    now = datetime.now(ZoneInfo("America/Los_Angeles"))
    begin_date = (now - timedelta(days=days_back)).strftime("%Y%m%d")
    end_date = (now + timedelta(days=days)).strftime("%Y%m%d")

    url = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
    params = {
        "begin_date": begin_date,
        "end_date": end_date,
        "station": station,
        "product": "predictions",
        "datum": "MLLW",
        "time_zone": "lst_ldt",
        "units": "english",
        "interval": "hilo",
        "format": "json",
    }

    fallback = {
        "station": station,
        "begin_date": begin_date,
        "end_date": end_date,
        "predictions": [],
    }

    try:
        response = get(url, params=params)
        if response.status_code != 200:
            return {**fallback, "error": "Failed to get tide predictions"}

        data = response.json()
        if "predictions" not in data:
            return {**fallback, "error": "No tide predictions returned", "details": data}

        predictions = sorted(
            data["predictions"],
            key=lambda tide: datetime.strptime(tide["t"], "%Y-%m-%d %H:%M"),
        )
        return {**fallback, "predictions": predictions}
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        return {**fallback, "error": f"Tides unavailable: {exc.__class__.__name__}"}
