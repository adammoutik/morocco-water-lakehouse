import os
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

DEFAULT_OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"
BASE_URL = os.environ.get('OPEN_METEO_URL', DEFAULT_OPEN_METEO_URL)


def extract_historical_weather(latitude: float, longitude: float, start_date: str, end_date: str) -> dict:
    """
    Extracts historical weather data from the Open-Meteo API.

    Args:
        latitude (float): Latitude of the location.
        longitude (float): Longitude of the location.
        start_date (str): Start date in 'YYYY-MM-DD' format.
        end_date (str): End date in 'YYYY-MM-DD' format.

    Returns:
        dict: A dictionary containing the historical weather data.
    """
    url = os.environ.get('OPEN_METEO_URL', BASE_URL)

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_sum"],
        "timezone": "Africa/Casablanca"
    }

    try:
        logging.info(f"Fetching weather data for Lat: {latitude}, Lon: {longitude} from {start_date} to {end_date}...")
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Check if the API returned an embedded error response
        if isinstance(data, dict) and data.get("error"):
            reason = data.get("reason", "Unknown Open-Meteo API error")
            raise requests.RequestException(f"Open-Meteo API returned error: {reason}")

        logging.info("Weather data fetched successfully.")
        return data
    except requests.RequestException as e:
        logging.error(f"Error fetching weather data: {e}")
        raise
