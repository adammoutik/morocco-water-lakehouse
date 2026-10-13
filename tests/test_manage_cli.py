import pytest
from unittest.mock import patch, MagicMock
from manage import build_parser, cmd_healthcheck, cmd_audit


def test_build_parser_arguments():
    parser = build_parser()

    # test healthcheck subcommand
    args_h = parser.parse_args(["healthcheck"])
    assert args_h.command == "healthcheck"

    # test run subcommand default
    args_r1 = parser.parse_args(["run"])
    assert args_r1.command == "run"
    assert args_r1.layer == "all"

    # test run subcommand specific layer
    args_r2 = parser.parse_args(["run", "--layer", "silver"])
    assert args_r2.layer == "silver"


@patch("src.extraction.api_healthcheck.run_preflight_healthchecks")
def test_cmd_healthcheck(mock_checks):
    mock_checks.return_value = {
        "all_healthy": True,
        "probes": [{"name": "test_api", "is_healthy": True, "latency_ms": 10.0, "url": "https://example.com"}],
    }
    parser = build_parser()
    args = parser.parse_args(["healthcheck"])
    code = cmd_healthcheck(args)
    assert code == 0


def test_cmd_audit():
    parser = build_parser()
    args = parser.parse_args(["audit"])
    code = cmd_audit(args)
    assert code == 0
