import pandas as pd
import logging
from src.config.locations import BASIN_LOCATION_ID, dam_location_ids

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

WEATHER_METRICS = ["precip_mm", "max_temp_c", "min_temp_c"]


def _rename_ckan_columns(ckan_df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardizes column names for reserve volume and fill percentage.
    Also ensures decimal comma strings are safely parsed to float.
    """
    rename_map = {}
    for col in ckan_df.columns:
        if col.endswith(".1"):
            rename_map[col] = col.replace(".1", "_fill_pct")
        elif col not in ["date", "jour"]:
            rename_map[col] = col + "_reserve_mm3"

    ckan_df = ckan_df.rename(columns=rename_map)

    numeric_cols = [col for col in ckan_df.columns if "_fill_pct" in col or "_reserve_mm3" in col]
    for col in numeric_cols:
        # parse french decimal commas to floats
        if ckan_df[col].dtype == "object":
            ckan_df[col] = ckan_df[col].astype(str).str.strip().str.replace(",", ".")
        ckan_df[col] = pd.to_numeric(ckan_df[col], errors="coerce")

    if "jour" in ckan_df.columns:
        ckan_df = ckan_df.drop(columns=["jour"])

    return ckan_df


def _melt_reservoirs(ckan_df: pd.DataFrame) -> pd.DataFrame:
    fill_cols = [c for c in ckan_df.columns if c.endswith("_fill_pct")]
    reserve_cols = [c for c in ckan_df.columns if c.endswith("_reserve_mm3")]

    if not fill_cols:
        logging.error("No reservoir fill-percentage columns found after CKAN rename.")
        return pd.DataFrame()

    fill_long = ckan_df.melt(
        id_vars=["date"], value_vars=fill_cols, var_name="_col", value_name="fill_pct"
    )
    fill_long["dam_id"] = fill_long["_col"].str.removesuffix("_fill_pct")
    fill_long = fill_long[["date", "dam_id", "fill_pct"]]

    if not reserve_cols:
        fill_long["reserve_mm3"] = pd.NA
        return fill_long

    reserve_long = ckan_df.melt(
        id_vars=["date"], value_vars=reserve_cols, var_name="_col", value_name="reserve_mm3"
    )
    reserve_long["dam_id"] = reserve_long["_col"].str.removesuffix("_reserve_mm3")
    reserve_long = reserve_long[["date", "dam_id", "reserve_mm3"]]

    return fill_long.merge(reserve_long, on=["date", "dam_id"], how="outer")


def _prepare_weather(weather_df: pd.DataFrame) -> pd.DataFrame:
    weather_df = weather_df.copy()
    weather_df["date"] = pd.to_datetime(weather_df["date"])

    if "location_id" not in weather_df.columns:
        logging.warning(
            "Silver weather has no location_id; treating the series as Tensift basin weather."
        )
        weather_df["location_id"] = BASIN_LOCATION_ID
        weather_df["location_type"] = "basin"

    # deduplicate weather records by date and location
    return weather_df.drop_duplicates(subset=["date", "location_id"])


def _basin_weather(weather_df: pd.DataFrame) -> pd.DataFrame:
    if "location_type" in weather_df.columns:
        basin = weather_df[weather_df["location_type"] == "basin"].copy()
    else:
        basin = pd.DataFrame()

    if basin.empty:
        basin = weather_df[weather_df["location_id"] == BASIN_LOCATION_ID].copy()

    if basin.empty:
        logging.error("No basin weather rows found (expected location_id=%s).", BASIN_LOCATION_ID)
        return pd.DataFrame()

    keep = ["date"] + [c for c in WEATHER_METRICS if c in basin.columns]
    basin = basin[keep].rename(columns={c: f"{c}_basin" for c in WEATHER_METRICS if c in basin.columns})
    return basin.drop_duplicates(subset=["date"])


def _local_weather(weather_df: pd.DataFrame) -> pd.DataFrame:
    catalog_dams = dam_location_ids()
    local = weather_df[weather_df["location_id"].isin(catalog_dams)].copy()
    if "location_type" in local.columns:
        local = local[local["location_type"] != "basin"]

    keep = ["date", "location_id"] + [c for c in WEATHER_METRICS + ["latitude", "longitude"] if c in local.columns]
    local = local[keep].rename(columns={"location_id": "dam_id"})
    return local


def build_gold_analytical_model(weather_df: pd.DataFrame, ckan_df: pd.DataFrame) -> pd.DataFrame:
    """join reservoir and weather data into date x dam_id analytical grain."""
    logging.info("Starting Gold layer aggregation...")

    ckan_df = _rename_ckan_columns(ckan_df.copy())
    ckan_df["date"] = pd.to_datetime(ckan_df["date"])

    # drop duplicate dates keeping latest observation
    ckan_df = ckan_df.drop_duplicates(subset=["date"], keep="last")

    reservoirs = _melt_reservoirs(ckan_df)
    if reservoirs.empty:
        return reservoirs

    weather_df = _prepare_weather(weather_df)
    basin_wx = _basin_weather(weather_df)
    if basin_wx.empty:
        return pd.DataFrame()

    gold_df = reservoirs.merge(basin_wx, on="date", how="inner")

    local_wx = _local_weather(weather_df)
    if not local_wx.empty:
        gold_df = gold_df.merge(local_wx, on=["date", "dam_id"], how="left")
    else:
        logging.warning("No dam-site weather found; all dams will use Tensift basin rainfall.")

    unmapped = set(gold_df["dam_id"].unique()) - dam_location_ids()
    if unmapped:
        logging.warning(
            "No dam-site weather catalog entry for %s; filling local precip/temp from Tensift basin.",
            sorted(unmapped),
        )

    for col in WEATHER_METRICS:
        basin_col = f"{col}_basin"
        if col not in gold_df.columns:
            gold_df[col] = gold_df[basin_col] if basin_col in gold_df.columns else pd.NA
        elif basin_col in gold_df.columns:
            gold_df[col] = gold_df[col].fillna(gold_df[basin_col])

    # deduplicate by date and dam_id and sort chronologically
    gold_df = gold_df.drop_duplicates(subset=["date", "dam_id"]).sort_values(["dam_id", "date"]).reset_index(drop=True)

    logging.info("Gold table successfully created with shape: %s (grain: date x dam_id)", gold_df.shape)
    return gold_df
