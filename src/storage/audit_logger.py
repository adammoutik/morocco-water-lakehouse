import os
import time
import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class PipelineAuditLogger:
    """
    tracks execution telemetry and data processing metrics across pipeline layers.
    records row counts, durations, status codes, and failure diagnostics.
    """

    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id or f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        self.records: List[Dict[str, Any]] = []

    def start_step(self, step_name: str, layer: str) -> Dict[str, Any]:
        """initialize timing for a pipeline execution step."""
        return {
            "run_id": self.run_id,
            "step_name": step_name,
            "layer": layer,
            "start_time": time.time(),
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

    def record_step(
        self,
        step_context: Dict[str, Any],
        status: str = "SUCCESS",
        row_count: int = 0,
        bytes_processed: int = 0,
        error_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """finalize and append an execution step record."""
        elapsed = round(time.time() - step_context.get("start_time", time.time()), 3)
        record = {
            "run_id": self.run_id,
            "step_name": step_context.get("step_name", "unknown"),
            "layer": step_context.get("layer", "general"),
            "status": status,
            "row_count": row_count,
            "bytes_processed": bytes_processed,
            "duration_seconds": elapsed,
            "started_at": step_context.get("started_at"),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "error_message": error_message,
            "details": details or {},
        }
        self.records.append(record)
        log_lvl = logging.INFO if status == "SUCCESS" else logging.ERROR
        logging.log(log_lvl, "Audit Step [%s.%s]: %s (%s rows, %ss)",
                    record["layer"], record["step_name"], status, row_count, elapsed)
        return record

    def get_summary(self) -> Dict[str, Any]:
        """summarize total steps, execution duration, and pass/fail counts."""
        total_steps = len(self.records)
        successes = sum(1 for r in self.records if r["status"] == "SUCCESS")
        failures = sum(1 for r in self.records if r["status"] != "SUCCESS")
        total_duration = round(sum(r["duration_seconds"] for r in self.records), 3)
        total_rows = sum(r["row_count"] for r in self.records)

        return {
            "run_id": self.run_id,
            "total_steps": total_steps,
            "successful_steps": successes,
            "failed_steps": failures,
            "total_duration_seconds": total_duration,
            "total_rows_processed": total_rows,
            "overall_status": "SUCCESS" if failures == 0 and total_steps > 0 else ("FAILED" if failures > 0 else "EMPTY"),
        }

    def to_json(self) -> str:
        """serialize telemetry records to a formatted json string."""
        return json.dumps({
            "summary": self.get_summary(),
            "records": self.records,
        }, indent=2)
