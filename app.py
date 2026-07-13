from flask import Flask, render_template

from services.nws import get_forecast, get_current_observation
from services.marine import get_marine_point_forecast, parse_marine_forecast
from services.ndbc import get_buoy_wave_data, get_buoy_current_data
from services.tides import get_tide_predictions
from services.alerts import get_alerts
from services.astro import get_sun_moon
from flask_caching import Cache
from datetime import datetime
import logging
from zoneinfo import ZoneInfo
from services.surf import get_surf_forecast

app = Flask(__name__)
logger = logging.getLogger(__name__)

cache = Cache(app, config={"CACHE_TYPE": "SimpleCache"})

def mph_to_knots(wind_text):
    parts = wind_text.split()

    converted = []

    for part in parts:
        try:
            mph = float(part)
            knots = round(mph * 0.868976, 1)
            converted.append(str(knots))
        except ValueError:
            converted.append(part)

    return " ".join(converted).replace("mph", "kt")


def c_to_f(temp_c):
    try:
        return round((float(temp_c) * 9/5) + 32, 1)
    except (ValueError, TypeError):
        return "N/A"

def get_cache_times():
    now = datetime.now(ZoneInfo("America/Los_Angeles"))
    return {
        "display": now.strftime("%d %b %Y %H%M"),
        "epoch": int(now.timestamp())
    }

def get_relevant_tides(tides):
    """
    Returns the last completed tide plus the next 3 upcoming tides.
    Tide times from NOAA are local because services.tides uses lst_ldt.
    """
    if tides.get("error"):
        return []

    now = datetime.now(ZoneInfo("America/Los_Angeles"))
    predictions = tides.get("predictions", [])

    past = []
    future = []

    for tide in predictions:
        try:
            tide_time = datetime.strptime(tide["t"], "%Y-%m-%d %H:%M")
            tide_time = tide_time.replace(tzinfo=ZoneInfo("America/Los_Angeles"))
        except (KeyError, ValueError, TypeError):
            continue

        if tide_time <= now:
            past.append(tide)
        else:
            future.append(tide)

    relevant = []

    if past:
        relevant.append(past[-1])

    relevant.extend(future[:3])

    return relevant

CPAOA = {
    "name": "Camp Pendleton Amphibious Operation Area",
    "land": {
        "lat": 33.25,
        "lon": -117.42
    },
    "marine": {
        "lat": 33.22,
        "lon": -117.50
    },
    "buoys": [
        "46224",
        "46275"
    ],
    "tide": {
        "station": "TWC0419"
    },
    "station": "EW3174"
}

