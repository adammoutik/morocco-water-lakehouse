import pytest
import time
from src.storage.audit_logger import PipelineAuditLogger


def test_audit_logger_step_recording():
    logger = PipelineAuditLogger(run_id="test_run_123")
    ctx = logger.start_step(step_name="test_step", layer="silver")
    time.sleep(0.01)
    record = logger.record_step(ctx, status="SUCCESS", row_count=100)

    assert record["run_id"] == "test_run_123"
    assert record["step_name"] == "test_step"
    assert record["layer"] == "silver"
    assert record["status"] == "SUCCESS"
    assert record["row_count"] == 100
    assert record["duration_seconds"] > 0


def test_audit_logger_summary_calculation():
    logger = PipelineAuditLogger(run_id="test_run_456")
    ctx1 = logger.start_step("step1", "bronze")
    logger.record_step(ctx1, "SUCCESS", row_count=50)

    ctx2 = logger.start_step("step2", "silver")
    logger.record_step(ctx2, "FAILED", row_count=0, error_message="mock error")

    summary = logger.get_summary()
    assert summary["total_steps"] == 2
    assert summary["successful_steps"] == 1
    assert summary["failed_steps"] == 1
    assert summary["total_rows_processed"] == 50
    assert summary["overall_status"] == "FAILED"

    json_str = logger.to_json()
    assert "test_run_456" in json_str
    assert "mock error" in json_str
