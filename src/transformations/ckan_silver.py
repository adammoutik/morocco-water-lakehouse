import pandas as pd
import logging
import re
import unicodedata

# A dictionary to map French months (full names and common abbreviations) to 2-digit numeric months
FRENCH_MONTHS = {
    'janvier': '01', 'janv': '01',
    'fevrier': '02', 'fevr': '02',
    'mars': '03',
    'avril': '04', 'avr': '04',
    'mai': '05',
    'juin': '06',
    'juillet': '07', 'juil': '07',
    'aout': '08',
    'septembre': '09', 'sept': '09',
    'octobre': '10', 'oct': '10',
    'novembre': '11', 'nov': '11',
    'decembre': '12', 'dec': '12'
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def _strip_accents(text: str) -> str:
    """strip accents from french text."""
    normalized = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in normalized if not unicodedata.combining(c))


def transform_ckan_to_silver(df: pd.DataFrame, filename: str) -> pd.DataFrame:
    """clean ckan excel bulletins and export to silver structure."""
    logging.info(f"Starting CKAN transformation for {filename}. Initial shape: {df.shape}")

    if df.empty:
        return df

    # clean column names
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace('-', '_')
    df = df.rename(columns={'bassin': 'jour'})

    # drop multi-level header rows
    df = df.iloc[2:].reset_index(drop=True)
    df = df.dropna(how='all')

    # extract year and month from filename
    filename_clean = _strip_accents(filename.lower())
    year_match = re.search(r'20\d{2}', filename_clean)
    if year_match:
        year = year_match.group()
    else:
        logging.warning(f"Could not extract 4-digit year from filename '{filename}'. Defaulting to current year.")
        year = '2026'

    month = None
    for fr_month in sorted(FRENCH_MONTHS.keys(), key=len, reverse=True):
        if fr_month in filename_clean:
            month = FRENCH_MONTHS[fr_month]
            break

    if not month:
        logging.warning(f"Could not extract month from filename '{filename}'. Defaulting to '01'.")
        month = '01'

    # drop footer summary rows and invalid days
    jour_num = pd.to_numeric(df['jour'], errors='coerce')
    valid_day_mask = jour_num.notna() & (jour_num >= 1) & (jour_num <= 31)
    df = df.loc[valid_day_mask].copy()

    df['jour'] = jour_num.loc[valid_day_mask].astype(int).astype(str).str.zfill(2)

    # create standardized iso date column
    df['date'] = pd.to_datetime(year + '-' + month + '-' + df['jour'], errors='coerce')
    df = df.dropna(subset=['date']).copy()

    # convert french comma decimals to dots and cast to float
    measurement_cols = [c for c in df.columns if c not in ['jour', 'date']]
    for col in measurement_cols:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.strip().str.replace(',', '.')
        df[col] = pd.to_numeric(df[col], errors='coerce')

    logging.info(f"Finished CKAN transformation. Final shape: {df.shape}")
    return df