import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def transform_ckan_to_silver(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans raw CKAN Excel data by standardizing column names and removing empty rows.
    """
    logging.info(f"Starting CKAN transformation. Initial shape: {df.shape}")

    if df.empty:
        logging.warning("DataFrame is empty. Skipping transformation.")
        return df

    # clean Column Names
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace('-', '_')

    # drop completely empty rows (common in Excel formatting)
    df = df.dropna(how='all')

    # standardize Date formatting (if a date column exists)
    date_columns = [col for col in df.columns if 'date' in col]
    for date_col in date_columns:
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')

    object_columns = df.select_dtypes(include=['object']).columns
    
    for col in object_columns:
        df[col] = df[col].astype(str)

    logging.info(f"Finished CKAN transformation. Final shape: {df.shape}")
    return df