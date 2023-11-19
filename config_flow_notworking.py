from homeassistant import config_entries
from .const import DOMAIN  # Ensure this matches the domain in your manifest.json

class WeatherImageGeneratorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Basic config flow for Weather Image Generator."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLLING

    async def async_step_user(self, user_input=None):
        """Handle a config flow initiated by the user."""
        if user_input is not None:
            # Normally, you would add validation logic here
            return self.async_create_entry(title="Weather Image Generator", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema={},  # No fields in the form, just a basic form
        )
