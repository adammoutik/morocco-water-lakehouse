import os
import sys
import gzip
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def create_warehouse_snapshot(
    output_dir: str = "infrastructure/backups",
    tables: List[str] = None
) -> Dict[str, Any]:
    """
    generates a timestamped, gzip-compressed snapshot of warehouse analytical marts.
    """
    target_tables = tables or ["dim_reservoir", "dim_date", "fact_reservoir_daily"]
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    snapshot_filename = f"warehouse_marts_snapshot_{timestamp}.json.gz"
    snapshot_path = os.path.join(output_dir, snapshot_filename)

    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "postgres")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "reservoir_db")

    dump_data = {
        "metadata": {
            "snapshot_timestamp": timestamp,
            "database": db,
            "tables": target_tables,
        },
        "tables": {}
    }

    try:
        from sqlalchemy import create_engine
        import pandas as pd
        engine = create_engine(f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}")

        for table in target_tables:
            query = f"SELECT * FROM marts.{table};"
            try:
                df = pd.read_sql(query, engine)
                dump_data["tables"][table] = df.to_dict(orient="records")
                logging.info("captured table marts.%s (%s rows)", table, len(df))
            except Exception as e:
                logging.warning("failed to export table marts.%s: %s", table, e)
                dump_data["tables"][table] = []
    except Exception as exc:
        logging.warning("database connection unavailable (%s); writing empty snapshot structure", exc)

    # write compressed gzip json
    payload = json.dumps(dump_data, default=str).encode("utf-8")
    with gzip.open(snapshot_path, "wb") as gz_file:
        gz_file.write(payload)

    bytes_written = os.path.getsize(snapshot_path)
    logging.info("snapshot successfully saved: %s (%s bytes)", snapshot_path, bytes_written)

    return {
        "snapshot_path": snapshot_path,
        "bytes_written": bytes_written,
        "timestamp": timestamp,
        "tables": target_tables,
    }


def prune_old_snapshots(backup_dir: str = "infrastructure/backups", keep_latest: int = 5) -> int:
    """
    retains only the latest N snapshots to prevent storage bloat.
    """
    if not os.path.exists(backup_dir):
        return 0

    files = [
        os.path.join(backup_dir, f)
        for f in os.listdir(backup_dir)
        if f.startswith("warehouse_marts_snapshot_") and f.endswith(".json.gz")
    ]
    files.sort(key=os.path.getmtime)

    deleted_count = 0
    while len(files) > keep_latest:
        to_delete = files.pop(0)
        try:
            os.remove(to_delete)
            deleted_count += 1
            logging.info("pruned old snapshot: %s", to_delete)
        except OSError as e:
            logging.warning("could not prune file %s: %s", to_delete, e)

    return deleted_count


if __name__ == "__main__":
    snapshot_meta = create_warehouse_snapshot()
    prune_old_snapshots()
    print(f"Backup complete: {snapshot_meta['snapshot_path']}")
