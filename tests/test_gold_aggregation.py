import pytest
import pandas as pd
from src.transformations.gold_aggregation import build_gold_analytical_model


def test_build_gold_analytical_model_structure_and_deduplication():
    """verify gold analytical model structure and deduplication."""
    # Create CKAN with duplicate date rows (e.g. from overlapping file imports)
    ckan_data = {
        "date": ["2026-08-01", "2026-08-01", "2026-08-02"],
        "yacoub_el_mansour": [49.44, 49.44, 49.12],
        "yacoub_el_mansour.1": [86.05, 86.05, 85.50],
        "lalla_takerkoust": [20.0, 20.0, 19.8],
        "lalla_takerkoust.1": [40.0, 40.0, 39.5],
    }
    ckan_df = pd.DataFrame(ckan_data)

    weather_data = {
        "date": ["2026-08-01", "2026-08-02", "2026-08-01", "2026-08-02", "2026-08-01", "2026-08-02"],
        "location_id": ["tensift_basin", "tensift_basin", "yacoub_el_mansour", "yacoub_el_mansour", "lalla_takerkoust", "lalla_takerkoust"],
        "location_type": ["basin", "basin", "dam", "dam", "dam", "dam"],
        "precip_mm": [5.0, 0.0, 10.0, 0.0, 2.0, 0.0],
        "max_temp_c": [35.0, 36.0, 30.0, 31.0, 32.0, 33.0],
        "min_temp_c": [20.0, 21.0, 18.0, 19.0, 19.0, 20.0],
    }
    weather_df = pd.DataFrame(weather_data)

    gold_df = build_gold_analytical_model(weather_df, ckan_df)

    assert not gold_df.empty
    # Expect 2 unique dates x 2 dams = 4 rows (no duplicate 2026-08-01 rows!)
    assert len(gold_df) == 4
    assert set(gold_df["dam_id"].unique()) == {"yacoub_el_mansour", "lalla_takerkoust"}
    assert "fill_pct" in gold_df.columns
    assert "reserve_mm3" in gold_df.columns
    assert "precip_mm_basin" in gold_df.columns
    assert "precip_mm" in gold_df.columns

    # Verify Yacoub El Mansour local rain vs basin rain
    ym_day1 = gold_df[(gold_df["dam_id"] == "yacoub_el_mansour") & (gold_df["date"] == pd.Timestamp("2026-08-01"))].iloc[0]
    assert ym_day1["precip_mm"] == 10.0
    assert ym_day1["precip_mm_basin"] == 5.0
