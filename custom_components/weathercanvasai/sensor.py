from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.const import ATTR_ATTRIBUTION
from .const import DOMAIN
from datetime import datetime
import logging

_LOGGER = logging.getLogger(__name__)

class weathercanvasaiPromptsSensor(SensorEntity):
    def __init__(self, hass, entry_id, name):
        #_LOGGER.info("Initializing weathercanvasaiPromptSensor")
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
        #_LOGGER.info(f"Initializing weathercanvasaiPeomptsSensor with unique ID: {self._attr_unique_id}")


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

class weathercanvasaiImageSensor(SensorEntity):
    def __init__(self, hass, entry_id, name):
        """Initialize the image URL sensor."""
        self.hass = hass
        self.entry_id = entry_id
        self._attr_name = name
        self._attr_unique_id = f"{entry_id}_image"
        self._state = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._attr_name

    @property
    def state(self):
        """Return the state of the sensor (URL of the latest image)."""
        return self._state

    async def async_added_to_hass(self):
        """Handle entity which will be added to Home Assistant."""
        async def update_state():
            # Retrieve the latest_image_url from DOMAIN
            self._state = self.hass.data[DOMAIN].get('latest_image_url', None)
            self.async_write_ha_state()

        # Set up a listener for dispatcher signal
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, 
                "update_weathercanvasai_image_sensor", 
                update_state
            )
        )

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the sensors upon entry setup."""
    prompts_sensor = weathercanvasaiPromptsSensor(hass, config_entry.entry_id, "weathercanvasai Prompts")
    image_sensor = weathercanvasaiImageSensor(hass, config_entry.entry_id, "weathercanvasai Image")
    async_add_entities([prompts_sensor, image_sensor])
