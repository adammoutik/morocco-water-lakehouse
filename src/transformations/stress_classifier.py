from typing import Dict, Any, Optional
import pandas as pd


STRESS_TIERS = {
    "CRITICAL": {
        "color": "#DC2626",
        "description": "Severe storage deficit; reservoir nearing dead-storage threshold",
        "action": "Trigger emergency water allocation plan; restrict non-essential agricultural intake",
    },
    "ALERT": {
        "color": "#EA580C",
        "description": "Depleted reserves; runway under 90 days",
        "action": "Enforce municipal conservation targets; restrict irrigation quotas by 30%",
    },
    "VIGILANCE": {
        "color": "#CA8A04",
        "description": "Moderate reserves; approaching seasonal drawdown limits",
        "action": "Increase monitoring cadence; review inter-basin transfer schedules",
    },
    "NORMAL": {
        "color": "#16A34A",
        "description": "Adequate storage capacity; healthy hydrological buffer",
        "action": "Maintain standard reservoir release curves",
    },
}


def classify_reservoir_stress(fill_pct: float, runway_days: Optional[float] = None) -> Dict[str, Any]:
    """
    evaluate operational water stress tier and response protocol.
    evaluates both current storage volume percentage and zero-rain runway projection.
    """
    if fill_pct is None or pd.isna(fill_pct):
        tier = "VIGILANCE"
    elif fill_pct < 20.0 or (runway_days is not None and pd.notna(runway_days) and 0 <= runway_days < 45):
        tier = "CRITICAL"
    elif fill_pct < 40.0 or (runway_days is not None and pd.notna(runway_days) and 0 <= runway_days < 90):
        tier = "ALERT"
    elif fill_pct < 60.0 or (runway_days is not None and pd.notna(runway_days) and 0 <= runway_days < 180):
        tier = "VIGILANCE"
    else:
        tier = "NORMAL"

    config = STRESS_TIERS[tier]
    return {
        "tier": tier,
        "fill_pct": fill_pct,
        "runway_days": runway_days,
        "color": config["color"],
        "description": config["description"],
        "recommended_action": config["action"],
    }


def add_stress_classification(df: pd.DataFrame) -> pd.DataFrame:
    """
    vectorized enrichment of a reservoir dataframe with stress tier categories and actions.
    """
    if df.empty:
        return df.copy()

    result = df.copy()
    fill_col = None
    for cand in ["fill_percentage", "fill_pct", "fill_ratio_pct"]:
        if cand in result.columns:
            fill_col = cand
            break

    runway_col = "runway_days" if "runway_days" in result.columns else None

    tiers = []
    actions = []

    for idx, row in result.iterrows():
        fill_val = row[fill_col] if fill_col else None
        runway_val = row[runway_col] if runway_col else None
        info = classify_reservoir_stress(fill_val, runway_val)
        tiers.append(info["tier"])
        actions.append(info["recommended_action"])

    result["stress_tier"] = tiers
    result["recommended_action"] = actions
    return result
