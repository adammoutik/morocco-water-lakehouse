import os
import sys
import subprocess
import logging

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.storage.load_silver_to_postgres import run_silver_to_postgres_loader

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def run_dbt_command(command: str):
    """execute dbt command targeting local dbt project and profiles."""
    dbt_executable = os.path.join(PROJECT_ROOT, ".venv", "Scripts", "dbt.exe")
    if not os.path.exists(dbt_executable):
        dbt_executable = "dbt"  # Fallback to system path

    cmd = [
        dbt_executable,
        command,
        "--project-dir",
        os.path.join(PROJECT_ROOT, "dbt_project"),
        "--profiles-dir",
        os.path.join(PROJECT_ROOT, "dbt_project"),
    ]
    logging.info(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=True)
    return result.returncode


def run_full_warehouse_pipeline():
    """
    Orchestrates the entire Data Warehouse / Gold layer process:
    1. Stages Silver Parquet files from MinIO into PostgreSQL staging schema.
    2. Runs dbt transformations to build the Star Schema (dim_reservoir, dim_date, fact_reservoir_daily).
    3. Runs dbt data quality test assertions.
    """
    logging.info("=== STARTING FULL POSTGRESQL + DBT WAREHOUSE PIPELINE ===")

    # Step 1: Load Silver to PostgreSQL staging
    run_silver_to_postgres_loader()

    # Step 2: Run dbt models
    logging.info("--- Step 2: Executing dbt Models (Star Schema Build) ---")
    run_dbt_command("run")

    # Step 3: Run dbt data tests
    logging.info("--- Step 3: Executing dbt Test Suite (Data Quality Assertions) ---")
    run_dbt_command("test")

    logging.info("=== FULL POSTGRESQL + DBT WAREHOUSE PIPELINE FINISHED SUCCESSFULLY ===\n")


if __name__ == "__main__":
    run_full_warehouse_pipeline()
