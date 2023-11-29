from homeassistant.components.camera import Camera
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import get_url
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
        self._attr_unique_id = entry_id  # Use entry_id as the unique ID
        self._state = "Initial State"  # Default state
        self._attr_icon = 'mdi:camera'  # Set the icon here
        self._attributes = {
            "last_image_update": datetime.now().isoformat()
        }
       # Use Home Assistant's internal URL to construct the image URL
        base_url = get_url(self.hass, allow_internal=True, allow_ip=True, prefer_external=False, prefer_cloud=False)
        self._image_url = f"{base_url}/local/dalle.png"
        _LOGGER.debug(f"Got image from {base_url}/local/dalle.png")
        
    @property
    def name(self):
        """Return the name of this camera."""
        return self._name

    async def async_camera_image(self):
        """Return the image of this camera in bytes."""
        _LOGGER.debug("Fetching camera image.")
        if self._image_url:
            # Use Home Assistant's aiohttp_client session for HTTP requests
            session = async_get_clientsession(self.hass)
            return await self._fetch_image_from_url(session, self._image_url)
        _LOGGER.warning("No image URL set for camera; returning None.")
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
        """Trigger camera to fetch the new image."""
        _LOGGER.debug("Received signal to fetch new image")
        # No need to update self._image_url since it's static
        # Directly fetch the new image
        session = async_get_clientsession(self.hass)
        new_image = await self._fetch_image_from_url(session, self._image_url)
        if new_image:
            # store the last update timestamp as an attribute
            self._attributes = {
                "last_image_update": datetime.now().isoformat()
            }
            self.async_write_ha_state()  # Update the state to reflect the new image
        else:
            _LOGGER.error("Failed to fetch new image.")

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the DalleWeatherImageCamera from a config entry."""
    async_add_entities([DalleWeatherImageCamera(hass, config_entry.entry_id, "Dalle Weather Image")])