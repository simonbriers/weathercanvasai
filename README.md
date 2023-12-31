# WeatherCanvasAI
Home Assistant weather image generator with OpenAI and Dall-E

# Custom Home Assistant Integration for DALL-E Image Generation

## Description
This custom integration for Home Assistant generates images using DALL-E, driven by prompts constructed from location and weather data. It combines data from Home Assistant, OpenWeatherMap, Googlemaps, and uses the OpenAI API to create unique, contextually relevant images.
Since the installed openai libary for python is the outdated 0.27, this integration makes direct calls to the latest Openai api endpoints, thus avoiding the python libary installed in HA at this moment. I didn't want the integration to forceupdate the libary to the current 1.3.5, as this would render your installation non standard and would require reinstallation on every update of HA.
Be aware that there is a small cost involved for the api calls to ChatGPT and to Dall-E. You need an Openai account and an active payment method to be able to use their api. You can choose the model you want during setup. The tokens sent to ChatGPT are limited, the cost is negligable. To fetch a Dalle-3 image, they cost at the moment € 0.04, for Dale-2 € 0.02 per call. The difference in quality is huge however. Api calls are only made by services, up to you if you do this manually or in an automations once every ... . Every hour during night and day would be 24 calls and cost € 1 per day. Be aware, that's € 30 per month ! 1 picture per day comes down to € 1.25 per month. You have been warned ! I have a version that makes an api call to a local automatic1111 server, but this relies on that server running nonstop in you homenetwork. If someone is aware of a free Stable diffusion service, I will test and provide another version.

## Features
- **Dynamic Image Generation**: Utilizes DALL-E to generate images based on ChatGPT prompts.
- **Location Awareness**: Integrates with Googlemaps: based on your location (LongLat) fom you Home Assistant, a reverse geocache is called to Googlemaps API. You need to get your API for this. Googlemaps will return the name of the town or city, province, state and country. As this data is be passed to Dalle, it is smart enough to create something that is suitable for your location. If you would live in a famous street, it could use that as well, but this information is not passed at this mooment.
- **Weather Awareness**: Integrates with OpenWeatherMap for real-time weather data and uses location data from Home Assistant.
- **Configurable via Home Assistant**: Easy setup and configuration through the Home Assistant interface.

## Prerequisites
- **API Keys Required**:
  - **OpenAI API Key**: For accessing DALL-E services (requires a subscription plan).
  - **OpenWeatherMap API Key**: Free key for weather data, obtained after registration.
  - **Google Maps API Key**: For location services. (Reverse geocaching to retrieve our adress from your HA coordinates)

##Install Dependencies:
- `openweathermap` integration is not a mandatory but an advisable installation. You need an account and API key (free). You can skip this installation. However, if no weatherdata can be retrieved from openwaethermap, ChatGPT wil be instructed 'to be creative about the weatherconditions'. An image will stil be generated for the location, the season and time of day, but the current weatherconditions wil not be incorporated in the image. It may be winter with a perfect sunny day, while you will get an image with a meter of snow. Openweathermap will provide temperature, general weather conditions and cloudiness that wil be passed on in the prompt to Dall-E.

## Installation
There are two ways to install:
 
1. **Download and Install the Integration**:
   - Place the integration files in your Home Assistant's custom components directory.
