import pandas as pd
import logging
import re

# A dictionary to map French months from the filename to numeric months
FRENCH_MONTHS = {
    'janvier': '01', 'fevrier': '02', 'mars': '03', 'avril': '04',
    'mai': '05', 'juin': '06', 'juillet': '07', 'aout': '08',
    'sept': '09', 'septembre': '09', 'oct': '10', 'octobre': '10', 
    'nov': '11', 'novembre': '11', 'dec': '12', 'decembre': '12'
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def transform_ckan_to_silver(df: pd.DataFrame, filename: str) -> pd.DataFrame:
    """
    Deep-cleans government CKAN Excel data by extracting dates from filenames 
    and dropping multi-level headers.
    """
    logging.info(f"Starting CKAN transformation for {filename}. Initial shape: {df.shape}")

    if df.empty:
        return df

    # clean Column Names
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace('-', '_')
    df = df.rename(columns={'bassin': 'jour'}) # Rename the first column to 'jour'

    # drop the weird header rows
    # the first two rows (index 0 and 1)
    df = df.iloc[2:].reset_index(drop=True)
    df = df.dropna(how='all')

    # extract Month and Year from the filename using Regex
    filename_lower = filename.lower()
    year = re.search(r'20\d{2}', filename_lower).group() if re.search(r'20\d{2}', filename_lower) else '2024'
    
    # find the month in the filename
    month = '01' 
    for fr_month, num in FRENCH_MONTHS.items():
        if fr_month in filename_lower:
            month = num
            break
            
    # create a real 'date' column!
    # force 'jour' to be a clean two-digit string
    df['jour'] = pd.to_numeric(df['jour'], errors='coerce').fillna(1).astype(int).astype(str).str.zfill(2)
    
    # combine Year-Month-Day
    df['date'] = pd.to_datetime(year + '-' + month + '-' + df['jour'], errors='coerce')

    # type casting for Parquet
    object_columns = df.select_dtypes(include=['object']).columns
    for col in object_columns:
        df[col] = df[col].astype(str)

    logging.info(f"Finished CKAN transformation. Final shape: {df.shape}")
    return df