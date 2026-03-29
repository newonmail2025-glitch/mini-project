import httpx
import os
from dotenv import load_dotenv

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "your_api_key_here")
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

async def fetch_weather_data(city: str):
    """
    Fetch real-time weather data for a given city using OpenWeatherMap API.
    """
    params = {
        "q": city,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric"  # Get temperature in Celsius
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(BASE_URL, params=params)
        
        if response.status_code != 200:
            return None
            
        data = response.json()
        
        # Extract required fields:
        # AT (Ambient Temperature) -> temp
        # AP (Atmospheric Pressure) -> pressure
        # RH (Relative Humidity) -> humidity
        
        weather_info = {
            "temp": data["main"]["temp"],
            "pressure": data["main"]["pressure"],
            "humidity": data["main"]["humidity"],
            "city": data["name"]
        }
        
        return weather_info

def estimate_vacuum_value(temp):
    """
    A simple heuristic to estimate Vacuum (V) based on Ambient Temperature (AT).
    In real power plant datasets, V often correlates with AT.
    Heuristic: V = 30 + 1.5 * AT (placeholder logic)
    """
    return 30.0 + (1.5 * temp)
