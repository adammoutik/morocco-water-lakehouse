import pytest
import pandas as pd
import io
import json
from unittest.mock import patch, MagicMock
from src.storage import minio_handler 


@patch.object(minio_handler, 's3_client')
@patch.object(minio_handler.requests, 'get')
def test_download_resources_success_bronze(mock_get, mock_s3_client):
    fake_df = pd.DataFrame({"Reservoir": ["Tensift"], "Level": [100]})
    excel_buffer = io.BytesIO()
    fake_df.to_excel(excel_buffer, index=False)
    valid_excel_bytes = excel_buffer.getvalue()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = valid_excel_bytes 
    mock_get.return_value = mock_response

    fake_datasets = [{
        "title": "Dataset de Test",
        "resources": [{
            "name": "fichier_test", 
            "format": "XLSX", 
            "url": "http://fake-url.ma/data.xlsx"
        }]
    }]

    minio_handler.download_resources(fake_datasets)

    # Verify it went to Bronze with extension added once
    mock_s3_client.upload_fileobj.assert_called_once()
    args, kwargs = mock_s3_client.upload_fileobj.call_args
    
    assert args[1] == minio_handler.BRONZE_BUCKET
    assert args[2] == "raw/tensift_reservoirs/fichier_test.xlsx"


@patch.object(minio_handler, 's3_client')
@patch.object(minio_handler.requests, 'get')
def test_download_resources_no_double_extension(mock_get, mock_s3_client):
    """verify filename extensions are not duplicated."""
    fake_df = pd.DataFrame({"Reservoir": ["Tensift"], "Level": [100]})
    excel_buffer = io.BytesIO()
    fake_df.to_excel(excel_buffer, index=False)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = excel_buffer.getvalue()
    mock_get.return_value = mock_response

    fake_datasets = [{
        "title": "Dataset with Extension",
        "resources": [{
            "name": "data_barrages_tensift_aout_2026.xlsx", 
            "format": "XLSX", 
            "url": "http://fake-url.ma/data.xlsx"
        }]
    }]

    minio_handler.download_resources(fake_datasets)

    args, _ = mock_s3_client.upload_fileobj.call_args
    assert args[2] == "raw/tensift_reservoirs/data_barrages_tensift_aout_2026.xlsx"
    assert not args[2].endswith(".xlsx.xlsx")


@patch.object(minio_handler, 's3_client')
def test_init_bucket_initializes_all_medallion_buckets(mock_s3_client):
    """verify init_bucket creates all medallion buckets."""
    mock_s3_client.head_bucket.side_effect = Exception("Bucket does not exist")
    minio_handler.init_bucket()

    created_buckets = [call[1]['Bucket'] for call in mock_s3_client.create_bucket.call_args_list]
    for expected in minio_handler.ALL_BUCKETS:
        assert expected in created_buckets


def test_validate_weather_schema():
    """verify weather payload schema validation contract."""
    valid_payload = {
        "latitude": 31.62,
        "longitude": -8.01,
        "daily": {
            "time": ["2026-08-01", "2026-08-02"],
            "temperature_2m_max": [35.0, 36.2],
            "temperature_2m_min": [20.1, 21.0],
            "precipitation_sum": [0.0, 5.2]
        }
    }
    is_valid, reason = minio_handler.validate_weather_schema(valid_payload)
    assert is_valid
    assert reason == ""

    # Test error response
    err_payload = {"error": True, "reason": "Rate limit exceeded"}
    is_valid, reason = minio_handler.validate_weather_schema(err_payload)
    assert not is_valid
    assert "api_error" in reason

    # Test missing daily key
    missing_daily = {"latitude": 31.0, "longitude": -8.0}
    is_valid, reason = minio_handler.validate_weather_schema(missing_daily)
    assert not is_valid
    assert "missing_or_empty_daily_key" in reason

    # Test length mismatch between metrics and time
    mismatched = {
        "latitude": 31.0,
        "longitude": -8.0,
        "daily": {
            "time": ["2026-08-01", "2026-08-02"],
            "temperature_2m_max": [35.0],  # only 1 item while time has 2!
            "temperature_2m_min": [20.0, 21.0],
            "precipitation_sum": [0.0, 0.0]
        }
    }
    is_valid, reason = minio_handler.validate_weather_schema(mismatched)
    assert not is_valid
    assert "length_mismatch" in reason


@patch.object(minio_handler, 's3_client')
def test_ingest_weather_to_bronze_success(mock_s3_client):
    """
    Verifies valid weather payload is routed to Bronze bucket.
    """
    valid_payload = {
        "latitude": 31.62,
        "longitude": -8.01,
        "daily": {
            "time": ["2026-08-01"],
            "temperature_2m_max": [35.0],
            "temperature_2m_min": [20.0],
            "precipitation_sum": [0.0]
        }
    }
    ok, final_key, reason = minio_handler.ingest_weather_to_bronze_or_quarantine(
        valid_payload, "raw/open_meteo/test_site.json"
    )
    assert ok
    assert final_key == "raw/open_meteo/test_site.json"
    assert reason is None

    mock_s3_client.upload_fileobj.assert_called_once()
    args, kwargs = mock_s3_client.upload_fileobj.call_args
    assert args[1] == minio_handler.BRONZE_BUCKET


@patch.object(minio_handler, 's3_client')
def test_ingest_weather_to_quarantine_on_invalid_schema(mock_s3_client):
    """
    Verifies corrupt or incomplete weather payload is routed to Quarantine bucket.
    """
    corrupt_payload = {
        "latitude": 31.62,
        # missing longitude and daily metrics!
    }
    ok, final_key, reason = minio_handler.ingest_weather_to_bronze_or_quarantine(
        corrupt_payload, "raw/open_meteo/bad_site.json"
    )
    assert not ok
    assert "quarantine/" in final_key
    assert reason == "missing_coordinates"

    mock_s3_client.upload_fileobj.assert_called_once()
    args, kwargs = mock_s3_client.upload_fileobj.call_args
    assert args[1] == minio_handler.QUARANTINE_BUCKET
    metadata = kwargs.get("ExtraArgs", {}).get("Metadata", {})
    assert metadata.get("quarantine_reason") == "missing_coordinates"