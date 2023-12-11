from homeassistant.components.camera import Camera
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import get_url
import aiohttp
import logging
import requests
from datetime import datetime
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class weathercanvasaiCamera(Camera):
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
        self._image_url = None
        self._cached_image = None
        self._cached_url = None

    
    async def async_added_to_hass(self):
        # This method is called when the camera is added to Home Assistant
        # Register an update listener
        self.async_on_remove(
            async_dispatcher_connect(self.hass, DOMAIN, self._update_image_url)
        )

    @property
    def name(self):
        """Return the name of this camera."""
        return self._name

    async def async_camera_image(self, width=None, height=None):
        """Return the image of this camera in bytes."""
        #_LOGGER.debug("Fetching camera image.")
        #_LOGGER.debug("Current image URL: %s", self._image_url)
        if self._image_url:
            # Check if the URL has changed since the last fetch
            if self._image_url == self._cached_url:
                #_LOGGER.debug("Returning cached image.")
                return self._cached_image

            # URL has changed, fetch new image
            session = async_get_clientsession(self.hass)
            new_image = await self._fetch_image_from_url(session, self._image_url)

            # Update cache
            self._cached_image = new_image
            self._cached_url = self._image_url
            return new_image

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
            "update_weathercanvasai_camera", 
            self._update_image_url
        )

    async def async_will_remove_from_hass(self):
        """Disconnect dispatcher listener when removed."""
        if self._remove_signal:
            self._remove_signal()

    async def _update_image_url(self):
        # Fetch the latest image URL from the domain
        self._image_url = self.hass.data[DOMAIN].get('latest_image_full_url')
        #_LOGGER.debug(f"Camera image URL updated: {self._image_url}")

    def camera_image(self):
        # Override this method to return the latest image from the stored URL
        if self._image_url:
            # Fetch and return the image from the URL
            response = requests.get(self._image_url)
            return response.content
        return None
    
async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the weathercanvasaiCamera from a config entry."""
    async_add_entities([weathercanvasaiCamera(hass, config_entry.entry_id, "weathercanvasai Image")])
