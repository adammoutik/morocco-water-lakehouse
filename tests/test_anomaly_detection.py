import pytest
import pandas as pd
import numpy as np
from src.transformations.anomaly_detection import (
    detect_hydrological_anomalies,
    summarize_anomaly_metrics,
)


def test_detect_anomalies_bounds_violation():
    data = {
        "dam_name": ["Dam A", "Dam A", "Dam A"],
        "observation_date": ["2026-01-01", "2026-01-02", "2026-01-03"],
        "fill_percentage": [50.0, -5.0, 105.0],
        "current_volume_mm3": [50.0, -2.0, 105.0],
    }
    df = pd.DataFrame(data)
    result = detect_hydrological_anomalies(df)

    assert result.loc[0, "is_anomaly"] == False
    assert result.loc[1, "is_anomaly"] == True
    assert "fill_below_zero" in result.loc[1, "anomaly_details"]
    assert "negative_volume" in result.loc[1, "anomaly_details"]
    assert result.loc[2, "is_anomaly"] == True
    assert "fill_above_100" in result.loc[2, "anomaly_details"]


def test_detect_anomalies_sudden_jump():
    data = {
        "dam_name": ["Dam B", "Dam B"],
        "observation_date": ["2026-01-01", "2026-01-02"],
        "fill_percentage": [20.0, 60.0],  # 40% jump
        "current_volume_mm3": [20.0, 60.0],
    }
    df = pd.DataFrame(data)
    result = detect_hydrological_anomalies(df, max_daily_jump_pct=25.0)

    assert result.loc[1, "is_anomaly"] == True
    assert "sudden_jump" in result.loc[1, "anomaly_details"]


def test_summarize_anomaly_metrics():
    df = pd.DataFrame({
        "is_anomaly": [True, False, False, True]
    })
    summary = summarize_anomaly_metrics(df)
    assert summary["total_records"] == 4
    assert summary["anomaly_count"] == 2
    assert summary["anomaly_rate_pct"] == 50.0
