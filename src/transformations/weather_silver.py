import pandas as pd
import logging
from src.config.locations import location_type_for

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def transform_weather_to_silver(
    raw_json: dict,
    location_id: str | None = None,
    location_type: str | None = None,
) -> pd.DataFrame:
    """
    Transforms raw Open-Meteo JSON into a flattened, typed Silver layer DataFrame.
    Grain is date x location_id when location_id is provided.
    """
    logging.info("Starting Silver layer transformation for weather data...")
    
    # 1. Extract the 'daily' arrays
    daily_data = raw_json.get("daily", {})
    if not daily_data:
        logging.error("No 'daily' data found in the raw JSON payload.")
        return pd.DataFrame()

    # 2. Convert to a Pandas DataFrame
    # Because 'daily_data' is a dict of lists of equal length, Pandas instantly makes it a table
    df = pd.DataFrame(daily_data)

    # 3. Clean and Standardize
    # Convert string dates to actual datetime objects
    df['time'] = pd.to_datetime(df['time'])
    
    # Rename columns to standard business naming conventions
    df = df.rename(columns={
        "time": "date",
        "temperature_2m_max": "max_temp_c",
        "temperature_2m_min": "min_temp_c",
        "precipitation_sum": "precip_mm"
    })

    df["latitude"] = raw_json.get("latitude")
    df["longitude"] = raw_json.get("longitude")

    if location_id:
        df["location_id"] = location_id
        df["location_type"] = location_type or location_type_for(location_id)

    logging.info(f"Successfully transformed {len(df)} rows.")
    return df

if __name__ == "__main__":
    mock_json = {
        "latitude": 31.17,
        "longitude": -8.13,
        "daily": {
            "time": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "temperature_2m_max": [22.7, 25.0, 25.3],
            "temperature_2m_min": [9.6, 7.6, 8.3],
            "precipitation_sum": [0.0, 0.0, 0.0]
        }
    }
    
    silver_df = transform_weather_to_silver(
        mock_json, location_id="yacoub_el_mansour", location_type="dam"
    )
    print("\n--- Silver Layer DataFrame ---")
    print(silver_df.head())
    print("\n--- Data Types ---")
    print(silver_df.dtypes)
