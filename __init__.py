import logging
import datetime
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.dispatcher import async_dispatcher_send
from .const import DOMAIN
from .weather_processing import async_calculate_day_segment, get_season, async_get_home_zone_address, async_get_weather_conditions, async_create_dalle_prompt
from homeassistant.const import (
    CONF_ID,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
)

from .sensor import Weather2ImgPromptsSensor

_LOGGER = logging.getLogger(__name__)

# Define the platforms that this integration supports
PLATFORMS = ["sensor","camera"]

# Define the update_listener function
async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    _LOGGER.info("Configuration options updated. Reloading integration.")
    await hass.config_entries.async_reload(entry.entry_id)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the weather_image_generator component."""
    # Placeholder for your component setup logic, if needed
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up weather_image_generator from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    config_data = entry.data

    # Check if a temporary location name was stored during the config flow
    if 'temporary_location_name' in hass.data[DOMAIN]:
        # Use the temporary location name if available
        location_name = hass.data[DOMAIN].pop('temporary_location_name')
    else:
        # Otherwise, use the location name from the config entry, or a default value
        location_name = config_data.get("location_name", "Unknown Location")

    # Store the configuration data in hass.data for later use
    hass.data[DOMAIN][entry.entry_id] = {
        "openai_api_key": config_data.get("openai_api_key"),
        "image_model_name": config_data.get("image_model_name"),
        "gpt_model_name": config_data.get("gpt_model_name"),
        "location_name": location_name
    }
    # Log the data stored under DOMAIN
    _LOGGER.debug(f"{DOMAIN} data: {hass.data[DOMAIN]}")

    # Define the weather2img service handler
    async def handle_weather2img(call):
        # Dummy URL for testing
        dummy_url = "https://via.placeholder.com/300.png?text=Dalle+Test"

        # Dispatch the update to the camera with the dummy URL
        async_dispatcher_send(hass, "update_dalle_weather_image_camera", dummy_url)

    # Register the weather2img service
    hass.services.async_register(DOMAIN, 'weather2img', handle_weather2img)

    # Define the create gpt prompt service handler
    async def create_gpt_prompt_service(call):
        # Get daypart and season
        day_segment = await async_calculate_day_segment(hass)
        now = datetime.datetime.now()
        season = get_season(now)
        
        # Retrieve the stored location name
        location_name = hass.data[DOMAIN][entry.entry_id].get('location_name', 'Unknown Location')

        # Get weather conditions
        weather_prompt = await async_get_weather_conditions(hass)

        # Combine the information into chatgpt_in, to be sent to chatgpt next and receive chatgpt_out
        chatgpt_in = f"In {location_name}, it is {day_segment} in {season}. {weather_prompt}"

        # Log the combined information
        _LOGGER.debug(chatgpt_in)

        # Ensure chatgpt_in is not empty
        if not chatgpt_in:
            _LOGGER.error("No input string provided for DALL-E prompt creation.")
            return

        # Call the function to create the DALL-E prompt
        # Log the data stored under DOMAIN
        #_LOGGER.debug(f"{DOMAIN} data: {hass.data[DOMAIN]}")
        try:
            config_data = hass.data[DOMAIN][entry.entry_id]
            chatgpt_out = await async_create_dalle_prompt(hass, chatgpt_in, config_data)
            # Use chatgpt_out for further processing or return it
            _LOGGER.debug(f"DALL-E Prompt: {chatgpt_out}")
            # Dispatch the update to the sensor with new data
            async_dispatcher_send(hass, "update_weather_image_generator_sensor", {
                "chatgpt_in": chatgpt_in,
                "chatgpt_out": chatgpt_out,
            })
        except Exception as e:
            _LOGGER.error(f"Error creating DALL-E prompt: {e}")

    # Register the gpt prompt service
    hass.services.async_register(DOMAIN, 'create_chatgpt_prompt', create_gpt_prompt_service)
    
    # Forward the setup to the sensor platform
    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

    return True
