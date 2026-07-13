import requests
from bs4 import BeautifulSoup

from services.http import get


def get_forecast(lat, lon):
    point_url = f"https://api.weather.gov/points/{lat},{lon}"
    fallback = {"properties": {"periods": []}}

    try:
        point_response = get(point_url)
        if point_response.status_code != 200:
            return {**fallback, "error": "Failed to get point data"}

        point_data = point_response.json()
        forecast_url = point_data.get("properties", {}).get("forecast")
        if not forecast_url:
            return {**fallback, "error": "Forecast URL missing"}

        forecast_response = get(forecast_url)
        if forecast_response.status_code != 200:
            return {**fallback, "error": "Failed to get forecast"}

        return forecast_response.json()
    except (requests.RequestException, ValueError, TypeError) as exc:
        return {**fallback, "error": f"Forecast unavailable: {exc.__class__.__name__}"}


def get_current_observation(station_id):
    url = "https://forecast.weather.gov/MapClick.php?lat=33.20983&lon=-117.39433"
    fallback = {
        "station": station_id,
        "visibility_nm": "UNR",
        "barometer_inhg": "N/A",
    }

    try:
        response = get(url)
        if response.status_code != 200:
            return fallback

        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(" ", strip=True)
        barometer = "N/A"

        if "Barometer" in text:
            after = text.split("Barometer", 1)[1].strip()
            barometer = after.split("in", 1)[0].strip()

        return {
            "station": station_id,
            "visibility_nm": "UNR",
            "barometer_inhg": barometer,
        }
    except requests.RequestException:
        return fallback
