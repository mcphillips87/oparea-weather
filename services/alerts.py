import requests

from services.http import get


def get_alerts(lat, lon):
    url = f"https://api.weather.gov/alerts/active?point={lat},{lon}"

    try:
        response = get(url)
        if response.status_code != 200:
            return {"error": "Failed to get alerts", "alerts": []}

        data = response.json()
        return {"alerts": data.get("features", [])}
    except (requests.RequestException, ValueError) as exc:
        return {"error": f"Alerts unavailable: {exc.__class__.__name__}", "alerts": []}
