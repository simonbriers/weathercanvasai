from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.const import ATTR_ATTRIBUTION
from .const import DOMAIN
from datetime import datetime
import logging

_LOGGER = logging.getLogger(__name__)

class weathercanvasaiPromptsSensor(SensorEntity):
    def __init__(self, hass, entry_id, name):
        """Initialize the sensor."""
        self.hass = hass
        self.entry_id = entry_id
        self._attr_name = name
        self._state = "Initial State"  # Default state
        self._attr_unique_id = f"{entry_id}_prompts"

        self._attributes = {
            "chatgpt_in": "Initial chatgpt_in",
            "chatgpt_out": "Initial chatgpt_out",
            "last_update": datetime.now().isoformat()
        }
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

    async def async_added_to_hass(self):
        """Register callbacks when entity is added."""
        async_dispatcher_connect(
            self.hass, 
            "update_weathercanvasai_sensor", 
            self._update_sensor
        )

    async def _update_sensor(self, data):
        """Update the sensor state and attributes."""
        current_time = datetime.now().isoformat() # Format the current date and time
        self._state = f"Updated at {current_time}" # Update the state to show it has been updated, along with the timestamp
        self._attributes["chatgpt_in"] = data.get("chatgpt_in")
        self._attributes["chatgpt_out"] = data.get("chatgpt_out")
        self._attributes["last_update"] = datetime.now().isoformat()
        self.async_write_ha_state()

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the sensor upon entry setup."""
    sensor = weathercanvasaiPromptsSensor(hass, config_entry.entry_id, "weathercanvasai Prompts")
    async_add_entities([sensor])
