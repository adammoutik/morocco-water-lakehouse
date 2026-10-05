import pytest
import pandas as pd
import io
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

    # Verify it went to Bronze
    mock_s3_client.upload_fileobj.assert_called_once()
    args, kwargs = mock_s3_client.upload_fileobj.call_args
    
    assert args[1] == "morocco-water-bronze"  # It passed validation!
    assert "raw/tensift_reservoirs/fichier_test.xlsx" in args[2]