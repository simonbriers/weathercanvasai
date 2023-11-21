import logging
from homeassistant.core import HomeAssistant
import datetime
import asyncio
import pytz

_LOGGER = logging.getLogger(__name__)

async def generate_weather_prompt(hass, entity_id):
    weather_data = hass.states.get(entity_id).attributes # Fetch Met.no weather data
    sun_state = hass.states.get('sun.sun').state # Determine sun position,'above_horizon' or 'below_horizon'
    now = datetime.now()
    season = get_season(now)

async def get_season(now):
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

    # Get current time in UTC
    now = datetime.datetime.now(datetime.timezone.utc)

    # Get sunrise and sunset times from sun integration
    sun_state = hass.states.get('sun.sun')
    sunrise = sun_state.attributes.get('next_rising')
    sunset = sun_state.attributes.get('next_setting')

    # Check if sunrise and sunset times are available
    if sunrise is None or sunset is None:
        _LOGGER.error("Sunrise or sunset time is not available.")
        return "Unknown time"

    try:
        # Parse sunrise and sunset into datetime objects
        sunrise_time = datetime.datetime.fromisoformat(sunrise)
        sunset_time = datetime.datetime.fromisoformat(sunset)
    except Exception as e:
        _LOGGER.error(f"Error parsing sunrise/sunset time: {e}")
        return "Unknown time"

    # Calculate the fraction of the day or night
    if now < sunrise_time:
        fraction = (now - sunrise_time).total_seconds() / (24 * 3600)
    elif now > sunset_time:
        fraction = (now - sunset_time).total_seconds() / (24 * 3600) + 1
    else:
        day_length = (sunset_time - sunrise_time).total_seconds()
        fraction = (now - sunrise_time).total_seconds() / day_length

    # Find the matching description in the lookup table
    for key, description in lookup_table.items():
        lower_bound, upper_bound = key.split('-')
        if lower_bound.endswith('+'):
            if fraction >= float(lower_bound[:-1]):
                return description
        elif float(lower_bound) <= fraction < float(upper_bound):
            return description

    return "Unknown time"

