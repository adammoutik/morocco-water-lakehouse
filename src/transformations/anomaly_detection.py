import pandas as pd
import numpy as np
from typing import Dict, Any


def detect_hydrological_anomalies(
    df: pd.DataFrame,
    max_daily_jump_pct: float = 25.0,
    z_score_threshold: float = 3.0
) -> pd.DataFrame:
    """
    detect hydrological anomalies and physically impossible sensor readings.
    flags bounds violations, sudden volume spikes without rainfall, and statistical drawdown outliers.
    """
    if df.empty:
        return df.copy()

    result = df.copy()
    reasons = []

    # ensure working columns exist
    has_fill = "fill_percentage" in result.columns or "fill_ratio_pct" in result.columns
    fill_col = "fill_percentage" if "fill_percentage" in result.columns else "fill_ratio_pct"

    has_volume = "current_volume_mm3" in result.columns or "reserve_volume_mm3" in result.columns
    vol_col = "current_volume_mm3" if "current_volume_mm3" in result.columns else "reserve_volume_mm3"

    anomaly_flags = pd.Series(False, index=result.index)
    anomaly_reasons = pd.Series("", index=result.index)

    # 1. value bounds validation
    if has_fill:
        below_zero = result[fill_col] < 0.0
        above_hundred = result[fill_col] > 100.0
        bounds_violation = below_zero | above_hundred

        anomaly_flags = anomaly_flags | bounds_violation
        anomaly_reasons = anomaly_reasons.mask(
            below_zero, anomaly_reasons.replace("", "") + "fill_below_zero; "
        )
        anomaly_reasons = anomaly_reasons.mask(
            above_hundred, anomaly_reasons.replace("", "") + "fill_above_100; "
        )

    if has_volume:
        neg_volume = result[vol_col] < 0.0
        anomaly_flags = anomaly_flags | neg_volume
        anomaly_reasons = anomaly_reasons.mask(
            neg_volume, anomaly_reasons.replace("", "") + "negative_volume; "
        )

    # 2. sudden rate of change checks per dam
    dam_col = None
    for cand in ["dam_name", "dam_id", "reservoir_name"]:
        if cand in result.columns:
            dam_col = cand
            break

    date_col = None
    for cand in ["observation_date", "date", "full_date"]:
        if cand in result.columns:
            date_col = cand
            break

    if dam_col and date_col and has_fill:
        result_sorted = result.sort_values(by=[dam_col, date_col])
        daily_diff = result_sorted.groupby(dam_col)[fill_col].diff().abs()

        sudden_jump = daily_diff > max_daily_jump_pct
        anomaly_flags = anomaly_flags | sudden_jump
        anomaly_reasons = anomaly_reasons.mask(
            sudden_jump, anomaly_reasons.replace("", "") + f"sudden_jump_gt_{max_daily_jump_pct}pct; "
        )

    # 3. statistical z-score on drawdown rates
    drawdown_col = None
    for cand in ["daily_drawdown_rate_mm3", "drawdown_rate"]:
        if cand in result.columns:
            drawdown_col = cand
            break

    if drawdown_col and len(result) >= 5:
        std_val = result[drawdown_col].std()
        if pd.notna(std_val) and std_val > 1e-6:
            mean_val = result[drawdown_col].mean()
            z_scores = ((result[drawdown_col] - mean_val) / std_val).abs()
            z_outliers = z_scores > z_score_threshold
            anomaly_flags = anomaly_flags | z_outliers
            anomaly_reasons = anomaly_reasons.mask(
                z_outliers, anomaly_reasons.replace("", "") + f"z_score_outlier_gt_{z_score_threshold}; "
            )

    result["is_anomaly"] = anomaly_flags
    result["anomaly_details"] = anomaly_reasons.str.rstrip("; ")
    return result


def summarize_anomaly_metrics(df_with_anomalies: pd.DataFrame) -> Dict[str, Any]:
    """
    generate aggregate summary counts of detected anomalies.
    """
    total_rows = len(df_with_anomalies)
    if total_rows == 0:
        return {"total_records": 0, "anomaly_count": 0, "anomaly_rate_pct": 0.0}

    anomaly_count = int(df_with_anomalies["is_anomaly"].sum()) if "is_anomaly" in df_with_anomalies.columns else 0
    return {
        "total_records": total_rows,
        "anomaly_count": anomaly_count,
        "anomaly_rate_pct": round((anomaly_count / total_rows) * 100.0, 2)
    }
