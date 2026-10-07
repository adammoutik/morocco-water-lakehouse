import os
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

DEFAULT_CKAN_URL = "https://data.gov.ma/data/api/3/action/package_search"
BASE_URL = os.environ.get('CKAN_URL', DEFAULT_CKAN_URL)


def extract_ckan_data(query: str, rows: int = 5) -> list:
    """
    Extracts datasets from the CKAN API based on a search query.

    Args:
        query (str): The search term for querying the CKAN API.
        rows (int): The number of results to return.

    Returns:
        list: A list of dictionaries representing the extracted datasets.
    """
    url = os.environ.get('CKAN_URL', BASE_URL)
    params = {
        "q": query,
        "rows": rows
    }

    try:
        logging.info(f"Connecting to CKAN API at {url} for query='{query}'...")
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if data.get("success"):
            logging.info("CKAN request successful. Data received.")
            results = data.get("result", {}).get("results", [])
            if not results:
                logging.warning("No datasets found for the query.")
                return []
            return results
        else:
            logging.warning("CKAN request succeeded HTTP-wise, but API returned success=False.")
            return []
    except requests.exceptions.Timeout as e:
        logging.error(f"CKAN request timed out: {e}")
        return []
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to connect to CKAN API: {e}")
        return []
