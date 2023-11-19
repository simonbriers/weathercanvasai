import requests
import datetime
import json
import yaml
import openai
import os
from dotenv import load_dotenv
import io
import base64
import pycountry
from PIL import Image

# Define the directory for saving images
IMAGE_DIR = 'weather_pictures'

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
load_dotenv(env_path)

# Environment variables for OpenWeatherMap API
openweather_api_key = os.getenv('OPENWEATHERMAP_API_KEY')
latitude = os.getenv('LATITUDE')
longitude = os.getenv('LONGITUDE')
units = os.getenv('UNITS', 'metric')  # Default to 'metric'
language = os.getenv('LANGUAGE', 'en')  # Default to 'en'

# OpenAI api key, models and client
openai_api_key = os.getenv('OPENAI_API_KEY')
client = openai.Client(api_key=openai_api_key)
openai_imagemodel = os.getenv('OPENAI_IMAGEMODEL', 'dall-e-2')  # Default to 'dall-e-2'
chatgpt_model = os.getenv('CHATGPT_MODEL', 'gpt-3.5-turbo')  # Default to 'gpt-3.5-turbo'

# OpenWeatherMap endpoint: defines the api endpoint
WEATHER_API_URL = "http://api.openweathermap.org/data/2.5/weather"

# function to determine the season based in the timestamp from openweathermap
def get_season(month):
    if 3 <= month <= 5:
        return 'Spring'
    elif 6 <= month <= 8:
        return 'Summer'
    elif 9 <= month <= 11:
        return 'Autumn'
    else:
        return 'Winter'

# function to fetch weater data from openweathermap API. It returns the weather data as json 
def fetch_weather_data(api_key, latitude, longitude, units="metric", language="en"):
    params = {
        'lat': latitude,
        'lon': longitude,
        'appid': api_key,
        'units': units,
        'lang': language,
    }

    response = requests.get(WEATHER_API_URL, params=params)
    response.raise_for_status()  # Raise an HTTPError for unsuccessful status codes
    return response.json()  # Return the weather data

# function to prepare chatgpt call for a prompt that can be used by dalle
def generate_weather_prompt(weather_data):
# Extract timestamps and location
    current_timestamp = weather_data['dt']
    sunrise_timestamp = weather_data['sys']['sunrise']
    sunset_timestamp = weather_data['sys']['sunset']
    country = weather_data['sys']['country']
    location = weather_data['name']

    # Convert timestamps to datetime objects
    current_time = datetime.datetime.utcfromtimestamp(current_timestamp)
    sunrise_time = datetime.datetime.utcfromtimestamp(sunrise_timestamp)
    sunset_time = datetime.datetime.utcfromtimestamp(sunset_timestamp)
    
    # Determine the season
    current_month = current_time.month
    season = get_season(current_month)
    
    # Calculate the fraction of the day or night
    if current_time < sunrise_time:
        fraction = (current_time - sunrise_time).total_seconds() / (24 * 3600)
    elif current_time > sunset_time:
        fraction = (current_time - sunset_time).total_seconds() / (24 * 3600) + 1
    else:
        day_length = (sunset_time - sunrise_time).total_seconds()
        fraction = (current_time - sunrise_time).total_seconds() / day_length

    # Load the lookup table from the YAML file
    with open('time_of_day_lookup.yaml', 'r') as file:
        lookup_table = yaml.safe_load(file)

    # Find the matching description in the lookup table
    day_part_description = None
    for key, description in lookup_table.items():
        lower_bound, upper_bound = map(float, key.split('-'))
        if lower_bound <= fraction < upper_bound:
            day_part_description = description
            break

    # Extract the country code and transfom it into country_name
    country_code = weather_data['sys']['country']
    country = pycountry.countries.get(alpha_2=country_code)
    if country:
        country_name = country.name
    else:
        country_name = "Unknown Country"

    weather_description = weather_data['weather'][0]['description']
    temperature = round(weather_data['main']['temp'])
    cloudiness = weather_data['clouds']['all']  # in percentage
    humidity = weather_data['main']['humidity']  # in percentage
    wind_speed = round(weather_data['wind']['speed'])  # assuming it's in km/h

    # Construct the prompt
    prompt = f"{season} {day_part_description.capitalize()} in {location}, {country_name}. There is a {weather_description} at {temperature} degrees. The cloudiness is {cloudiness}%, the humidity is {humidity}%, the wind speed is {wind_speed} km/h."
    return prompt


