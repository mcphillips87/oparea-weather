import requests
import re
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": "AOA Weather App"
}


def get_marine_point_forecast(lat, lon):
    url = f"https://forecast.weather.gov/MapClick.php?lat={lat}&lon={lon}"

    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        return {
            "error": "Failed to get marine point forecast",
            "status_code": response.status_code
        }

    soup = BeautifulSoup(response.text, "html.parser")

    forecast_items = soup.select("#detailed-forecast-body .row-forecast")

    if not forecast_items:
        return {
            "error": "Could not find detailed marine forecast"
        }

    periods = []

    for item in forecast_items:
        label = item.select_one(".forecast-label")
        text = item.select_one(".forecast-text")

        if label and text:
            periods.append({
                "name": label.get_text(strip=True),
                "forecast": text.get_text(" ", strip=True)
            })

    return {
        "url": url,
        "periods": periods
    }

def parse_marine_forecast(forecast_text):
    wind_match = re.search(
        r"^(.+?\bwind[s]?\b.+?kt(?: or less)?)(?:\.|$)",
        forecast_text,
        re.IGNORECASE
    )

    wind = wind_match.group(1).strip() + "." if wind_match else "N/A"

    seas_match = re.search(
        r"((?:Mixed swell|Swell|Seas).*?)(?=$)",
        forecast_text,
        re.IGNORECASE
    )

    seas = seas_match.group(1).strip() if seas_match else "N/A"

    weather = forecast_text

    if wind_match:
        weather = weather.replace(wind_match.group(0), "").strip()

    if seas_match:
        weather = weather.replace(seas_match.group(0), "").strip()

    weather = weather.strip(" .")

    return {
        "wind": wind,
        "weather": weather + "." if weather else "N/A",
        "seas": seas,
        "raw": forecast_text,
    }