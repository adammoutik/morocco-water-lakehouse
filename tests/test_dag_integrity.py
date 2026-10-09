"""dag integrity and structure tests."""

import ast
import os
import sys
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DAG_PATH = os.path.join(PROJECT_ROOT, "dags", "morocco_water_lakehouse_dag.py")


def test_dag_file_exists():
    """Verify that the DAG file exists in the standard dags/ directory."""
    assert os.path.exists(DAG_PATH), f"DAG file not found at {DAG_PATH}"


def test_dag_syntax_validity():
    """Verify that the DAG file parses with standard Python AST without syntax errors."""
    with open(DAG_PATH, "r", encoding="utf-8") as f:
        source = f.read()
    parsed = ast.parse(source, filename=DAG_PATH)
    assert isinstance(parsed, ast.Module), "Failed to parse DAG file as a valid Python module"


def test_dag_callables_importable():
    """
    Verify that all task callable functions are importable from the DAG module
    and are callable Python functions.
    """
    import dags.morocco_water_lakehouse_dag as dag_mod

    expected_callables = [
        "task_ingest_ckan_bronze_callable",
        "task_ingest_weather_bronze_callable",
        "task_transform_ckan_silver_callable",
        "task_transform_weather_silver_callable",
        "task_load_silver_to_postgres_callable",
        "task_dbt_run_callable",
        "task_dbt_test_callable",
        "task_gold_parquet_backup_callable",
    ]

    for callable_name in expected_callables:
        assert hasattr(dag_mod, callable_name), f"Missing task callable: {callable_name}"
        fn = getattr(dag_mod, callable_name)
        assert callable(fn), f"{callable_name} is not callable"


def test_dag_task_definitions_in_ast():
    """
    Validates task definitions directly from the AST:
    Confirms all 8 tasks are defined and the DAG id is 'morocco_tensift_water_lakehouse'.
    """
    with open(DAG_PATH, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())

    task_ids = []
    dag_ids = []

    for node in ast.walk(tree):
        # Find PythonOperator task_id
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg == "task_id" and isinstance(kw.value, ast.Constant):
                    task_ids.append(kw.value.value)
                elif kw.arg == "dag_id" and isinstance(kw.value, ast.Constant):
                    dag_ids.append(kw.value.value)

    assert "morocco_tensift_water_lakehouse" in dag_ids, "Expected DAG id not found"

    expected_tasks = {
        "ingest_ckan_bronze",
        "ingest_weather_bronze",
        "transform_ckan_silver",
        "transform_weather_silver",
        "load_silver_to_postgres_staging",
        "dbt_run_star_schema",
        "dbt_test_assertions",
        "build_gold_minio_parquet",
    }

    assert expected_tasks.issubset(set(task_ids)), (
        f"Missing tasks in DAG: {expected_tasks - set(task_ids)}"
    )
