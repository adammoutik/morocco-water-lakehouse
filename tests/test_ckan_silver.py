import pytest
import pandas as pd
from src.transformations.ckan_silver import transform_ckan_to_silver


def test_transform_ckan_accented_month_and_decimal_commas():
    """verify french accented months and decimal comma parsing."""
    raw_data = {
        "Bassin": ["CAPACITE NORMALE (Mm3)", "JOUR", "1", "2"],
        "Yacoub El Mansour": [57.45, "RESERVE (Mm3)", "49,44", "49.12"],
        "Yacoub El Mansour.1": [57.45, "TAUX DE REMPLISSAGE (%)", "86,05", "85.50"],
    }
    df_raw = pd.DataFrame(raw_data)
    filename = "data_barrages_tensift_août_2026.xlsx"

    silver_df = transform_ckan_to_silver(df_raw, filename)

    assert not silver_df.empty
    assert len(silver_df) == 2
    # verify month resolution
    assert silver_df["date"].iloc[0] == pd.Timestamp("2026-08-01")
    assert silver_df["date"].iloc[1] == pd.Timestamp("2026-08-02")
    # verify comma decimal parsed as float
    assert silver_df["yacoub_el_mansour"].iloc[0] == pytest.approx(49.44)
    assert silver_df["yacoub_el_mansour.1"].iloc[0] == pytest.approx(86.05)


def test_transform_ckan_drops_summary_footer_rows():
    """verify footer summary rows are safely dropped."""
    raw_data = {
        "Bassin": ["CAPACITE NORMALE (Mm3)", "JOUR", "1", "2", "Total", "Moyenne"],
        "Yacoub El Mansour": [57.45, "RESERVE (Mm3)", "49.44", "49.12", "98.56", "49.28"],
        "Yacoub El Mansour.1": [57.45, "TAUX DE REMPLISSAGE (%)", "86.05", "85.50", "-", "-"],
    }
    df_raw = pd.DataFrame(raw_data)
    filename = "data_barrages_tensift_septembre_2026.xlsx"

    silver_df = transform_ckan_to_silver(df_raw, filename)

    # Should keep only day 1 and day 2
    assert len(silver_df) == 2
    assert list(silver_df["jour"]) == ["01", "02"]
    assert silver_df["date"].iloc[0] == pd.Timestamp("2026-09-01")
    assert silver_df["date"].iloc[1] == pd.Timestamp("2026-09-02")
