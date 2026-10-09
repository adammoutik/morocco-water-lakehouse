"""airflow orchestration dag for morocco tensift lakehouse."""

from datetime import datetime, timedelta
import os
import sys
import logging

# ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# airflow imports
try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator
    from airflow.operators.bash import BashOperator
except ImportError:
    logging.warning("airflow is not installed in the current environment.")
    DAG = None
    PythonOperator = None
    BashOperator = None

# default task execution arguments
default_args = {
    "owner": "data_engineering_lakehouse",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
    "execution_timeout": timedelta(minutes=15),
}

# task callables

def task_ingest_ckan_bronze_callable():
    """ingest tensift reservoir bulletins to bronze."""
    from run_ingestion import ingest_ckan_data
    logging.info("ingesting ckan reservoir bulletins to bronze...")
    ingest_ckan_data(query="tensift", rows=10)


def task_ingest_weather_bronze_callable():
    """
    Step 1B: Ingest Multi-Station Weather Records to Bronze.
    Queries Open-Meteo API for basin center and all 5 dams, validates JSON schema
    contract (array dimensions and required metrics), and uploads to MinIO Bronze.
    """
def task_ingest_weather_bronze_callable():
    """ingest multi-station weather records to bronze."""
    from run_ingestion import ingest_weather_data
    logging.info("ingesting open-meteo weather data to bronze...")
    ingest_weather_data(start_date="2026-08-01", end_date="2026-09-30")


def task_transform_ckan_silver_callable():
    """clean and standardize reservoir bulletins in silver parquet."""
    from run_silver_pipeline import process_ckan_to_silver
    logging.info("transforming ckan excel to silver parquet...")
    process_ckan_to_silver()


def task_transform_weather_silver_callable():
    """clean and standardize weather data in silver parquet."""
    from run_silver_pipeline import process_weather_to_silver
    logging.info("transforming weather json to silver parquet...")
    process_weather_to_silver()


def task_load_silver_to_postgres_callable():
    """stage silver parquet into postgresql staging schema."""
    from run_warehouse_pipeline import run_silver_to_postgres_loader
    logging.info("loading silver parquet into postgresql staging...")
    run_silver_to_postgres_loader()


def task_dbt_run_callable():
    """execute dbt transformations to build star schema."""
    from run_warehouse_pipeline import run_dbt_command
    logging.info("running dbt models...")
    returncode = run_dbt_command("run")
    if returncode != 0:
        raise RuntimeError(f"dbt run failed with returncode {returncode}")


def task_dbt_test_callable():
    """execute dbt data quality assertions."""
    from run_warehouse_pipeline import run_dbt_command
    logging.info("running dbt test suite...")
    returncode = run_dbt_command("test")
    if returncode != 0:
        raise RuntimeError(f"dbt test suite failed with returncode {returncode}")


def task_gold_parquet_backup_callable():
    """build minio gold analytical master parquet."""
    from run_gold_pipeline import process_gold_pipeline
    logging.info("generating gold parquet snapshot in minio...")
    process_gold_pipeline()


# dag definition
if DAG is not None:
    with DAG(
        dag_id="morocco_tensift_water_lakehouse",
        default_args=default_args,
        description="medallion lakehouse and dbt star schema orchestration",
        schedule_interval="0 6 * * *",
        start_date=datetime(2026, 8, 1),
        catchup=False,
        max_active_runs=1,
        tags=["lakehouse", "morocco", "water_reliability", "dbt", "minio", "postgres"],
    ) as dag:

        ingest_ckan_bronze = PythonOperator(
            task_id="ingest_ckan_bronze",
            python_callable=task_ingest_ckan_bronze_callable,
        )

        ingest_weather_bronze = PythonOperator(
            task_id="ingest_weather_bronze",
            python_callable=task_ingest_weather_bronze_callable,
        )

        transform_ckan_silver = PythonOperator(
            task_id="transform_ckan_silver",
            python_callable=task_transform_ckan_silver_callable,
        )

        transform_weather_silver = PythonOperator(
            task_id="transform_weather_silver",
            python_callable=task_transform_weather_silver_callable,
        )

        load_silver_to_postgres = PythonOperator(
            task_id="load_silver_to_postgres_staging",
            python_callable=task_load_silver_to_postgres_callable,
        )

        dbt_run_star_schema = PythonOperator(
            task_id="dbt_run_star_schema",
            python_callable=task_dbt_run_callable,
        )

        dbt_test_assertions = PythonOperator(
            task_id="dbt_test_assertions",
            python_callable=task_dbt_test_callable,
        )

        build_gold_minio_parquet = PythonOperator(
            task_id="build_gold_minio_parquet",
            python_callable=task_gold_parquet_backup_callable,
        )

        # dependencies
        ingest_ckan_bronze >> transform_ckan_silver
        ingest_weather_bronze >> transform_weather_silver
        [transform_ckan_silver, transform_weather_silver] >> load_silver_to_postgres
        load_silver_to_postgres >> dbt_run_star_schema
        dbt_run_star_schema >> [dbt_test_assertions, build_gold_minio_parquet]
