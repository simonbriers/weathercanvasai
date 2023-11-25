from homeassistant.components.camera import Camera
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import aiohttp
import logging
from datetime import datetime

_LOGGER = logging.getLogger(__name__)

class DalleWeatherImageCamera(Camera):
    def __init__(self, hass, entry_id, name):
        """Initialize the camera."""
        super().__init__()
        self.hass = hass
        self.entry_id = entry_id
        self._name = name
        self._image_url = None
        self._attr_unique_id = entry_id  # Use entry_id as the unique ID
        self._state = "Initial State"  # Default state
        self._attr_icon = 'mdi:camera'  # Set the icon here

        # Additional initialization code...

    @property
    def name(self):
        """Return the name of this camera."""
        return self._name

    async def async_camera_image(self):
        """Return the image of this camera in bytes."""
        if self._image_url:
            # Use Home Assistant's aiohttp_client session for HTTP requests
            session = async_get_clientsession(self.hass)
            return await self._fetch_image_from_url(session, self._image_url)
        return None

    async def _fetch_image_from_url(self, session, url):
        """Fetch and return image from the URL using the provided session."""
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.read()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error fetching camera image: %s", err)
            return None
               
    async def async_added_to_hass(self):
        """Register callbacks when entity is added."""
        self._remove_signal = async_dispatcher_connect(
            self.hass, 
            "update_dalle_weather_image_camera", 
            self._update_image_url
        )

    async def async_will_remove_from_hass(self):
        """Disconnect dispatcher listener when removed."""
        if self._remove_signal:
            self._remove_signal()

    async def _update_image_url(self, image_url):
        """Update the camera's image URL."""
        self._image_url = image_url
        # Assuming you want to store the last update timestamp as an attribute
        self._attributes["last_image_update"] = datetime.now().isoformat()
        self.async_schedule_update_ha_state()


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the DalleWeatherImageCamera from a config entry."""
    async_add_entities([DalleWeatherImageCamera(hass, config_entry.entry_id, "Dalle Weather Image")])