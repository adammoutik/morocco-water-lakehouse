from datetime import datetime
import logging
import pandas as pd
from src.storage.minio_handler import (
    SILVER_BUCKET,
    GOLD_BUCKET,
    get_parquet_from_minio,
    list_objects_in_prefix,
    upload_parquet_to_minio
)
from src.transformations.gold_aggregation import build_gold_analytical_model

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def load_all_parquets_from_prefix(bucket: str, prefix: str) -> pd.DataFrame:
    """
    Dynamically discovers and concatenates all Parquet files in a given MinIO folder.
    """
    file_keys = list_objects_in_prefix(bucket, prefix)
    parquet_keys = [k for k in file_keys if k.endswith('.parquet')]
    
    if not parquet_keys:
        logging.warning(f"No parquet files found in {prefix}")
        return pd.DataFrame()
        
    dfs = []
    for key in parquet_keys:
        logging.info(f"Loading {key}...")
        df = get_parquet_from_minio(bucket, key)
        if not df.empty:
            dfs.append(df)
            
    if dfs:
        # concatenate discovered parquet partitions
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()


def process_gold_pipeline():
    logging.info("=== STARTING GOLD PIPELINE ===")
    logging.info("--- Extracting Silver Weather Data ---")
    weather_df = load_all_parquets_from_prefix(SILVER_BUCKET, "cleansed/open_meteo/")
    
    logging.info("--- Extracting Silver CKAN Data ---")
    ckan_df = load_all_parquets_from_prefix(SILVER_BUCKET, "cleansed/ckan_reservoirs/")
    
    if weather_df.empty or ckan_df.empty:
        logging.error("Failed to load sufficient Silver datasets. Aborting Gold pipeline.")
        return

    gold_df = build_gold_analytical_model(weather_df, ckan_df)

    if gold_df.empty:
        logging.error("The joined Gold DataFrame is empty. Check if dates overlap between datasets!")
        return

    execution_date = datetime.now().strftime("%Y%m%d")
    gold_key = f"analytical/water_reliability_master_{execution_date}.parquet"

    logging.info(f"Writing master Gold dataset to: {gold_key}")
    upload_parquet_to_minio(gold_df, GOLD_BUCKET, gold_key)
    
    logging.info("=== GOLD PIPELINE COMPLETE ===\n")


if __name__ == "__main__":
    process_gold_pipeline()