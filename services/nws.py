import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "CPAOA Weather App (mcphillips87@gmail.com)"
}

def get_forecast(lat, lon):
    # First get the forecast URL for the coordinates
    point_url = f"https://api.weather.gov/points/{lat},{lon}"
    point_response = requests.get(point_url)

    if point_response.status_code != 200:
        return {"error": "Failed to get point data"}

    point_data = point_response.json()

    forecast_url = point_data["properties"]["forecast"]

    # Pull the actual forecast
    forecast_response = requests.get(forecast_url)

    if forecast_response.status_code != 200:
        return {"error": "Failed to get forecast"}

    return forecast_response.json()

def get_current_observation(station_id):
    url = "https://forecast.weather.gov/MapClick.php?lat=33.20983&lon=-117.39433"

    response = requests.get(url, headers=HEADERS, timeout=10)

    if response.status_code != 200:
        return {
            "station": station_id,
            "visibility_nm": "UNR",
            "barometer_inhg": "N/A"
        }

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