import requests

from services.http import get


def clean(value):
    if value in ["MM", "999", "999.0", "99.0", None]:
        return "N/A"
    return value


def meters_to_feet(value):
    try:
        return round(float(value) * 3.28084, 1)
    except (ValueError, TypeError):
        return "N/A"


def get_buoy_wave_data(station):
    url = f"https://www.ndbc.noaa.gov/data/realtime2/{station}.txt"
    fallback = {
        "station": station,
        "wave_height": "N/A",
        "dominant_period": "N/A",
        "average_period": "N/A",
        "water_temp": "N/A",
    }

    try:
        response = get(url)
        if response.status_code != 200:
            return {**fallback, "error": f"Failed to get wave data for {station}"}

        lines = response.text.splitlines()
        if len(lines) < 3:
            return {**fallback, "error": f"No wave data for {station}"}

        headers = lines[0].replace("#", "").split()
        for line in lines[2:30]:
            values = line.split()
            if len(values) < len(headers):
                continue

            data = dict(zip(headers, values))
            raw_wave = data.get("WVHT")
            if clean(raw_wave) != "N/A":
                return {
                    "station": station,
                    "wave_height": meters_to_feet(raw_wave),
                    "dominant_period": clean(data.get("DPD")),
                    "average_period": clean(data.get("APD")),
                    "water_temp": clean(data.get("WTMP")),
                }

        return fallback
    except requests.RequestException as exc:
        return {**fallback, "error": f"Wave data unavailable: {exc.__class__.__name__}"}


def get_buoy_current_data(station):
    url = f"https://www.ndbc.noaa.gov/data/realtime2/{station}.adcp"
    fallback = {
        "station": station,
        "direction": "N/A",
        "speed_cms": "N/A",
        "speed_knots": "N/A",
        "depth_bin": "N/A",
    }

    try:
        response = get(url)
        if response.status_code != 200:
            return {**fallback, "error": f"Failed to get current data for {station}"}

        lines = response.text.splitlines()
        if len(lines) < 3:
            return {**fallback, "error": f"No current data for {station}"}

        headers = lines[0].replace("#", "").split()
        values = lines[2].split()
        data = dict(zip(headers, values))
        speed_cms = clean(data.get("SPD01"))

        try:
            speed_knots = round(float(speed_cms) * 0.0194384, 2) if speed_cms != "N/A" else "N/A"
        except (ValueError, TypeError):
            speed_knots = "N/A"

        return {
            "station": station,
            "year": data.get("YY"),
            "month": data.get("MM"),
            "day": data.get("DD"),
            "hour": data.get("hh"),
            "minute": data.get("mm"),
            "depth_bin": clean(data.get("DEP01")),
            "direction": clean(data.get("DIR01")),
            "speed_cms": speed_cms,
            "speed_knots": speed_knots,
        }
    except requests.RequestException as exc:
        return {**fallback, "error": f"Current data unavailable: {exc.__class__.__name__}"}
