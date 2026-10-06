import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def build_gold_analytical_model(weather_df: pd.DataFrame, ckan_df: pd.DataFrame) -> pd.DataFrame:
    """
    Joins Silver weather and reservoir data into a single, analytics-ready Gold dataset.
    """
    logging.info("Starting Gold layer aggregation...")

    rename_map = {}
    for col in ckan_df.columns:
        if col.endswith('.1'):
            rename_map[col] = col.replace('.1', '_fill_pct')
        elif col not in ['date', 'jour']:
            rename_map[col] = col + '_reserve_mm3'
            
    ckan_df = ckan_df.rename(columns=rename_map)
    
    numeric_cols = [col for col in ckan_df.columns if '_fill_pct' in col or '_reserve_mm3' in col]
    for col in numeric_cols:
        ckan_df[col] = pd.to_numeric(ckan_df[col], errors='coerce')

    if 'jour' in ckan_df.columns:
        ckan_df = ckan_df.drop(columns=['jour'])

    gold_df = pd.merge(weather_df, ckan_df, on='date', how='inner')
    
    logging.info(f"Gold table successfully created with shape: {gold_df.shape}")
    return gold_df