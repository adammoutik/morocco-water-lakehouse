import os
import re
import logging
from src.storage.minio_handler import (
    BRONZE_BUCKET,
    SILVER_BUCKET,
    get_json_from_minio,
    get_excel_from_minio,
    upload_parquet_to_minio,
    list_objects_in_prefix
)
from src.config.locations import location_id_from_filename, location_type_for
from src.transformations.weather_silver import transform_weather_to_silver
from src.transformations.ckan_silver import transform_ckan_to_silver

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def process_weather_to_silver():
    logging.info("=== STARTING WEATHER SILVER PIPELINE ===")
    
    folder_prefix = "raw/open_meteo/"
    weather_files = list_objects_in_prefix(BRONZE_BUCKET, folder_prefix)
    json_files = [key for key in weather_files if key.endswith(".json")]

    if not json_files:
        logging.warning(f"No JSON files found in {folder_prefix}. Skipping.")
        return

    logging.info(f"Found {len(json_files)} weather file(s) to process.")

    for bronze_key in json_files:
        logging.info(f"Reading from Bronze layer: {bronze_key}")
        raw_json = get_json_from_minio(bronze_key)
        
        if not raw_json:
            logging.error(f"Failed to read Bronze data for {bronze_key}. Skipping.")
            continue

        filename = os.path.basename(bronze_key)
        location_id = location_id_from_filename(filename)
        location_type = location_type_for(location_id)
        df = transform_weather_to_silver(
            raw_json, location_id=location_id, location_type=location_type
        )
        if df.empty:
            logging.warning(f"Transformation resulted in empty DataFrame for {bronze_key}. Skipping.")
            continue

        base_name = os.path.splitext(filename)[0]
        silver_key = f"cleansed/open_meteo/{base_name}.parquet"

        logging.info(f"Writing to Silver layer: {silver_key}")
        upload_parquet_to_minio(df, SILVER_BUCKET, silver_key)

    logging.info("=== WEATHER SILVER PIPELINE COMPLETE ===\n")


def process_ckan_to_silver():
    logging.info("=== STARTING CKAN SILVER PIPELINE ===")
    
    folder_prefix = "raw/tensift_reservoirs/"
    excel_files = list_objects_in_prefix(BRONZE_BUCKET, folder_prefix)
    
    if not excel_files:
        logging.warning(f"No files found in {folder_prefix}. Skipping.")
        return
        
    logging.info(f"Found {len(excel_files)} files to process in {folder_prefix}.")

    for bronze_key in excel_files:
        if not bronze_key.endswith(('.xls', '.xlsx')):
            continue
            
        logging.info(f"Processing: {bronze_key}")
        df = get_excel_from_minio(BRONZE_BUCKET, bronze_key)
        if df.empty:
            logging.warning(f"File {bronze_key} was empty or unreadable.")
            continue

        file_name = bronze_key.split('/')[-1]
        # remove trailing excel extensions
        clean_name = re.sub(r'(\.xlsx|\.xls)+$', '', file_name, flags=re.IGNORECASE)
        silver_key = f"cleansed/ckan_reservoirs/{clean_name}.parquet"
        
        clean_df = transform_ckan_to_silver(df, file_name)
        logging.info(f"Saving Parquet to: {silver_key}")
        upload_parquet_to_minio(clean_df, SILVER_BUCKET, silver_key)
        
    logging.info("=== CKAN SILVER PIPELINE COMPLETE ===\n")


if __name__ == "__main__":
    process_weather_to_silver()
    process_ckan_to_silver()