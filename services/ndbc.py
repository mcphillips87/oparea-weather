import requests


def clean(value):
    if value in ["MM", "999", "999.0", "99.0"]:
        return "N/A"
    return value

def meters_to_feet(value):
    try:
        return round(float(value) * 3.28084, 1)
    except (ValueError, TypeError):
        return "N/A"

def get_buoy_wave_data(station):
    url = f"https://www.ndbc.noaa.gov/data/realtime2/{station}.txt"
    response = requests.get(url, timeout=10)

    if response.status_code != 200:
        return {"error": f"Failed to get wave data for {station}"}

    lines = response.text.splitlines()

    if len(lines) < 3:
        return {"error": f"No wave data for {station}"}

    headers = lines[0].replace("#", "").split()
    values = lines[2].split()

    data = dict(zip(headers, values))

    return {
        "station": station,
        "wave_height": meters_to_feet(clean(data.get("WVHT"))),
        "dominant_period": clean(data.get("DPD")),
        "average_period": clean(data.get("APD")),
        "water_temp": clean(data.get("WTMP")),
    }


def get_buoy_current_data(station):
    url = f"https://www.ndbc.noaa.gov/data/realtime2/{station}.adcp"
    response = requests.get(url, timeout=10)

    if response.status_code != 200:
        return {"error": f"Failed to get current data for {station}"}

    lines = response.text.splitlines()

    if len(lines) < 3:
        return {"error": f"No current data for {station}"}

    headers = lines[0].replace("#", "").split()
    values = lines[2].split()

    data = dict(zip(headers, values))

    speed_cms = clean(data.get("SPD01"))

    if speed_cms != "N/A":
        speed_knots = round(float(speed_cms) * 0.0194384, 2)
    else:
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