from flask import Flask, render_template, request

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

source_cache = {
    "surf": {
        "data": None,
        "updated": None,
    },
    "land": {
        "data": None,
        "updated": None,
    },
    "marine": {
        "data": None,
        "updated": None,
    },
    "tides": {
        "data": None,
        "updated": None,
    },
    "alerts": {
        "data": None,
        "updated": None,
    },
    "current": {
        "data": None,
        "updated": None,
    },
    "observation": {
        "data": None,
        "updated": None,
    },
    "buoy_46224": {
        "data": None,
        "updated": None,
    },
    "buoy_46275": {
        "data": None,
        "updated": None,
    },
}

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

def format_data_age(updated_time):
    if updated_time is None:
        return "unknown age"

    now = datetime.now(ZoneInfo("America/Los_Angeles"))
    age = now - updated_time
    total_minutes = max(0, int(age.total_seconds() // 60))

    if total_minutes < 1:
        return "less than 1 minute ago"

    if total_minutes == 1:
        return "1 minute ago"

    if total_minutes < 60:
        return f"{total_minutes} minutes ago"

    hours, minutes = divmod(total_minutes, 60)

    if hours == 1:
        hour_text = "1 hour"
    else:
        hour_text = f"{hours} hours"

    if minutes == 0:
        return f"{hour_text} ago"

    minute_text = "1 minute" if minutes == 1 else f"{minutes} minutes"
    return f"{hour_text} {minute_text} ago"

def use_cached_source(source_name, live_data):
    cached = source_cache[source_name]
    live_failed = not isinstance(live_data, dict) or bool(live_data.get("error"))

    if live_failed:
        if cached["data"] is not None:
            logger.warning(
                "Using cached %s data because the live source failed.",
                source_name
            )

            updated = cached["updated"]

            return {
                "data": cached["data"],
                "stale": True,
                "updated_time": updated.strftime("%H%M %Z"),
                "age": format_data_age(updated),
            }

        return {
            "data": live_data if isinstance(live_data, dict) else {
                "error": "Source temporarily unavailable"
            },
            "stale": False,
            "updated_time": None,
            "age": None,
        }

    cached["data"] = live_data
    cached["updated"] = datetime.now(
        ZoneInfo("America/Los_Angeles")
    )

    return {
        "data": live_data,
        "stale": False,
        "updated_time": None,
        "age": None,
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
@cache.cached(timeout=600, query_string=True)
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

    test_stale_param = request.args.get("test_stale", "")
    if test_stale_param == "1":
        test_stale_param = "surf"

    # Accept one source or multiple comma-separated sources, for example:
    # /?test_stale=observation,current,buoy_46275
    test_stale_sources = {
        source.strip()
        for source in test_stale_param.split(",")
        if source.strip()
    }

    if "land" in test_stale_sources:
        land = {"error": "Temporary test failure"}
    if "marine" in test_stale_sources:
        marine = {"error": "Temporary test failure"}
    if "tides" in test_stale_sources:
        tides = {"error": "Temporary test failure"}
    if "alerts" in test_stale_sources:
        alerts = {"error": "Temporary test failure"}
    if "observation" in test_stale_sources:
        observation = {"error": "Temporary test failure"}
    if "current" in test_stale_sources:
        current = {"error": "Temporary test failure"}
    if "buoy_46224" in test_stale_sources:
        buoys[0] = {"station": "46224", "error": "Temporary test failure"}
    if "buoy_46275" in test_stale_sources:
        buoys[1] = {"station": "46275", "error": "Temporary test failure"}
    if "surf" in test_stale_sources:
        surf = {
            "san_diego_surf": "N/A",
            "error": "Temporary test failure"
        }

    source_results = {
        "land": use_cached_source("land", land),
        "marine": use_cached_source("marine", marine),
        "tides": use_cached_source("tides", tides),
        "alerts": use_cached_source("alerts", alerts),
        "observation": use_cached_source("observation", observation),
        "current": use_cached_source("current", current),
        "buoy_46224": use_cached_source("buoy_46224", buoys[0]),
        "buoy_46275": use_cached_source("buoy_46275", buoys[1]),
        "surf": use_cached_source("surf", surf),
    }

    land = source_results["land"]["data"]
    marine = source_results["marine"]["data"]
    tides = source_results["tides"]["data"]
    alerts = source_results["alerts"]["data"]
    observation = source_results["observation"]["data"]
    current = source_results["current"]["data"]
    surf = source_results["surf"]["data"]
    buoys = [
        source_results["buoy_46224"]["data"],
        source_results["buoy_46275"]["data"],
    ]

    source_labels = {
        "land": {
            "name": "NWS Land Forecast",
            "affected": "Land forecast, forecast high/low temperature, and land wind",
        },
        "marine": {
            "name": "NOAA Marine Forecast",
            "affected": "Marine weather, marine wind, and forecast seas",
        },
        "tides": {
            "name": "NOAA Tide Predictions",
            "affected": "Tide times, tide heights, and tide graph",
        },
        "alerts": {
            "name": "NWS Advisories",
            "affected": "Active advisories and warning details",
        },
        "observation": {
            "name": "Oceanside Weather Station (EW3174)",
            "affected": "Visibility and barometer",
        },
        "current": {
            "name": "Buoy 46275 Current",
            "affected": "Current direction and current speed",
        },
        "buoy_46224": {
            "name": "Buoy 46224",
            "affected": "Significant wave height and dominant wave period",
        },
        "buoy_46275": {
            "name": "Buoy 46275",
            "affected": "Significant wave height, dominant wave period, and sea temperature",
        },
        "surf": {
            "name": "NOAA Surf Forecast",
            "affected": "Surf height forecast",
        },
    }

    stale_sources = []
    for source_name, result in source_results.items():
        if result["stale"]:
            stale_sources.append({
                "name": source_labels[source_name]["name"],
                "affected": source_labels[source_name]["affected"],
                "updated_time": result["updated_time"],
                "age": result["age"],
            })

    relevant_tides = get_relevant_tides(tides)

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
        cache_epoch=cache_times["epoch"],
        stale_sources=stale_sources
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