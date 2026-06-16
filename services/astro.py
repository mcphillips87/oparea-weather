from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo

from astral import LocationInfo
from astral import Depression
from astral.sun import sun
from astral.moon import moonrise, moonset

import ephem


def get_current_moon_illumination():
    local_now = datetime.now(ZoneInfo("America/Los_Angeles"))
    moon = ephem.Moon(local_now)

    return round(moon.phase, 1)


def get_night_illumination():
    now = datetime.now(ZoneInfo("America/Los_Angeles"))

    if now.hour < 5:
        target_date = now.date() - timedelta(days=1)
    else:
        target_date = now.date()

    target_noon = datetime(
        target_date.year,
        target_date.month,
        target_date.day,
        12, 0, 0,
        tzinfo=ZoneInfo("America/Los_Angeles")
    )

    moon = ephem.Moon(target_noon)

    return round(moon.phase, 1)

def get_hourly_moon_data(lat, lon):
    now = datetime.now(ZoneInfo("America/Los_Angeles"))

    start = now.replace(hour=18, minute=0, second=0, microsecond=0)

    if now.hour < 5:
        start = start - timedelta(days=1)

    hourly_data = []

    for i in range(13):  # 1800 to 0600
        sample_time = start + timedelta(hours=i)

        moon = ephem.Moon(sample_time)

        observer = ephem.Observer()
        observer.lat = str(lat)
        observer.lon = str(lon)
        observer.date = sample_time.astimezone(ZoneInfo("UTC"))

        moon.compute(observer)

        moon_up = moon.alt > 0

        hourly_data.append({
            "time": sample_time.strftime("%H%M"),
            "illumination": round(moon.phase, 1),
            "moon_up": moon_up
        })

    return hourly_data
def get_sun_moon(lat, lon):
    location = LocationInfo(
        name="CPAOA",
        region="CA",
        timezone="America/Los_Angeles",
        latitude=lat,
        longitude=lon
    )

    today = date.today()
    tomorrow = today + timedelta(days=1)

    today_sun = sun(location.observer, date=today, tzinfo=location.timezone)
    tomorrow_sun = sun(location.observer, date=tomorrow, tzinfo=location.timezone)

    moonrise_today = moonrise(location.observer, date=today, tzinfo=location.timezone)
    moonset_today = moonset(location.observer, date=today, tzinfo=location.timezone)

    moonrise_tomorrow = moonrise(location.observer, date=tomorrow, tzinfo=location.timezone)
    moonset_tomorrow = moonset(location.observer, date=tomorrow, tzinfo=location.timezone)

    moon_current = get_current_moon_illumination()

    moon_night_max = get_night_illumination()

    hourly_moon = get_hourly_moon_data(lat, lon)

    civil = sun(
        location.observer,
        date=today,
        tzinfo=location.timezone,
        dawn_dusk_depression=Depression.CIVIL
    )

    nautical = sun(
        location.observer,
        date=today,
        tzinfo=location.timezone,
        dawn_dusk_depression=Depression.NAUTICAL
    )

    astronomical = sun(
        location.observer,
        date=today,
        tzinfo=location.timezone,
        dawn_dusk_depression=Depression.ASTRONOMICAL
    )

    return {
        "sunrise": today_sun["sunrise"].strftime("%H%M"),
        "sunset": today_sun["sunset"].strftime("%H%M"),
        "moonrise_today": moonrise_today.strftime("%H%M") if moonrise_today else "N/A",
        "moonset_today": moonset_today.strftime("%H%M") if moonset_today else "N/A",
        "moonrise_tomorrow": moonrise_tomorrow.strftime("%H%M") if moonrise_tomorrow else "N/A",
        "moonset_tomorrow": moonset_tomorrow.strftime("%H%M") if moonset_tomorrow else "N/A",
        "moon_current": moon_current,
        "moon_night_max": moon_night_max,
        "hourly_moon": hourly_moon,
        "civil_dawn": civil["dawn"].strftime("%H%M"),
        "nautical_dawn": nautical["dawn"].strftime("%H%M"),
        "astronomical_dawn": astronomical["dawn"].strftime("%H%M"),
        "civil_dusk": civil["dusk"].strftime("%H%M"),
        "nautical_dusk": nautical["dusk"].strftime("%H%M"),
        "astronomical_dusk": astronomical["dusk"].strftime("%H%M"),
    }