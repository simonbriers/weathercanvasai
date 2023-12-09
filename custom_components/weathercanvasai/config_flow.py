import logging
from typing import Any, Tuple
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from .api_util import test_openai_api, test_googlemaps_api
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required('openai_api_key', default= None): str,
    vol.Required('googlemaps_api_key', default= None): str,
    vol.Required('gpt_model_name', default='gpt-3.5-turbo'): vol.In(['gpt-3.5-turbo', 'gpt-4']),
    vol.Required('max_images_retained', default=5): int,
    vol.Required('system_instruction', default="Create a succinct DALL-E prompt under 100 words, that will create an artistic image, focusing on the most visually striking aspects of the given city/region, weather, and time of day. Highlight key elements that define the scene's character, such as specific landmarks, weather effects, folklore or cultural features, in a direct and vivid manner. Avoid elaborate descriptions; instead, aim for a prompt that vividly captures the essence of the scene in a concise format, suitable for generating a distinct and compelling image."): str
})

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> Tuple[bool, str, str, str]:
    openai_api_key = data['openai_api_key']
    googlemaps_api_key = data['googlemaps_api_key']

    # Test the OpenAI API key
    openai_test_success, openai_error = await test_openai_api(openai_api_key)
    if not openai_test_success:
        return False, openai_error or 'openai_api_test_fail', '', None

    # Test the Google Maps API key
    googlemaps_test_success, googlemaps_error, google_location_name = await test_googlemaps_api(hass, googlemaps_api_key)
    if not googlemaps_test_success:
        return False, '', googlemaps_error or 'googlemaps_api_test_fail', None

    # If both tests pass, return success along with the location name
    return True, '', '', google_location_name


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for generating Weather Images."""

    VERSION = 1
  
    def __init__(self):
        """Initialize the config flow."""

    async def async_step_user(self, user_input=None):
        """Handle the initial user input configuration step."""
        errors = {}

        # Check the number of current entries and abort if any exists
        current_entries = self._async_current_entries()
        _LOGGER.debug(f"Current entries: {current_entries}")
        if len(current_entries) > 0:
            errors["base"] = "single_instance_allowed"
            return self.async_show_form(step_id="user", errors=errors)

        if user_input is not None:
            success, openai_error, googlemaps_error, google_location_name = await validate_input(self.hass, user_input)

            if not success:
                # Add specific errors for each API key if validation fails
                if openai_error:
                    errors['openai_api_key'] = openai_error
                if googlemaps_error:
                    errors['googlemaps_api_key'] = googlemaps_error

                # Redisplay the form with errors
                return self.async_show_form(
                    step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
                )
            else:
                # Store the valid API keys, model choices, and location name temporarily
                self.openai_api_key = user_input['openai_api_key']
                self.googlemaps_api_key = user_input['googlemaps_api_key']
                self.gpt_model_name = user_input['gpt_model_name']
                self.max_images_retained = user_input['max_images_retained']
                self.system_instruction = user_input['system_instruction']

                # Store the location name in hass.data
                if self.hass.data.get(DOMAIN) is None:
                    self.hass.data[DOMAIN] = {}
                self.hass.data[DOMAIN]['temporary_location_name'] = google_location_name

                # Proceed to the location step
                return await self.async_step_location()
            
 
        # Show the form again with any errors
        return self.async_show_form(
            step_id="user", data_schema= STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_location(self, user_input=None):
        """Handle the location configuration step."""
        errors = {}

        if user_input is not None:
            # Use the stored location name
            location_name = self.hass.data[DOMAIN].get('temporary_location_name', "Unknown Location")

            # Create the final configuration with the user-provided or stored location name
            final_configuration = {
                'openai_api_key': self.openai_api_key,
                'googlemaps_api_key': self.googlemaps_api_key,
                'gpt_model_name': self.gpt_model_name,
                'location_name': user_input.get('location_name', location_name),
                'max_images_retained': self.max_images_retained,
                'system_instruction': self.system_instruction
            }

            # Create the configuration entry
            return self.async_create_entry(title="Weather Canvas AI", data=final_configuration)

        # Form for finalizing location
        stored_location_name = self.hass.data[DOMAIN].get('temporary_location_name', "Enter location")
        data_schema = vol.Schema({
            vol.Required('location_name', default=stored_location_name): str,
        })

        # Show the form again with any errors
        return self.async_show_form(
            step_id="location", data_schema=data_schema, errors=errors
        )
