import logging
import datetime
import asyncio
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.dispatcher import async_dispatcher_send
from .weather_processing import (
    async_calculate_day_segment, 
    get_season, 
    async_get_weather_conditions, 
    async_create_dalle_prompt
)
from homeassistant.const import (
    CONF_ID,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME
)
import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from .sensor import weathercanvasaiPromptsSensor
from .weather_processing import (generate_dalle2_image, generate_dalle3_image)

from .const import (
    DOMAIN,
    CONF_MAX_IMAGES_RETAINED,
    DEFAULT_MAX_IMAGES_RETAINED,
    CONF_GPT_MODEL_NAME,
    DEFAULT_GPT_MODEL_NAME,
    CONF_SYSTEM_INSTRUCTION,
    DEFAULT_SYSTEM_INSTRUCTION,

)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "camera"] # Define the platforms that this integration supports

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the weathercanvasai component."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up weathercanvasai from a config entry."""
    _LOGGER.debug("Entering async_step_setup_entry")
    
    # Check if the integration is already fully set up
    if DOMAIN in hass.data and hass.data[DOMAIN].get('setup_complete'):
        _LOGGER.error("Weather Image Generator integration already configured and setup completed")
        return False

    # Extract configuration data from the entry
    config_data = entry.data
    # Retrieve values for entry options or use a default value
    max_images_retained = entry.options.get(CONF_MAX_IMAGES_RETAINED, DEFAULT_MAX_IMAGES_RETAINED)
    gpt_model_name = entry.options.get(CONF_GPT_MODEL_NAME, DEFAULT_GPT_MODEL_NAME)
    system_instruction = entry.options.get(CONF_SYSTEM_INSTRUCTION, DEFAULT_SYSTEM_INSTRUCTION)

    # Check if a temporary location name was stored during the config flow
    if 'temporary_location_name' in hass.data:
        location_name = hass.data.pop('temporary_location_name')
    else:
        location_name = config_data.get("location_name", "Unknown Location")

    _LOGGER.debug("Initial configuration data: %s", config_data)
    _LOGGER.debug("Options being set: max_images_retained=%s, gpt_model_name=%s, system_instruction=%s", max_images_retained, gpt_model_name, system_instruction)

    # Store the configuration data in hass.data for the domain
    hass.data[DOMAIN] = {
        "openai_api_key": config_data["openai_api_key"],
        "gpt_model_name": gpt_model_name,
        "location_name": location_name,
        "max_images_retained": max_images_retained,  # Use the value from options
        "system_instruction": system_instruction
    }

    _LOGGER.debug(f"{DOMAIN} configuration data set up: {hass.data[DOMAIN]}")
    
    # reload the configuration and options data
    entry.add_update_listener(options_update_listener)

    # Forward the setup to the sensor platform
    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

    # Define the create gpt prompt service handler
    async def create_gpt_prompt_service(call):
        # Get daypart and season
        day_segment = await async_calculate_day_segment(hass)
        now = datetime.datetime.now()
        season = get_season(now)
    
        # Retrieve the stored location name from the configuration
        location_name = hass.data[DOMAIN].get('location_name', 'Unknown Location')

        # Get weather conditions
        weather_prompt = await async_get_weather_conditions(hass)

        # Combine the information into chatgpt_in, to be sent to chatgpt next and receive chatgpt_out
        chatgpt_in = f"In {location_name}, it is {day_segment} in {season}. {weather_prompt}"

        # Log the combined information
        #_LOGGER.debug(chatgpt_in)

        # Ensure chatgpt_in is not empty
        if not chatgpt_in:
            _LOGGER.error("No input string provided for DALL-E prompt creation.")
            return

        # Log the data stored under DOMAIN
        #_LOGGER.debug(f"{DOMAIN} data: {hass.data[DOMAIN]}")
        try:
            config_data = hass.data[DOMAIN]  # Accessing the configuration data
            chatgpt_out = await async_create_dalle_prompt(hass, chatgpt_in, config_data)
            # Use chatgpt_out for further processing or return it
            _LOGGER.debug(f"DALL-E Prompt: {chatgpt_out}")
            # Dispatch the update to the sensor with new data
            async_dispatcher_send(hass, "update_weathercanvasai_sensor", {
                "chatgpt_in": chatgpt_in,
                "chatgpt_out": chatgpt_out,
            })
        except Exception as e:
            _LOGGER.error(f"Error creating DALL-E prompt: {e}")

    # Register the gpt prompt service
    hass.services.async_register(DOMAIN, 'create_chatgpt_prompt', create_gpt_prompt_service)

    # Define the "create dalle2 image" service handler
    async def create_dalle2_image_service(call):
        # Define the entity ID of the weathercanvasaiPromptsSensor
        entity_id = "sensor.weathercanvasai_prompts"

        # Retrieve the state of the weathercanvasaiPromptsSensor
        sensor_state = hass.states.get(entity_id)
        # Retrieve additional parameters from the service call
        size = call.data.get("size", "1024x1024")  # Default to 1024x1024 if not provided

        if sensor_state is None:
            _LOGGER.error(f"Entity {entity_id} not found")
            return

        # Retrieve the 'chatgpt_out' attribute from the sensor's state
        prompt = sensor_state.attributes.get("chatgpt_out")

        if not prompt:
            _LOGGER.error("No 'chatgpt_out' prompt found for DALL-E image generation")
            return

        try:
            image_url = await generate_dalle2_image(hass, prompt, size)
            if image_url:
                _LOGGER.info(f"DALL-E-2 image generated: {image_url}")
                # Dispatch the update to the camera with the real image URL
                async_dispatcher_send(hass, "update_weathercanvasai_camera")
            else:
                _LOGGER.error("Failed to generate DALL-E-2 image or invalid URL received")
        except Exception as e:
            _LOGGER.error(f"Error generating DALL-E image: {e}")

    # Register the "create dalle2 image" service
    hass.services.async_register(DOMAIN, 'create_dalle2_image', create_dalle2_image_service)

    # Define the "create dalle3 image" service handler
    async def create_dalle3_image_service(call):
        # Define the entity ID of the weathercanvasaiPromptsSensor
        entity_id = "sensor.weathercanvasai_prompts"

        # Retrieve the state of the weathercanvasaiPromptsSensor
        sensor_state = hass.states.get(entity_id)
        # Retrieve additional parameters from the service call
        size = call.data.get("size", "1024x1024")  # Default to 1024x1024 if not provided
        quality = call.data.get("quality", "standard")  # Default to 'standard' if not provided
        style = call.data.get("style", "vivid")  # Default to 'vivid' if not provided

        if sensor_state is None:
            _LOGGER.error(f"Entity {entity_id} not found")
            return

        # Retrieve the 'chatgpt_out' attribute from the sensor's state
        prompt = sensor_state.attributes.get("chatgpt_out")

        if not prompt:
            _LOGGER.error("No 'chatgpt_out' prompt found for DALL-E image generation")
            return

        try:
            image_url = await generate_dalle3_image(hass, prompt, size, quality, style)

            if image_url:
                _LOGGER.info(f"DALL-E-3 image generated: {image_url}")
                # Dispatch the update to the camera with the real image URL
                async_dispatcher_send(hass, "update_weathercanvasai_camera")
            else:
                _LOGGER.error("Failed to generate DALL-E-3 image or invalid URL received")
        except Exception as e:
            _LOGGER.error(f"Error generating DALL-E image: {e}")
            
    # Register the "create dalle3 image" service
    hass.services.async_register(DOMAIN, 'create_dalle3_image', create_dalle3_image_service)

    # Service schemas
    CREATE_DALLE2_IMAGE_SCHEMA = vol.Schema({
        vol.Optional("size", default="1024x1024"): cv.string,
    })

    CREATE_DALLE3_IMAGE_SCHEMA = vol.Schema({
        vol.Optional("size", default="1024x1024"): cv.string,
        vol.Optional("quality", default="standard"): cv.string,
        vol.Optional("style", default="vivid"): cv.string,
    })

    # Register services
    hass.services.async_register(DOMAIN, 'create_dalle2_image', create_dalle2_image_service, schema=CREATE_DALLE2_IMAGE_SCHEMA)
    hass.services.async_register(DOMAIN, 'create_dalle3_image', create_dalle3_image_service, schema=CREATE_DALLE3_IMAGE_SCHEMA)


    # At the end of the setup process, after successfully setting up
    hass.data[DOMAIN]['setup_complete'] = True
    _LOGGER.debug("Integration setup completed successfully.")

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle unloading of weathercanvasai integration."""
    unload_ok = all(
        await asyncio.gather(
            *[hass.config_entries.async_forward_entry_unload(entry, platform) for platform in PLATFORMS]
        )
    )

    # Deregister custom services
    hass.services.async_remove(DOMAIN, 'create_chatgpt_prompt')
    hass.services.async_remove(DOMAIN, 'create_dalle2_image')
    hass.services.async_remove(DOMAIN, 'create_dalle3_image')

    # Remove data stored in hass.data
    if DOMAIN in hass.data:
        hass.data.pop(DOMAIN)

    return unload_ok

async def options_update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)

