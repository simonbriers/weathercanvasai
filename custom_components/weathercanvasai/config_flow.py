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
                self.max_images_retained = user_input['max_images_retained']
                self.system_instruction = self.create_system_instruction(user_input)

                # Store the location name in hass.data
                if self.hass.data.get(DOMAIN) is None:
                    self.hass.data[DOMAIN] = {}
                self.hass.data[DOMAIN]['temporary_location_name'] = google_location_name

                # Proceed to the location step
                return await self.async_step_location()

        # Initial form for API keys, chatgpmodel, number of images to be retained, ChatGP instructions
        data_schema = vol.Schema({
            vol.Required('openai_api_key', default="Enter your OpenAI API key"): str,
            vol.Required('googlemaps_api_key', default="Enter your Google Maps API key"): str,
            vol.Optional('gpt_model_name', default='gpt-3.5-turbo'): vol.In(['gpt-3.5-turbo', 'gpt-4']),
            vol.Required('max_images_retained', default=5): int,
            vol.Required('prompt_structure', default="Create a short narrative of maximum 200 words around the location, weather, and time, focusing on evoking a strong visual image. An AI will use it to create an image."): str,
            vol.Required('location_aspect', default="Describe the location in a way that highlights its unique beauty and character."): str,
            vol.Required('weather_description', default="Incorporate the weather into the narrative to enhance the mood of the scene."): str,
            vol.Required('time_of_day_effect', default="Use the time of day description to add dynamism to the lighting and atmosphere."): str,
            vol.Required('artistic_direction', default="Choose an artistic style that best conveys the scene's emotion and theme."): str,
            vol.Required('color_scheme', default="Select a color palette that complements the overall mood and setting."): str,
            vol.Required('distinct_elements', default="Emphasize any prominent features or landmarks that add significance to the image."): str,
            vol.Required('cultural_hints', default="Integrate cultural elements to enrich the story behind the image. If possible, use seasonal elements"): str,
            vol.Required('prompt_precision', default="Be precise and brief in your descriptions to guide the AI in creating a detailed and coherent image. Use captivating but as little words as possible."): str,
            vol.Required('visual_goal', default="Aim to capture the essence of the scene in a way that resonates emotionally with the viewer."): str
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

    def create_system_instruction(self, user_input):
        # Concatenate the individual fields to form the system instruction.
        parts = [
            user_input.get('prompt_structure', ''),
            user_input.get('location_aspect', ''),
            user_input.get('weather_description', ''),
            user_input.get('time_of_day_effect', ''),
            user_input.get('artistic_direction', ''),
            user_input.get('color_scheme', ''),
            user_input.get('distinct_elements', ''),
            user_input.get('cultural_hints', ''),
            user_input.get('prompt_precision', ''),
            user_input.get('visual_goal', '')
        ]
        return ' '.join(filter(None, parts))

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
