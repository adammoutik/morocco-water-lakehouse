import os
import shutil
import tempfile
import gzip
import json
import pytest
from infrastructure.scripts.backup_warehouse import create_warehouse_snapshot, prune_old_snapshots


def test_create_warehouse_snapshot():
    temp_dir = tempfile.mkdtemp()
    try:
        res = create_warehouse_snapshot(output_dir=temp_dir, tables=["dim_reservoir"])
        assert os.path.exists(res["snapshot_path"])
        assert res["bytes_written"] > 0

        # verify gzip readable
        with gzip.open(res["snapshot_path"], "rt", encoding="utf-8") as f:
            content = json.load(f)
        assert "metadata" in content
        assert "tables" in content
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_prune_old_snapshots():
    temp_dir = tempfile.mkdtemp()
    try:
        # Create 7 mock snapshot files
        for i in range(7):
            fname = os.path.join(temp_dir, f"warehouse_marts_snapshot_20261013_{i:02d}.json.gz")
            with open(fname, "wb") as f:
                f.write(b"mock data")

        pruned = prune_old_snapshots(backup_dir=temp_dir, keep_latest=5)
        assert pruned == 2
        remaining = [f for f in os.listdir(temp_dir) if f.startswith("warehouse_marts_snapshot_")]
        assert len(remaining) == 5
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
