import aiohttp
import logging
import json
import googlemaps

from .const import DEFAULT_CHAT_MODEL
_LOGGER = logging.getLogger(__name__)


async def test_openai_api(api_key):

    url = "https://api.openai.com/v1/chat/completions"
    _LOGGER.debug(url)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": DEFAULT_CHAT_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say Test"}
        ]
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status == 200:
                    # If the request was successful, the API key is valid
                    return True, None
                else:
                    # If the request failed, the API key might be invalid
                    response_text = await response.text()
                    _LOGGER.error('OpenAI API returned an error: %s', response_text)
                    return False, response_text
    except Exception as e:
        _LOGGER.error('Error testing OpenAI API: %s', e)
        return False, str(e)

async def test_googlemaps_api(hass, googlemaps_api_key):
    try:
        # Retrieve the latitude and longitude from Home Assistant's core configuration
        latitude = hass.config.latitude
        longitude = hass.config.longitude

        # Initialize the Google Maps client
        gmaps = googlemaps.Client(key=googlemaps_api_key)

        # Define a local function for the blocking call
        def _reverse_geocode():
            test_location = (latitude, longitude)
            return gmaps.reverse_geocode(test_location)

        # Perform a simple reverse geocode test
        googlemaps_response = await hass.async_add_executor_job(_reverse_geocode)

        if googlemaps_response:
            formatted_location_name = format_location_name(googlemaps_response)
            return True, None, formatted_location_name
        else:
            return False, "No response from Google Maps API", None

    except Exception as e:
        _LOGGER.error('Error testing Google Maps API: %s', e)
        return False, str(e), None

def format_location_name(geocode_result):
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
