import logging
from homeassistant.core import HomeAssistant
import datetime
import asyncio
import pytz

_LOGGER = logging.getLogger(__name__)

async def generate_weather_prompt(hass, entity_id):
    weather_data = hass.states.get(entity_id).attributes # Fetch Met.no weather data
    
def get_season(now):
    month = now.month
    if 3 <= month <= 5:
        return 'Spring'
    elif 6 <= month <= 8:
        return 'Summer'
    elif 9 <= month <= 11:
        return 'Autumn'
    else:
        return 'Winter'

async def async_calculate_day_segment(hass: HomeAssistant) -> str:
    """Calculate the current segment of the day based on sunrise and sunset times."""

    # Internal lookup table for time of day
    lookup_table = {
        "0.0-0.1": "early morning",
        "0.1-0.2": "morning",
        "0.2-0.3": "mid-morning",
        "0.3-0.4": "late morning",
        "0.4-0.5": "around noon",
        "0.5-0.6": "early afternoon",
        "0.6-0.7": "mid-afternoon",
        "0.7-0.8": "late afternoon",
        "0.8-0.9": "early evening",
        "0.9-1.0": "evening",
        "1.0-1.1": "getting dark",
        "1.1-1.2": "night",
        "1.2-1.3": "late at night",
        "1.3-1.4": "the deep night",
        "1.4-1.5": "the early hours",
        "1.5+": "the darkest hour"
    }

    now = datetime.datetime.now(datetime.timezone.utc).time()

    sun_state = hass.states.get('sun.sun')
    sunrise = datetime.datetime.fromisoformat(sun_state.attributes.get('next_rising')).time()
    sunset = datetime.datetime.fromisoformat(sun_state.attributes.get('next_setting')).time()

    # Determine if it's day or night
    if sunrise < now < sunset:
        # It's day
        day_length = datetime.datetime.combine(datetime.date.today(), sunset) - datetime.datetime.combine(datetime.date.today(), sunrise)
        time_passed = datetime.datetime.combine(datetime.date.today(), now) - datetime.datetime.combine(datetime.date.today(), sunrise)
    else:
        # It's night
        if now < sunrise:
            # Before sunrise, calculate time since yesterday's sunset
            yesterday_sunset = sunset - datetime.timedelta(days=1)
            day_length = datetime.datetime.combine(datetime.date.today(), sunrise) - datetime.datetime.combine(datetime.date.today(), yesterday_sunset)
            time_passed = datetime.datetime.combine(datetime.date.today(), now) - datetime.datetime.combine(datetime.date.today(), yesterday_sunset)
        else:
            # After sunset, calculate time until tomorrow's sunrise
            tomorrow_sunrise = sunrise + datetime.timedelta(days=1)
            day_length = datetime.datetime.combine(datetime.date.today(), tomorrow_sunrise) - datetime.datetime.combine(datetime.date.today(), sunset)
            time_passed = datetime.datetime.combine(datetime.date.today(), now) - datetime.datetime.combine(datetime.date.today(), sunset)

    fraction = time_passed / day_length
    # Find the matching description in the lookup table
    _LOGGER.info(f"Current time: {now}")
    _LOGGER.info(f"Fraction of the day: {fraction}")

    for key, description in lookup_table.items():
    # Existing comparison logic...
        if '+' in key:  # Handle open-ended ranges like '1.5+'
            lower_bound = key[:-1]  # Remove the '+' and get the number
            if fraction >= float(lower_bound):
                return description
        else:
            lower_bound, upper_bound = key.split('-')
            if float(lower_bound) <= fraction < float(upper_bound):
                return description
    return "Unknown time"

