import argparse
import logging
from src.config.locations import LOCATIONS
from src.extraction.extract_ck import extract_ckan_data
from src.extraction.weather_client import extract_historical_weather
from src.storage.minio_handler import (
    init_bucket,
    download_resources,
    ingest_weather_to_bronze_or_quarantine
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def ingest_ckan_data(query: str = "tensift", rows: int = 10):
    """ingest ckan reservoir bulletins into bronze."""
    logging.info(f"=== STARTING CKAN INGESTION (query='{query}', rows={rows}) ===")
    datasets = extract_ckan_data(query, rows=rows)
    
    if not datasets:
        logging.warning("No CKAN datasets found or extraction failed.")
        return

    logging.info(f"Found {len(datasets)} dataset(s). Streaming to MinIO Bronze...")
    download_resources(datasets)
    logging.info("=== CKAN INGESTION COMPLETE ===\n")


def ingest_weather_data(start_date: str = "2026-08-01", end_date: str = "2026-09-30"):
    """ingest multi-station weather data into bronze."""
    logging.info(f"=== STARTING WEATHER INGESTION ({start_date} to {end_date}) ===")

    for location_id, site in LOCATIONS.items():
        lat, lon = site["latitude"], site["longitude"]
        object_key = f"raw/open_meteo/{location_id}_{start_date}_to_{end_date}.json"
        logging.info(
            "Fetching weather for %s (%s) at %s, %s",
            location_id,
            site["location_type"],
            lat,
            lon,
        )
        try:
            weather_data = extract_historical_weather(lat, lon, start_date, end_date)
        except Exception:
            logging.exception("Weather extraction failed for %s. Skipping site.", location_id)
            continue

        if not weather_data:
            logging.warning("Weather extraction returned no data for %s. Skipping.", location_id)
            continue

        # validate payload contract and land in bronze or quarantine
        ok, final_key, reason = ingest_weather_to_bronze_or_quarantine(weather_data, object_key)
        if ok:
            logging.info(f"Weather successfully landed in Bronze: {final_key}")
        else:
            logging.warning(f"Weather payload was quarantined for {location_id}: {final_key} (reason={reason})")

    logging.info("=== WEATHER INGESTION COMPLETE ===\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Morocco Water Lakehouse Bronze Data")
    parser.add_argument("--start-date", default="2026-08-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", default="2026-09-30", help="End date (YYYY-MM-DD)")
    parser.add_argument("--ckan-query", default="tensift", help="CKAN search query")
    parser.add_argument("--ckan-rows", type=int, default=10, help="Max CKAN datasets to inspect")
    args = parser.parse_args()

    logging.info("Starting Morocco Water Reliability Lakehouse Ingestion Pipeline...")
    
    # ensure buckets exist before ingestion
    init_bucket()

    ingest_ckan_data(query=args.ckan_query, rows=args.ckan_rows)
    ingest_weather_data(start_date=args.start_date, end_date=args.end_date)

    logging.info("All Bronze layer ingestion tasks finished successfully!")