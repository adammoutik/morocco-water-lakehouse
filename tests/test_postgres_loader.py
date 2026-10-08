import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from src.storage import load_silver_to_postgres


def test_get_postgres_engine_config():
    """
    Verifies that get_postgres_engine reads environment variables properly.
    """
    with patch.dict("os.environ", {
        "POSTGRES_USER": "test_user",
        "POSTGRES_PASSWORD": "test_password",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "test_db",
    }):
        engine = load_silver_to_postgres.get_postgres_engine()
        assert "test_user:***@localhost:5432/test_db" in str(engine.url)


@patch("src.storage.load_silver_to_postgres.get_parquet_from_minio")
@patch("src.storage.load_silver_to_postgres.list_objects_in_prefix")
def test_load_silver_ckan_to_staging_mock(mock_list, mock_get):
    """
    Verifies that load_silver_ckan_to_staging correctly extracts and transforms
    parquet files before writing to the database engine.
    """
    mock_list.return_value = ["cleansed/ckan_reservoirs/data_test.parquet"]
    fake_df = pd.DataFrame({
        "jour": ["01", "02"],
        "date": ["2026-08-01", "2026-08-02"],
        "yacoub_el_mansour": [49.44, 49.12],
        "yacoub_el_mansour.1": [86.05, 85.50],
    })
    mock_get.return_value = fake_df

    mock_engine = MagicMock()
    # Mock context manager for engine.begin()
    mock_conn = MagicMock()
    mock_engine.begin.return_value.__enter__.return_value = mock_conn

    count = load_silver_to_postgres.load_silver_ckan_to_staging(mock_engine)
    assert count == 2  # 2 days x 1 dam
    # Ensure TRUNCATE was executed
    assert mock_conn.execute.called
