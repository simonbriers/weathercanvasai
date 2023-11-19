import requests

def get_city_name(latitude, longitude):
    url = f"https://nominatim.openstreetmap.org/reverse?lat={latitude}&lon={longitude}&format=json"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get('address', {}).get('city', 'Unknown')
    except requests.RequestException as e:
        print(f"Error: {e}")
        return 'Unknown'

# Usage
city_name = get_city_name(36.6402359,-4.5864382)
print(city_name)