def create_dalle_prompt(chatgpt_in):
    system_instruction = "Create a succinct DALL-E prompt under 100 words, focusing on the most visually striking aspects of the given city/region, weather, and time of day. Highlight key elements that define the scene's character, such as specific landmarks, weather effects, or cultural features, in a direct and vivid manner. Avoid elaborate descriptions; instead, aim for a prompt that vividly captures the essence of the scene in a concise format, suitable for generating a distinct and compelling image."

    response = client.chat.completions.create(
        model=chatgpt_model,
        messages=[
            {
                "role": "system",
                "content": system_instruction
            },
            {
                "role": "user",
                "content": chatgpt_in
            }
        ],
        temperature=1,
        max_tokens=256,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )

    # Check if the response is valid and contains choices
    if response and response.choices and len(response.choices) > 0:
        # Extract just the 'content' part of the message
        chatgpt_prompt = response.choices[0].message.content
        return chatgpt_prompt.strip()
    else:
        return "Error: No response from ChatGPT."

# function to find the root directory, to save the created images in a separate directory
def find_project_root(current_dir):
    """
    Recursively searches for the .env file that indicates the project root.
    """
    # Check if the .env file exists in the current directory
    if '.env' in os.listdir(current_dir):
        return current_dir
    else:
        # Move up one directory
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            # This means we have reached the filesystem root without finding .env
            raise FileNotFoundError(".env file not found, unable to determine project root.")
        return find_project_root(parent_dir)

#function to save images with location, model and timestamps    
def save_image(image_url, location, image_dir='weather_images'):
    # Find the project root
    project_root = find_project_root(os.path.dirname(os.path.abspath(__file__)))
    # Path for the new directory in the project root
    image_dir_path = os.path.join(project_root, image_dir)
    # Create the directory if it doesn't exist
    os.makedirs(image_dir_path, exist_ok=True)

    # Format the file name with the location, model name, and timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    image_name = f"{location}_{openai_imagemodel}_{timestamp}.png"
    image_path = os.path.join(image_dir_path, image_name)
    
    # Download and save the image
    response = requests.get(image_url)
    if response.status_code == 200:
        with open(image_path, 'wb') as file:
            file.write(response.content)
        print(f"Image saved as {image_path}")
        return image_path
    else:
        print("Failed to download the image.")
        return None


# function to retrieve a local automatic1111 image   
def generate_and_save_image(description):
    image_gen_url = "http://100.103.138.63:7861/sdapi/v1/txt2img"  # Replace with your actual URL
    payload = {
        "prompt": description,
        "steps": 25,  # Adjust as needed
        "width": 512,
        "height": 512
    }

    response = requests.post(url=image_gen_url, json=payload)
    response.raise_for_status()

    r = response.json()
    image_data = base64.b64decode(r['images'][0])
    image = Image.open(io.BytesIO(image_data))
    image.save('weather_output.png')

    print("Stable diffusion Weather image generated and saved as weather_output.png")

# function to change county ISO codes into countrynames
def get_country_name(country_code):
    country = pycountry.countries.get(alpha_2=country_code)
    if country:
        return country.name
    else:
        return "Unknown Country"




def main():
    try:
        # Fetch weather data from openweather
        weather_data = fetch_weather_data(openweather_api_key, latitude, longitude, units, language)
        # construct a user prompt to pass on to chatgpt
        chatgpt_in = generate_weather_prompt(weather_data)
        # create a prompt to pass to chatgpt
        chatgpt_response = create_dalle_prompt(chatgpt_in)
        print(f"DALL-E Prompt from chatgpt: {chatgpt_response}")

        # Generate image using OpenAI's API to DALL-E
        response = client.images.generate(
            model=openai_imagemodel,
            prompt=chatgpt_response,  # Use the prompt directly
            n=1,
            size="1024x1024"
        )

        # Check if the image was successfully generated and get the URL
        if response and response.data and len(response.data) > 0:
            image_url = response.data[0].url
            
            # Call the save_image function to save the image
            image_path = save_image(image_url, weather_data['name'])
            if image_path:
                print(f"Dall-E image generated and saved as {image_path}")
            else:
                print("Failed to download the image.")
        else:
            print("No image URL found in the response.")

    except requests.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"An error occurred: {err}")

if __name__ == "__main__":
    main()

