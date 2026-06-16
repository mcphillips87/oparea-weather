import requests


HEADERS = {
    "User-Agent": "AOA Weather App"
}


def get_alerts(lat, lon):
    url = f"https://api.weather.gov/alerts/active?point={lat},{lon}"

    response = requests.get(url, headers=HEADERS, timeout=10)

    if response.status_code != 200:
        return {"error": "Failed to get alerts"}

    data = response.json()

    return {
        "alerts": data.get("features", [])
    }