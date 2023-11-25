from homeassistant.components.sensor import SensorEntity
from homeassistant.const import ATTR_ATTRIBUTION
from .const import DOMAIN
from datetime import datetime

class Weather2ImgPromptsSensor(SensorEntity):
    def __init__(self, hass, entry_id, name):
        """Initialize the sensor."""
        self.hass = hass
        self.entry_id = entry_id
        self._attr_name = name
        self._state = None
        self._attributes = {}
        self._attr_icon = 'mdi:chat'  # Set the icon here


    @property
    def name(self):
        """Return the name of the sensor."""
        return self._attr_name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    def update(self):
        """Update the sensor state."""
        # Logic to update the state and attributes goes here
        # For example, fetch the latest prompts and update
        self._state = "new_state_value"
        self._attributes["chatgpt_in"] = "your_chatgpt_in_value"
        self._attributes["chatgpt_out"] = "your_chatgpt_out_value"
        # Update the timestamp
        self._attributes["last_update"] = datetime.now().isoformat()