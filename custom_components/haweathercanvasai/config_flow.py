import logging
import openai
import googlemaps
import asyncio
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from .const import DOMAIN
import json

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
            openai_test_success, openai_error = await self.test_openai_api(user_input['openai_api_key'], user_input['gpt_model_name'])
            if not openai_test_success:
                errors['openai_api_key'] = openai_error or 'openai_api_test_fail'

            # Test the Google Maps API key and retrieve location name
            # Retrieve the latitude and longitude from Home Assistant's core configuration
            self.latitude = self.hass.config.latitude
            self.longitude = self.hass.config.longitude

            googlemaps_test_success, googlemaps_error, google_location_name = await self.test_googlemaps_api(user_input['googlemaps_api_key'])
            if not googlemaps_test_success:
                errors['googlemaps_api_key'] = googlemaps_error or 'googlemaps_api_test_fail'

            if not errors:
                # Store the valid API keys, model choices, and location name temporarily
                self.openai_api_key = user_input['openai_api_key']
                self.googlemaps_api_key = user_input['googlemaps_api_key']
                self.gpt_model_name = user_input['gpt_model_name']
                self.image_model_name = user_input['image_model_name']

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
            vol.Optional('gpt_model_name', default='gpt-3.5-turbo'): vol.In(['gpt-3.5-turbo', 'gpt-4']),
            vol.Optional('image_model_name', default='dall-e-2'): vol.In(['dall-e-2', 'dall-e-3']),
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
                'image_model_name': self.image_model_name,
                'location_name': user_input.get('location_name', location_name)
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

    async def test_openai_api(self, api_key, gpt_model_name):
        try:
            def make_api_call():
                openai.api_key = api_key
                return openai.ChatCompletion.create(
                    model=gpt_model_name, 
                    messages=[{"role": "user", "content": "Say Test"}]
                )
            completion = await self.hass.async_add_executor_job(make_api_call)
            #_LOGGER.debug('OpenAI API response: %s', completion)
            return True, None
        except Exception as e:
            _LOGGER.error('Error testing OpenAI API: %s', e)
            return False, str(e)

    async def test_googlemaps_api(self, googlemaps_api_key):
        try:
            # Initialize the Google Maps client
            gmaps = googlemaps.Client(key=googlemaps_api_key)

            # Define a local function for the blocking call
            def _reverse_geocode():
                test_location = (self.latitude, self.longitude)
                return gmaps.reverse_geocode(test_location)

            # Perform a simple reverse geocode test
            googlemaps_response = await self.hass.async_add_executor_job(_reverse_geocode)

            if googlemaps_response:
                formatted_location_name = self.format_location_name(googlemaps_response)
                return True, None, formatted_location_name
            else:
                return False, "No response from Google Maps API", None

        except Exception as e:
            _LOGGER.error('Error testing Google Maps API: %s', e)
            return False, str(e), None

    def format_location_name(self, geocode_result):
        # Initialize variables
        locality = province = region = country = None
        # Iterate through address components to find required information
        for component in geocode_result[0]['address_components']:
            if 'locality' in component['types']:
                locality = component['long_name']
            elif 'administrative_area_level_2' in component['types']:
                province = component['long_name']
            elif 'administrative_area_level_1' in component['types']:
                region = component['long_name']
            elif 'country' in component['types']:
                country = component['long_name']

        # Construct location name
        parts = [locality, province, region, country]
        location_name = ', '.join(filter(None, parts))
        return location_name

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
            vol.Optional('image_model_name', 
                         default=self.config_entry.options.get('image_model_name', 'dall-e-2')): 
                         vol.In(['dall-e-2', 'dall-e-3'])
        }

        return self.async_show_form(step_id="init", data_schema=vol.Schema(options))