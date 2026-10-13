import os
import io
import logging
import pandas as pd
from typing import List, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def partition_dataframe_by_keys(
    df: pd.DataFrame,
    partition_cols: List[str]
) -> List[tuple]:
    """
    splits dataframe into subsets by partition columns.
    returns a list of (partition_values_dict, partition_subset_df).
    """
    if df.empty or not partition_cols:
        return [({}, df.copy())]

    # ensure date year/month columns exist if partitioning by time
    working_df = df.copy()
    if "year" in partition_cols and "year" not in working_df.columns:
        date_col = next((c for c in ["date", "observation_date", "full_date"] if c in working_df.columns), None)
        if date_col:
            working_df["year"] = pd.to_datetime(working_df[date_col]).dt.year

    valid_cols = [c for c in partition_cols if c in working_df.columns]
    if not valid_cols:
        return [({}, working_df)]

    partitions = []
    for keys, group in working_df.groupby(valid_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        key_dict = dict(zip(valid_cols, keys))
        # drop partition columns from the written payload if hive standard
        subset = group.drop(columns=valid_cols).copy()
        partitions.append((key_dict, subset))

    return partitions


def build_hive_path(base_dir: str, partition_keys: dict, filename: str = "part-0000.snappy.parquet") -> str:
    """
    constructs a standard hive partitioning path:
    e.g. base_dir/year=2026/dam_id=yacoub_el_mansour/part-0000.snappy.parquet
    """
    parts = [base_dir]
    for k, v in partition_keys.items():
        parts.append(f"{k}={v}")
    parts.append(filename)
    return os.path.join(*parts)


def compact_parquet_partitions(
    df: pd.DataFrame,
    output_dir: str,
    partition_cols: Optional[List[str]] = None,
    compression: str = "snappy"
) -> int:
    """
    writes partitioned and compacted parquet datasets to disk or buffer.
    returns count of written partition segments.
    """
    if df.empty:
        logging.warning("empty dataframe supplied for parquet compaction.")
        return 0

    p_cols = partition_cols or ["year", "dam_id"]
    partitions = partition_dataframe_by_keys(df, p_cols)

    os.makedirs(output_dir, exist_ok=True)
    count = 0

    for key_dict, subset in partitions:
        out_path = build_hive_path(output_dir, key_dict)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        subset.to_parquet(out_path, engine="pyarrow", compression=compression, index=False)
        count += 1

    logging.info("compacted %s records into %s hive-partitioned files in %s", len(df), count, output_dir)
    return count
