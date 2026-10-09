"""local pipeline orchestrator runner."""

import os
import sys
import time
import logging
from datetime import datetime

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dags.morocco_water_lakehouse_dag import (
    task_ingest_ckan_bronze_callable,
    task_ingest_weather_bronze_callable,
    task_transform_ckan_silver_callable,
    task_transform_weather_silver_callable,
    task_load_silver_to_postgres_callable,
    task_dbt_run_callable,
    task_dbt_test_callable,
    task_gold_parquet_backup_callable,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)


def execute_pipeline_step(step_name: str, callable_func):
    """
    Executes a task step with start/stop banner and execution duration tracking.
    """
    logging.info(f"{'='*25} START: {step_name} {'='*25}")
    start_time = time.time()
    try:
        callable_func()
        duration = time.time() - start_time
        logging.info(f"SUCCESS: {step_name} completed in {duration:.2f}s\n")
        return True, duration
    except Exception as e:
        duration = time.time() - start_time
        logging.error(f"FAILED: {step_name} failed after {duration:.2f}s: {e}\n")
        raise


def run_full_lakehouse_orchestration():
    """
    Executes all 8 tasks in the exact topological dependency order of the Airflow DAG:
    1. Ingest CKAN Bronze (with Quarantine Gatekeeper)
    2. Ingest Weather Bronze (with JSON Data Contract Validator)
    3. Transform CKAN Silver (Parquet conversion + accent/comma cleanup)
    4. Transform Weather Silver (Parquet conversion + time-series flattening)
    5. Load Silver to Postgres Staging (Truncate-and-Append)
    6. Run dbt Star Schema Models (dim_reservoir, dim_date, fact_reservoir_daily)
    7. Run dbt Test Suite (22 automated quality assertions)
    8. Build MinIO Gold Analytical Master Parquet
    """
    pipeline_start = time.time()
    logging.info("********************************************************************************")
    logging.info("  MOROCCO TENSIFT WATER RELIABILITY LAKEHOUSE: END-TO-END ORCHESTRATION RUN     ")
    logging.info(f"  Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                     ")
    logging.info("********************************************************************************\n")

    steps = [
        ("Task 1A: Ingest CKAN Reservoir Data to Bronze", task_ingest_ckan_bronze_callable),
        ("Task 1B: Ingest Open-Meteo Weather Data to Bronze", task_ingest_weather_bronze_callable),
        ("Task 2A: Transform CKAN Reservoir Data to Silver Parquet", task_transform_ckan_silver_callable),
        ("Task 2B: Transform Weather Data to Silver Parquet", task_transform_weather_silver_callable),
        ("Task 3: Load Silver Datasets to PostgreSQL Staging", task_load_silver_to_postgres_callable),
        ("Task 4: Execute dbt Models (Star Schema Build)", task_dbt_run_callable),
        ("Task 5: Execute dbt Data Quality Assertions (22 Tests)", task_dbt_test_callable),
        ("Task 6: Generate Master Gold Parquet in MinIO", task_gold_parquet_backup_callable),
    ]

    report = []
    for name, func in steps:
        success, duration = execute_pipeline_step(name, func)
        report.append((name, "SUCCESS" if success else "FAILED", f"{duration:.2f}s"))

    total_duration = time.time() - pipeline_start
    logging.info("********************************************************************************")
    logging.info("                       PIPELINE EXECUTION SUMMARY REPORT                        ")
    logging.info("********************************************************************************")
    for name, status, duration in report:
        logging.info(f"  {status:<10} | {duration:>8} | {name}")
    logging.info("--------------------------------------------------------------------------------")
    logging.info(f"  TOTAL TIME: {total_duration:.2f}s | All layers validated & verified!")
    logging.info("********************************************************************************\n")


if __name__ == "__main__":
    run_full_lakehouse_orchestration()
