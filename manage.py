#!/usr/bin/env python3
"""
unified lakehouse management cli interface.
usage:
    python manage.py healthcheck
    python manage.py run --layer [bronze|silver|warehouse|gold|all]
    python manage.py audit
    python manage.py test
"""

import sys
import argparse
import logging
import subprocess

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def cmd_healthcheck(args) -> int:
    """run preflight api healthchecks."""
    from src.extraction.api_healthcheck import run_preflight_healthchecks
    logging.info("running preflight api reachability checks...")
    res = run_preflight_healthchecks()
    for probe in res["probes"]:
        status = "OK" if probe["is_healthy"] else "FAIL"
        print(f"[{status}] {probe['name']}: {probe['latency_ms']}ms (URL: {probe['url'][:50]}...)")
    return 0 if res["all_healthy"] else 1


def cmd_run(args) -> int:
    """execute lakehouse pipeline layers."""
    layer = args.layer.lower()
    logging.info("triggering lakehouse execution for layer: %s", layer)

    if layer in ["bronze", "all"]:
        from run_ingestion import ingest_ckan_data, ingest_weather_data
        logging.info("running bronze ingestion...")
        ingest_ckan_data(query="tensift", rows=10)
        ingest_weather_data(start_date="2026-08-01", end_date="2026-09-30")

    if layer in ["silver", "all"]:
        from run_silver_pipeline import process_ckan_to_silver, process_weather_to_silver
        logging.info("running silver transformations...")
        process_ckan_to_silver()
        process_weather_to_silver()

    if layer in ["warehouse", "all"]:
        from run_warehouse_pipeline import run_silver_to_postgres_loader, run_dbt_command
        logging.info("running warehouse staging loader and dbt models...")
        run_silver_to_postgres_loader()
        run_dbt_command("run")
        run_dbt_command("test")

    if layer in ["gold", "all"]:
        from run_gold_pipeline import process_gold_pipeline
        logging.info("running gold parquet generation...")
        process_gold_pipeline()

    logging.info("layer execution finished successfully.")
    return 0


def cmd_audit(args) -> int:
    """display pipeline audit summary."""
    from src.storage.audit_logger import PipelineAuditLogger
    logger = PipelineAuditLogger()
    print("\n--- Pipeline Audit Summary ---")
    print(logger.to_json())
    return 0


def cmd_test(args) -> int:
    """run pytest test suite."""
    logging.info("running pytest test suite...")
    cmd = [sys.executable, "-m", "pytest", "-v"]
    return subprocess.call(cmd)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="manage.py",
        description="Morocco Tensift Water Lakehouse Management CLI"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # healthcheck
    p_health = subparsers.add_parser("healthcheck", help="check external api endpoints")
    p_health.set_defaults(func=cmd_healthcheck)

    # run
    p_run = subparsers.add_parser("run", help="run pipeline layers")
    p_run.add_argument(
        "--layer",
        choices=["bronze", "silver", "warehouse", "gold", "all"],
        default="all",
        help="pipeline layer to execute (default: all)"
    )
    p_run.set_defaults(func=cmd_run)

    # audit
    p_audit = subparsers.add_parser("audit", help="display execution audit telemetry")
    p_audit.set_defaults(func=cmd_audit)

    # test
    p_test = subparsers.add_parser("test", help="run automated test suite")
    p_test.set_defaults(func=cmd_test)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    returncode = args.func(args)
    sys.exit(returncode)


if __name__ == "__main__":
    main()
