import logging
import datetime
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN
from .weather_processing import async_calculate_day_segment, get_season


_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the weather_image_generator component."""
    # Placeholder for your component setup logic, if needed
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up weather_image_generator from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    config_data = entry.data

    # Store the configuration data in hass.data for later use
    hass.data[DOMAIN][entry.entry_id] = {
        "openai_api_key": config_data.get("openai_api_key"),
        "image_model_name": config_data.get("image_model_name"),
        "gpt_model_name": config_data.get("gpt_model_name"),
    }

    # Define the weather2img service handler
    async def handle_weather2img(call):
        # Retrieve configuration data
        service_data = hass.data[DOMAIN][entry.entry_id]

    # Register the weather2img service
    hass.services.async_register(DOMAIN, 'weather2img', handle_weather2img)

    # Define the test_servive handler
    async def handle_test_service(call):
        # Call your function and log the result
        day_segment = await async_calculate_day_segment(hass)
        now = datetime.datetime.now()
        season = get_season(now)
        _LOGGER.info(f"Calculated Day Segment and season: {day_segment} in {season}")

    hass.services.async_register(DOMAIN, 'test_day_segment', handle_test_service)

    return True
