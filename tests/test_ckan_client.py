import pytest
from unittest.mock import patch
from src.extraction import extract_ck

# test the extract_ckan_data function
@patch.object(extract_ck.requests, 'get')
def test_extract_ckan_data_success(mock_get):
    # mock the response from requests.get
    mock_response = mock_get.return_value
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "success": True,
        "result": {
            "results": [
                {"title": "Tensift Reservoir Data 1", "resources": [{"name": "data.xlsx"}]},
                {"title": "Tensift Reservoir Data 2", "resources": [{"name": "data2.xlsx"}]}
            ]
        }
    }
    
    query = "tensift"
    rows = 2
    # call the function from the imported module
    result = extract_ck.extract_ckan_data(query, rows)

    assert len(result) == 2
    assert result[0]["title"] == "Tensift Reservoir Data 1"
    assert result[1]["title"] == "Tensift Reservoir Data 2"