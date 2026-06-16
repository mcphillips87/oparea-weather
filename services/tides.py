import requests
from datetime import datetime, timedelta


def get_tide_predictions(station, days=7):
    today = datetime.utcnow()
    end_date = today + timedelta(days=days)

    begin_date = today.strftime("%Y%m%d")
    end_date = end_date.strftime("%Y%m%d")

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

    return {
        "station": station,
        "predictions": data["predictions"]
    }