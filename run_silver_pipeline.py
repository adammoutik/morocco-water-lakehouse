import logging
from src.storage.minio_handler import get_json_from_minio, upload_parquet_to_minio, list_objects_in_prefix
from src.transformations.weather_silver import transform_weather_to_silver
from src.storage.minio_handler import get_excel_from_minio
from src.transformations.ckan_silver import transform_ckan_to_silver

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

import os
import logging
from src.storage.minio_handler import (
    get_json_from_minio, 
    upload_parquet_to_minio, 
    list_objects_in_prefix
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def process_weather_to_silver():
    logging.info("=== STARTING WEATHER SILVER PIPELINE ===")
    
    bronze_bucket = "morocco-water-bronze"
    silver_bucket = "morocco-water-silver"
    folder_prefix = "raw/open_meteo/"


    weather_files = list_objects_in_prefix(bronze_bucket, folder_prefix)
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


        df = transform_weather_to_silver(raw_json)
        if df.empty:
            logging.warning(f"Transformation resulted in empty DataFrame for {bronze_key}. Skipping.")
            continue


        filename = os.path.basename(bronze_key)
        base_name = os.path.splitext(filename)[0]
        silver_key = f"cleansed/open_meteo/{base_name}.parquet"

        logging.info(f"Writing to Silver layer: {silver_key}")
        upload_parquet_to_minio(df, silver_bucket, silver_key)

    logging.info("=== WEATHER SILVER PIPELINE COMPLETE ===\n")

def process_ckan_to_silver():
    logging.info("=== STARTING CKAN SILVER PIPELINE ===")
    
    bronze_bucket = "morocco-water-bronze"
    silver_bucket = "morocco-water-silver"
    
    folder_prefix = "raw/tensift_reservoirs/" 
    
    # dynamically discover all files in that folder
    excel_files = list_objects_in_prefix(bronze_bucket, folder_prefix)
    
    if not excel_files:
        logging.warning(f"No files found in {folder_prefix}. Skipping.")
        return
        
    logging.info(f"Found {len(excel_files)} files to process in {folder_prefix}.")

    
    for bronze_key in excel_files:
        if not bronze_key.endswith(('.xls', '.xlsx')):
            continue
            
        logging.info(f"Processing: {bronze_key}")
        df = get_excel_from_minio(bronze_bucket, bronze_key)
        if df.empty:
            logging.warning(f"File {bronze_key} was empty or unreadable.")
            continue

        # dynamic Parquet Naming
        file_name = bronze_key.split('/')[-1] 
        clean_name = file_name.replace('.xlsx', '').replace('.xls', '')
        silver_key = f"cleansed/ckan_reservoirs/{clean_name}.parquet"
        clean_df = transform_ckan_to_silver(df, file_name)
        logging.info(f"Saving Parquet to: {silver_key}")
        upload_parquet_to_minio(clean_df, silver_bucket, silver_key)
        
        
    logging.info("=== CKAN SILVER PIPELINE COMPLETE ===\n")
if __name__ == "__main__":
    process_weather_to_silver()
    process_ckan_to_silver()