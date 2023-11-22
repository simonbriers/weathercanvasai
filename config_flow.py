import logging
import openai
import asyncio
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Test logging messages at various levels

class WeatherImageGeneratorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    
    def __init__(self):
        """Initialize the config flow."""
        self.latitude = None
        self.longitude = None

    async def async_step_user(self, user_input=None):
        """Handle a config flow initiated by the user."""
        # Retrieve the latitude and longitude from Home Assistant's core configuration
        if self.hass:
            self.latitude = self.hass.config.latitude
            self.longitude = self.hass.config.longitude

        errors = {}

        # Define your data schema for the form with default values
        data_schema = vol.Schema({
            vol.Required('openai_api_key', default="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"): str,
            vol.Optional('image_model_name', default='dall-e-2'): vol.In(['dall-e-2', 'dall-e-3']),
            vol.Optional('gpt_model_name', default='gpt-3.5-turbo'): vol.In(['gpt-3.5-turbo', 'gpt-4']),
        })

        if user_input is not None:
            gpt_model_name = user_input.get('gpt_model_name', 'gpt-3.5-turbo')  # Get the GPT model name or default
            openai_test_success, openai_error = await self.test_openai_api(user_input['openai_api_key'], gpt_model_name)
            
            # Check the results of the API tests and set errors if they failed
            if not openai_test_success:
                errors['openai_api_key'] = openai_error or 'openai_api_test_fail'
            
            # If there are no errors, proceed to create the config entry
            if not errors:
                #_LOGGER.info("API test to ChatGPT passed. Ready to create config entry.")
                # Placeholder for creating config entry
                return self.async_create_entry(title="Weather Image Generator", data=user_input)

        # Show the form again with any errors
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)


    async def test_openai_api(self, api_key, gpt_model_name):
        try:
            def make_api_call():
                openai.api_key = api_key
                return openai.ChatCompletion.create(
                    model=gpt_model_name, 
                    messages=[{"role": "user", "content": "Say Test"}]
                )
            completion = await self.hass.async_add_executor_job(make_api_call)
            # _LOGGER.debug('OpenAI API response: %s', completion)
            return True, None
        except Exception as e:
            _LOGGER.error('Error testing OpenAI API: %s', e)
            return False, str(e)
        