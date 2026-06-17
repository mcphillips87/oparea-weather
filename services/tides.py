import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def get_tide_predictions(station, days=7, days_back=0):
    """
    Get NOAA high/low tide predictions.

    days_back lets the Current page include the previous tide shift,
    while the Data page can keep using the normal 7-day forward view.
    NOAA returns local tide strings because time_zone is lst_ldt, so the
    request dates are also built from Pacific local time.
    """
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

    response = requests.get(url, params=params, timeout=10)

    if response.status_code != 200:
        return {"error": "Failed to get tide predictions"}

    data = response.json()

    if "predictions" not in data:
        return {
            "error": "No tide predictions returned",
            "details": data
        }

    predictions = sorted(
        data["predictions"],
        key=lambda tide: datetime.strptime(tide["t"], "%Y-%m-%d %H:%M")
    )

    return {
        "station": station,
        "begin_date": begin_date,
        "end_date": end_date,
        "predictions": predictions
    }