@app.route("/")
@cache.cached(timeout=600)
def home():
    cache_times = get_cache_times()

    land = get_forecast(
        CPAOA["land"]["lat"],
        CPAOA["land"]["lon"]
    )

    marine = get_marine_point_forecast(
        CPAOA["marine"]["lat"],
        CPAOA["marine"]["lon"]
    )

    buoys = []
    for station in CPAOA["buoys"]:
        buoys.append(get_buoy_wave_data(station))

    current = get_buoy_current_data("46275")

    tides = get_tide_predictions(
        CPAOA["tide"]["station"],
        days=7,
        days_back=1
    )

    relevant_tides = get_relevant_tides(tides)

    alerts = get_alerts(
        CPAOA["land"]["lat"],
        CPAOA["land"]["lon"]
    )

    try:
        astro = get_sun_moon(
            CPAOA["land"]["lat"],
            CPAOA["land"]["lon"]
        )
    except Exception:
        logger.exception("Astronomy calculation failed")
        astro = {
            "sunrise": "N/A", "sunset": "N/A",
            "moonrise_today": "N/A", "moonset_today": "N/A",
            "moonrise_tomorrow": "N/A", "moonset_tomorrow": "N/A",
            "moon_current": "N/A", "moon_night_max": "N/A",
            "hourly_moon": [], "civil_dawn": "N/A",
            "nautical_dawn": "N/A", "astronomical_dawn": "N/A",
            "civil_dusk": "N/A", "nautical_dusk": "N/A",
            "astronomical_dusk": "N/A",
        }

    observation = get_current_observation(
        CPAOA["station"]
    )

    surf = get_surf_forecast()

    land_periods = land.get("properties", {}).get("periods", [])
    marine_periods = marine.get("periods", [])

    first_land = land_periods[0] if land_periods else {}
    first_marine = marine_periods[0] if marine_periods else {}
    parsed_marine = parse_marine_forecast(first_marine.get("forecast", ""))

    buoy_46224 = next((b for b in buoys if b.get("station") == "46224"), {})
    buoy_46275 = next((b for b in buoys if b.get("station") == "46275"), {})

    brief = {
        "weather_forecast": first_land.get("shortForecast", "N/A").upper(),
        "visibility": f"{observation.get('visibility_nm', 'N/A')} NM",
        "barometer": f"{observation.get('barometer_inhg', 'N/A')} inHg",
        "low_temp": first_land.get("temperature", "N/A"),
        "high_temp": land_periods[1].get("temperature", "N/A") if len(land_periods) > 1 else "N/A",
        "sea_temp": c_to_f(buoy_46275.get("water_temp", "N/A")),
        "land_wind": mph_to_knots(
            f"{first_land.get('windDirection', 'N/A')} {first_land.get('windSpeed', 'N/A')}"
        ),
        "sea_wind": parsed_marine["wind"],
        "marine_weather": parsed_marine["weather"],
        "seas": parsed_marine["seas"],
        "buoy_46224": f"{buoy_46224.get('wave_height', 'N/A')} ft @ {buoy_46224.get('dominant_period', 'N/A')} sec",
        "buoy_46275": f"{buoy_46275.get('wave_height', 'N/A')} ft @ {buoy_46275.get('dominant_period', 'N/A')} sec",
        "current": f"{current.get('direction', 'N/A')}° @ {current.get('speed_knots', 'N/A')} kt ({current.get('speed_cms', 'N/A')} cm/s)",
        "tides": tides,
        "relevant_tides": relevant_tides,
        "surf_height": surf.get("san_diego_surf", "N/A"),
        "alerts": alerts,
        "astro": astro,
    }

    return render_template(
        "index.html",
        oparea=CPAOA,
        brief=brief,
        cache_time=cache_times["display"],
        cache_epoch=cache_times["epoch"]
    )

@app.route("/data")
@cache.cached(timeout=600)
def data():
    cache_times = get_cache_times()

    land = get_forecast(
        CPAOA["land"]["lat"],
        CPAOA["land"]["lon"]
    )

    marine = get_marine_point_forecast(
        CPAOA["marine"]["lat"],
        CPAOA["marine"]["lon"]
    )

    alerts = get_alerts(
        CPAOA["land"]["lat"],
        CPAOA["land"]["lon"]
    )

    tides = get_tide_predictions(
        CPAOA["tide"]["station"],
        days=7
    )

    surf = get_surf_forecast()

    buoys = []
    for station in CPAOA["buoys"]:
        buoys.append(get_buoy_wave_data(station))

    current = get_buoy_current_data("46275")

    land_periods = land.get("properties", {}).get("periods", [])[:6]
    marine_periods = marine.get("periods", [])[:6]

    forecast_periods = []

    for i in range(min(len(land_periods), len(marine_periods))):
        forecast_periods.append({
            "land": land_periods[i],
            "marine": marine_periods[i]
        })

    return render_template(
        "data.html",
        oparea=CPAOA,
        alerts=alerts,
        forecast_periods=forecast_periods,
        buoys=buoys,
        current=current,
        tides=tides,
        surf=surf,
        cache_time=cache_times["display"],
        cache_epoch=cache_times["epoch"]
    )

@app.route("/today")
def today():
    cache_times = get_cache_times()
    return render_template(
        "coming_soon.html",
        page_title="Today",
        cache_time=cache_times["display"],
        cache_epoch=cache_times["epoch"]
    )

@app.route("/tomorrow")
def tomorrow():
    cache_times = get_cache_times()
    return render_template(
        "coming_soon.html",
        page_title="Tomorrow",
        cache_time=cache_times["display"],
        cache_epoch=cache_times["epoch"]
    )

if __name__ == "__main__":
    app.run()