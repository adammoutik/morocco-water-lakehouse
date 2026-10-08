import os
import sys
import logging
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Ensure project root is in sys.path when executed directly
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.storage.minio_handler import (
    SILVER_BUCKET,
    get_parquet_from_minio,
    list_objects_in_prefix,
)
from src.transformations.gold_aggregation import _rename_ckan_columns, _melt_reservoirs

# Load environment configuration
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def get_postgres_engine():
    """create postgresql database engine."""
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "postgres")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "reservoir_db")

    conn_str = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    return create_engine(conn_str)


def load_silver_ckan_to_staging(engine) -> int:
    """read silver ckan parquet files and stage into postgresql via truncate-and-append."""
    logging.info("Reading Silver CKAN Parquet files from MinIO...")
    keys = list_objects_in_prefix(SILVER_BUCKET, "cleansed/ckan_reservoirs/")
    parquet_keys = [k for k in keys if k.endswith(".parquet")]

    if not parquet_keys:
        logging.warning("No Silver CKAN parquet files found in MinIO.")
        return 0

    all_melted = []
    for key in parquet_keys:
        df = get_parquet_from_minio(SILVER_BUCKET, key)
        if df.empty:
            continue
        # standardize column headers and unpivot reservoir measurements to long rows
        clean_df = _rename_ckan_columns(df)
        clean_df["date"] = pd.to_datetime(clean_df["date"])
        melted = _melt_reservoirs(clean_df)
        all_melted.append(melted)

    if not all_melted:
        logging.warning("No reservoir data could be extracted.")
        return 0

    combined_df = pd.concat(all_melted, ignore_index=True)
    # deduplicate on composite grain: date x dam_id
    combined_df = combined_df.drop_duplicates(subset=["date", "dam_id"]).reset_index(drop=True)

    # ensure clean data types for postgresql
    combined_df["date"] = combined_df["date"].dt.date
    combined_df["dam_id"] = combined_df["dam_id"].astype(str)
    combined_df["reserve_mm3"] = pd.to_numeric(combined_df["reserve_mm3"], errors="coerce")
    combined_df["fill_pct"] = pd.to_numeric(combined_df["fill_pct"], errors="coerce")

    table_name = "stg_reservoirs"
    with engine.begin() as conn:
        # create table if it does not exist yet
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS staging.stg_reservoirs (
                date date,
                dam_id text,
                fill_pct double precision,
                reserve_mm3 double precision
            );
        """))
        # truncate existing data to avoid breaking dependent dbt views
        conn.execute(text("TRUNCATE TABLE staging.stg_reservoirs;"))

    # append fresh staged rows
    combined_df.to_sql(
        table_name,
        engine,
        schema="staging",
        if_exists="append",
        index=False,
        method="multi",
    )
    logging.info(f"Loaded {len(combined_df)} rows into staging.{table_name} successfully.")
    return len(combined_df)


def load_silver_weather_to_staging(engine) -> int:
    """read silver weather parquet files and stage into postgresql via truncate-and-append."""
    logging.info("Reading Silver Weather Parquet files from MinIO...")
    keys = list_objects_in_prefix(SILVER_BUCKET, "cleansed/open_meteo/")
    parquet_keys = [k for k in keys if k.endswith(".parquet")]

    if not parquet_keys:
        logging.warning("No Silver Weather parquet files found in MinIO.")
        return 0

    weather_dfs = []
    for key in parquet_keys:
        df = get_parquet_from_minio(SILVER_BUCKET, key)
        if not df.empty:
            weather_dfs.append(df)

    if not weather_dfs:
        logging.warning("No weather data could be extracted.")
        return 0

    combined_weather = pd.concat(weather_dfs, ignore_index=True)
    combined_weather["date"] = pd.to_datetime(combined_weather["date"]).dt.date

    # Deduplicate on date x location_id
    combined_weather = combined_weather.drop_duplicates(
        subset=["date", "location_id"]
    ).reset_index(drop=True)

    # Cast metrics to proper numeric types
    for col in ["precip_mm", "max_temp_c", "min_temp_c", "latitude", "longitude"]:
        if col in combined_weather.columns:
            combined_weather[col] = pd.to_numeric(combined_weather[col], errors="coerce")

    table_name = "stg_weather"
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS staging.stg_weather (
                date date,
                max_temp_c double precision,
                min_temp_c double precision,
                precip_mm double precision,
                latitude double precision,
                longitude double precision,
                location_id text,
                location_type text
            );
        """))
        conn.execute(text("TRUNCATE TABLE staging.stg_weather;"))

    # Append fresh staged rows
    combined_weather.to_sql(
        table_name,
        engine,
        schema="staging",
        if_exists="append",
        index=False,
        method="multi",
    )
    logging.info(f"Loaded {len(combined_weather)} rows into staging.{table_name} successfully.")
    return len(combined_weather)


def run_silver_to_postgres_loader():
    """
    Main orchestrator for loading Silver Parquet data from MinIO into PostgreSQL.
    Creates the 'staging' schema if missing and populates raw staging tables.
    """
    logging.info("=== STARTING SILVER TO POSTGRESQL STAGING LOADER ===")
    engine = get_postgres_engine()

    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS staging;"))

    ckan_count = load_silver_ckan_to_staging(engine)
    weather_count = load_silver_weather_to_staging(engine)

    logging.info(f"Staging Loader Finished: {ckan_count} reservoir rows, {weather_count} weather rows.")
    logging.info("=== SILVER TO POSTGRESQL LOADER COMPLETE ===\n")


if __name__ == "__main__":
    run_silver_to_postgres_loader()
