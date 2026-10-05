import requests
import json
import os 
import logging
from dotenv import load_dotenv
import boto3

load_dotenv()
BASE_URL = os.environ.get('CKAN_URL')

def extract_ckan_data(query, rows=5):
    """
    Extracts datasets from the CKAN API based on a search query.

    Args:
        query (str): The search term for querying the CKAN API.
        rows (int): The number of results to return.

    Returns:
        list: A list of dictionaries representing the extracted datasets.
    """
    params = {
        "q": query,
        "rows": rows
    }

    try:
        logging.info(f"Tentative de connexion à {BASE_URL}...")
        response = requests.get(BASE_URL, params=params, timeout=100
        )
        response.raise_for_status()
        data = response.json()

        if data.get("success"):
            logging.info("Requête réussie ! Données reçues.")
            if not data["result"]["results"]:
                logging.warning("Aucun résultat trouvé pour la requête.")
                return []
            return data["result"]["results"]
        else:
            logging.warning("La requête a réussi, mais CKAN a retourné une erreur.")
            return []
    except requests.exceptions.Timeout as e:
            logging.error(f"The request timed out: {e}")
            return []    
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to connect to the CKAN API: {e}")
        return []


