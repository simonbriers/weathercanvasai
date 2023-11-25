from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.const import ATTR_ATTRIBUTION
from .const import DOMAIN
from datetime import datetime

class Weather2ImgPromptsSensor(SensorEntity):
    def __init__(self, hass, entry_id, name):
        """Initialize the sensor."""
        self.hass = hass
        self.entry_id = entry_id
        self._attr_name = name
        self._attr_unique_id = entry_id  # Use entry_id as the unique ID
        self._state = "Initial State"  # Default state
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

    def update(self):
        """Update the sensor state."""
        # Logic to update the state and attributes goes here
        # For example, fetch the latest prompts and update
        self._state = "new_state_value"
        self._attributes["chatgpt_in"] = "your_chatgpt_in_value"
        self._attributes["chatgpt_out"] = "your_chatgpt_out_value"
        # Update the timestamp
        self._attributes["last_update"] = datetime.now().isoformat()

        # ... existing code ...


    async def async_added_to_hass(self):
        """Register callbacks when entity is added."""
        await async_dispatcher_connect(
            self.hass, 
            "update_weather_image_generator_sensor", 
            self._update_sensor
        )

    async def _update_sensor(self, data):
        """Update the sensor state and attributes."""
        self._state = "Updated State"  # Modify as needed
        self._attributes["chatgpt_in"] = data.get("chatgpt_in")
        self._attributes["chatgpt_out"] = data.get("chatgpt_out")
        self._attributes["last_update"] = datetime.now().isoformat()
        self.async_write_ha_state()

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the sensor upon entry setup."""
    sensor = Weather2ImgPromptsSensor(hass, config_entry.entry_id, "Weather2Img Prompts")
    async_add_entities([sensor])