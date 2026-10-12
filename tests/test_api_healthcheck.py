import pytest
from unittest.mock import patch, MagicMock
from src.extraction.api_healthcheck import ping_endpoint, run_preflight_healthchecks


@patch("requests.get")
def test_ping_endpoint_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_get.return_value = mock_resp

    res = ping_endpoint("test_service", "https://api.example.com")
    assert res["name"] == "test_service"
    assert res["status_code"] == 200
    assert res["is_healthy"] is True
    assert res["error"] is None


@patch("requests.get")
def test_ping_endpoint_failure(mock_get):
    mock_get.side_effect = Exception("Connection refused")

    res = ping_endpoint("test_service", "https://api.example.com")
    assert res["name"] == "test_service"
    assert res["status_code"] is None
    assert res["is_healthy"] is False
    assert "Connection refused" in res["error"]


@patch("src.extraction.api_healthcheck.ping_endpoint")
def test_run_preflight_healthchecks(mock_ping):
    mock_ping.side_effect = [
        {"name": "ep1", "is_healthy": True, "latency_ms": 45.0},
        {"name": "ep2", "is_healthy": True, "latency_ms": 60.0},
    ]

    summary = run_preflight_healthchecks({"ep1": "url1", "ep2": "url2"})
    assert summary["all_healthy"] is True
    assert len(summary["probes"]) == 2
