import logging

# CORRECT
from src.extraction.extract_ck import extract_ckan_data
from src.extraction.weather_client import extract_historical_weather
from src.storage.minio_handler import download_resources, upload_json_to_minio


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def ingest_ckan_data():
    logging.info("=== STARTING CKAN INGESTION ===")
    query = "tensift"
    
    datasets = extract_ckan_data(query, rows=2)
    
    if not datasets:
        logging.warning("No CKAN datasets found or extraction failed.")
        return

    # Download files and stream to MinIO
    logging.info(f"Found {len(datasets)} datasets. Streaming to MinIO...")
    download_resources(datasets)
    logging.info("=== CKAN INGESTION COMPLETE ===\n")

def ingest_weather_data():
    logging.info("=== STARTING WEATHER INGESTION ===")
    lat, lon = 31.63, -8.00
    start_date, end_date = "2024-01-01", "2024-01-31"
    object_key = f"raw/open_meteo/tensift_{start_date}_to_{end_date}.json"

    # Extract JSON
    weather_data = extract_historical_weather(lat, lon, start_date, end_date)
    if not weather_data:
        logging.warning("Weather extraction failed.")
        return

    # Upload to MinIO
    logging.info(f"Uploading weather data to {object_key}...")
    upload_json_to_minio(weather_data, object_key)
    logging.info("=== WEATHER INGESTION COMPLETE ===\n")

if __name__ == "__main__":
    logging.info("Starting Morocco Water Reliability Lakehouse Ingestion Pipeline...")
    
    # Run pipelines sequentially
    ingest_ckan_data()
    ingest_weather_data()

    logging.info("All Bronze layer ingestion tasks finished successfully!")