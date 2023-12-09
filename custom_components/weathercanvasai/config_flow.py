import logging
import json
import openai
import googlemaps
import asyncio
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .api_util import test_openai_api, test_googlemaps_api


from .const import DOMAIN


_LOGGER = logging.getLogger(__name__)

class WeatherImageGeneratorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

  
    def __init__(self):
        """Initialize the config flow."""
        self.latitude = None
        self.longitude = None

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
            # Test the OpenAI API key
            openai_test_success, openai_error = await test_openai_api(user_input['openai_api_key'])
            if not openai_test_success:
                errors['openai_api_key'] = openai_error or 'openai_api_test_fail'

            # Test the Google Maps API key and retrieve location name
            googlemaps_test_success, googlemaps_error, google_location_name = await test_googlemaps_api(self.hass, user_input['googlemaps_api_key'])
            if not googlemaps_test_success:
                errors['googlemaps_api_key'] = googlemaps_error or 'googlemaps_api_test_fail'

            if not errors:
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
            
        # Initial form for API keys and model choices
        data_schema = vol.Schema({
            vol.Required('openai_api_key', default="your openai api key here"): str,
            vol.Required('googlemaps_api_key', default="your googlemaps api key here"): str,
            vol.Required('gpt_model_name', default='gpt-3.5-turbo'): vol.In(['gpt-3.5-turbo', 'gpt-4']),
            vol.Required('max_images_retained', default=5): int,
            vol.Required('system_instruction', default="Create a succinct DALL-E prompt under 100 words, that will create an artistic image, focusing on the most visually striking aspects of the given city/region, weather, and time of day. Highlight key elements that define the scene's character, such as specific landmarks, weather effects, folkore or cultural features, in a direct and vivid manner. Avoid elaborate descriptions; instead, aim for a prompt that vividly captures the essence of the scene in a concise format, suitable for generating a distinct and compelling image."): str
            })

        # Show the form again with any errors
        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
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

class WeatherImageGeneratorOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = {
            vol.Optional('gpt_model_name', 
                         default=self.config_entry.options.get('gpt_model_name', 'gpt-3.5-turbo')): 
                         vol.In(['gpt-3.5-turbo', 'gpt-4']),
        }

        return self.async_show_form(step_id="init", data_schema=vol.Schema(options))
