import requests
from bs4 import BeautifulSoup

from services.http import get


def get_forecast(lat, lon):
    point_url = f"https://api.weather.gov/points/{lat},{lon}"
    fallback = {"properties": {"periods": []}}

    try:
        point_response = get(point_url)

        if point_response.status_code != 200:
            print(
                f"LAND POINTS FAILED: HTTP {point_response.status_code} "
                f"URL={point_response.url}"
            )
            return {
                **fallback,
                "error": (
                    f"Failed to get point data: "
                    f"HTTP {point_response.status_code}"
                ),
            }

        point_data = point_response.json()
        forecast_url = point_data.get("properties", {}).get("forecast")

        if not forecast_url:
            print("LAND FORECAST FAILED: Forecast URL missing")
            return {
                **fallback,
                "error": "Forecast URL missing",
            }

        forecast_response = get(forecast_url)

        if forecast_response.status_code != 200:
            print(
                f"LAND FORECAST FAILED: HTTP "
                f"{forecast_response.status_code} "
                f"URL={forecast_response.url}"
            )
            return {
                **fallback,
                "error": (
                    f"Failed to get forecast: "
                    f"HTTP {forecast_response.status_code}"
                ),
            }

        return forecast_response.json()

    except (requests.RequestException, ValueError, TypeError) as exc:
        print(
            f"LAND FORECAST EXCEPTION: "
            f"{type(exc).__name__}: {exc}"
        )
        return {
            **fallback,
            "error": f"Forecast unavailable: {exc.__class__.__name__}",
        }

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
    except (requests.RequestException, ValueError, TypeError) as exc:
        print(f"LAND FORECAST EXCEPTION: {type(exc).__name__}: {exc}")
        return {
            **fallback,
            "error": f"Forecast unavailable: {exc.__class__.__name__}"
        }

