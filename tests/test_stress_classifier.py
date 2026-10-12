import pytest
import pandas as pd
from src.transformations.stress_classifier import (
    classify_reservoir_stress,
    add_stress_classification,
    STRESS_TIERS,
)


def test_classify_reservoir_stress_tiers():
    # critical tests
    crit = classify_reservoir_stress(15.0, runway_days=30.0)
    assert crit["tier"] == "CRITICAL"
    assert crit["color"] == STRESS_TIERS["CRITICAL"]["color"]

    # alert tests
    alert = classify_reservoir_stress(35.0, runway_days=70.0)
    assert alert["tier"] == "ALERT"

    # vigilance tests
    vig = classify_reservoir_stress(55.0, runway_days=120.0)
    assert vig["tier"] == "VIGILANCE"

    # normal tests
    norm = classify_reservoir_stress(80.0, runway_days=250.0)
    assert norm["tier"] == "NORMAL"


def test_add_stress_classification_dataframe():
    df = pd.DataFrame({
        "dam_name": ["Dam A", "Dam B", "Dam C"],
        "fill_percentage": [15.0, 35.0, 75.0],
        "runway_days": [20.0, 80.0, 200.0],
    })
    enriched = add_stress_classification(df)

    assert "stress_tier" in enriched.columns
    assert "recommended_action" in enriched.columns
    assert enriched["stress_tier"].tolist() == ["CRITICAL", "ALERT", "NORMAL"]
