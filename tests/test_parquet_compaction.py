import os
import shutil
import tempfile
import pytest
import pandas as pd
from src.storage.parquet_compaction import (
    partition_dataframe_by_keys,
    build_hive_path,
    compact_parquet_partitions,
)


def test_build_hive_path():
    path = build_hive_path("data/gold", {"year": 2026, "dam_id": "yacoub"}, "data.parquet")
    assert "year=2026" in path
    assert "dam_id=yacoub" in path
    assert path.endswith("data.parquet")


def test_compact_parquet_partitions():
    temp_dir = tempfile.mkdtemp()
    try:
        df = pd.DataFrame({
            "date": ["2026-08-01", "2026-08-02", "2026-08-01", "2026-08-02"],
            "dam_id": ["dam1", "dam1", "dam2", "dam2"],
            "fill_pct": [50.0, 49.5, 75.0, 74.8],
        })

        file_count = compact_parquet_partitions(df, temp_dir, partition_cols=["dam_id"])
        assert file_count == 2

        # Check directories exist
        assert os.path.exists(os.path.join(temp_dir, "dam_id=dam1"))
        assert os.path.exists(os.path.join(temp_dir, "dam_id=dam2"))
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