2. **Install with HACS (Home Assistant Custom Component Store)
   - In HACS, click on integrations, then click the 3 dots in the top right corner
   - From the dropdown menu, choose "Custom Repositories"
   - Enter https://github.com/simonbriers/weathercanvasai as repository and choose integration for the second field.
     
  ![image](https://github.com/simonbriers/weathercanvasai/assets/101293590/20378c3f-911c-49b1-a5ff-4ebd5afc30c6)

   - In the next windows, click on Weather Canvas AI (left of the bin)
     
  ![image](https://github.com/simonbriers/weathercanvasai/assets/101293590/034d65a3-8143-4f30-a5e5-3371b50f570b)

   - This readme will open, click on download in the down-right corner
     
  ![image](https://github.com/simonbriers/weathercanvasai/assets/101293590/2fade912-d63d-42cf-bf19-4373cad06ae3)

   - confirm the downloas and restart HA
    
   - In your main HA menu, go to Settings - Devices and services and choose "+ Add integration"
   - In the search field, enter "Weather Canvas AI"
     
  ![image](https://github.com/simonbriers/weathercanvasai/assets/101293590/1f51eff3-1686-4370-a515-a819ca113ca2)

   - you should now arrive in the configuration menu
     
  ![image](https://github.com/simonbriers/weathercanvasai/assets/101293590/46992dce-6ebd-400c-8fb1-779b52cb7535)

## Configuration
1. **Via Home Assistant UI**:
   - Navigate to the Integrations page and add this custom integration.
   - Enter the required API keys, ChatGPT and Dall-E models when prompted.
   - As for the location name, the integration will look up the name of you location based on the longitude and Lattitude of your HA installation. You can change then ame into anything that would be more descriptive. if you live in a small town that neither ChatGPT nor Dall-E may recognize, enter a location name of the nearest city. You can even enter the name of a location in another country, and the integration will create an imga of that city with your weather and time of day situation.

2. **Configuration Parameters**:
   - `api_key_openai`: Your OpenAI API key. Used for accessing DALL-E and GPT services.
   - `api_key_openweathermap`: Your OpenWeatherMap API key. Used for fetching weather data.
   - `api_key_googlemaps`: Your Google Maps API key. Used for location services.
   - `location_name`: A default or custom location for weather and image context.
   - number of images to be retained in the local storage. Default set to 5.
  
     The choice of the ChatGPT model is final for your installation. If you want to switch, you need to uninstall and reinstall the integration.

## Entities and Services
This integration creates two entities and provides three services:

### Entities

1. **Camera Entity - `camera.weathercanvasai_image`**:
   - This entity represents the image generated by the integration.
   - **Casting to Media Players**: The generated image can be cast to any suitable media player in your Home Assistant setup. Beware that in a docker installation, the ip adress of the container may not be included in your local network, google casting to such devices is not possible out of the box. 
   - **Use in UI**: The image, saved in /local can be displayed in the Home Assistant UI using an image card, providing a visual representation of the current weather and location scenario.

2. **Sensor Entity - `sensor.weathercanvasai_prompts`**:
   - Tracks the last used ChatGPT prompts for image generation.
   - **Attributes**:
     - `chatgpt_in`: The prompt input derived from weather and location data.
     - `chatgpt_out`: The final prompt sent to the OpenAI API for image generation.

### Services
The integration offers two services:

## Service: `create_chatgpt_prompt` (to be called before attempting to generate an image with Dall-E)
### Purpose
- Creates a ChatGPT prompt combining location, time of day, season, and weather conditions for image generation.
### Functionality
- Retrieves the current day segment and season, and combines it with location name and weather conditions to create `chatgpt_in`.
- Processes `chatgpt_in` to generate `chatgpt_out` for use in DALL-E image generation.
- Dispatches `chatgpt_out` to update the `sensor.weathercanvasai_prompts`.

## Service: `create_dalle2_image`
### Purpose
- Generates an image using DALL-E-2 based on the ChatGPT prompt.
### Functionality
- Retrieves `chatgpt_out` from `sensor.weathercanvasai_prompts`.
- Uses this prompt to generate an image via DALL-E-2.
- Updates the `camera.weathercanvasai_image` entity with the new image URL upon successful generation.

### Options

Dall-e-2 offers an options to customize the size of the generated images:

- `size`: Specifies the size of the generated image.
  - Available options are: `256x256`, `512x512`, or `1024x1792`.
  - Default is `1024x1024`.

## YAML Configuration Example

To create a custom Dall-e-2 image with the desired options, use the following YAML configuration:

```yaml
service: weathercanvasai.create_dalle2_image
data:
  size: "512x512"
````

## Service: `create_dalle3_image`
### Purpose
- Generates an image using DALL-E-3 based on the ChatGPT prompt.
### Functionality
- Retrieves `chatgpt_out` from `sensor.weathercanvasai_prompts`.
- Uses this prompt to generate an image via DALL-E-3.
- Updates the `camera.weathercanvasai_image` entity with the new image URL upon successful generation.

### Options

Dall-e-3 offers a variety of options to customize the generated images:

- `size`: Specifies the size of the generated image.
  - Available options are: `1024x1024`, `1792x1024`, or `1024x1792`.
  - Default is `1024x1024`.
  
- `quality`: Determines the quality of the image.
  - Choose `standard` for normal quality or `hd` for high definition which offers finer details and greater consistency.
  - Default is `standard`.
  
- `style`: Defines the style of the generated images.
  - Options are `vivid` for hyper-real and dramatic images or `natural` for more natural-looking images.
  - Default is `vivid`.

![image](https://github.com/simonbriers/weathercanvasai/assets/101293590/7d6e38a4-eb03-4797-88d1-0ad85e8858b9)

## YAML Configuration Example

To create a custom Dall-e-3 image with the desired options, use the following YAML configuration:

```yaml
service: weathercanvasai.create_dalle3_image
data:
  size: 1792x1024
  quality: hd
  style: vivid
```
 
## Usage and Integration in UI
- **Call the service "Weather Canvas AI: create_chatgpt_prompt"** to have ChatGPT pepare a promp based on the season, time of day, weather conditions and location.

![image](https://github.com/simonbriers/weathercanvasai/assets/101293590/60e24bfe-3276-4475-b269-54ec0fa49072)

- **Call the service "Weather Canvas AI: create_dalle_image (2 or 3) "** to send the prompt to Dall-E. The camera entity will be updated with the image. The image will be saved under /config/www 

- **Generated Image Accessibility**:
  - The last generated image by `camera.weathercanvasai_image` is saved in the Home Assistant configuration directory under `/local`. (This is your /configuration/www directory)
  - This enables easy integration of the image into different parts of the Home Assistant UI, such as in an image card, providing dynamic visual content based on the current environmental conditions.

## Contributing
- Contributions to enhance or fix issues in this integration are welcome.


