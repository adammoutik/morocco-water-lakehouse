import logging
from src.storage.minio_handler import get_json_from_minio, upload_parquet_to_minio
from src.transformations.weather_silver import transform_weather_to_silver

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def process_weather_to_silver():
    logging.info("=== STARTING WEATHER SILVER PIPELINE ===")
    
    silver_bucket = "morocco-water-silver"
    bronze_key = "raw/open_meteo/tensift_2024-01-01_to_2024-01-31.json"
    silver_key = "cleansed/open_meteo/tensift_2024_01.parquet"

    logging.info(f"Reading from Bronze layer: {bronze_key}")
    raw_json = get_json_from_minio(bronze_key)
    
    if not raw_json:
        logging.error("Failed to read Bronze data. Aborting pipeline.")
        return

    df = transform_weather_to_silver(raw_json)
    
    if df.empty:
        logging.error("Transformation resulted in empty DataFrame. Aborting.")
        return

    logging.info(f"Writing to Silver layer: {silver_key}")
    upload_parquet_to_minio(df, silver_bucket, silver_key)
    
    logging.info("=== WEATHER SILVER PIPELINE COMPLETE ===\n")

if __name__ == "__main__":
    process_weather_to_silver()