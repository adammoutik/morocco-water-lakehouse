import time
import logging
import requests
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

DEFAULT_ENDPOINTS = {
    "open_meteo": "https://archive-api.open-meteo.com/v1/archive?latitude=31.63&longitude=-8.00&start_date=2026-01-01&end_date=2026-01-02&daily=precipitation_sum",
    "ckan_portal": "https://data.gov.ma/data/api/3/action/package_list",
}


def ping_endpoint(name: str, url: str, timeout_seconds: float = 5.0) -> Dict[str, Any]:
    """
    check responsiveness and measure latency for an external api endpoint.
    """
    start_time = time.time()
    try:
        response = requests.get(url, timeout=timeout_seconds, headers={"User-Agent": "MoroccoWaterLakehouse/1.0"})
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        is_healthy = response.status_code < 500

        return {
            "name": name,
            "url": url,
            "status_code": response.status_code,
            "latency_ms": elapsed_ms,
            "is_healthy": is_healthy,
            "error": None if is_healthy else f"HTTP {response.status_code}",
        }
    except requests.exceptions.Timeout:
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "name": name,
            "url": url,
            "status_code": None,
            "latency_ms": elapsed_ms,
            "is_healthy": False,
            "error": "Request timed out",
        }
    except Exception as exc:
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "name": name,
            "url": url,
            "status_code": None,
            "latency_ms": elapsed_ms,
            "is_healthy": False,
            "error": str(exc),
        }


def run_preflight_healthchecks(endpoints: Dict[str, str] = None, timeout_seconds: float = 5.0) -> Dict[str, Any]:
    """
    execute pre-flight reachability checks across all upstream ingestion apis.
    returns aggregate status and individual target diagnostics.
    """
    targets = endpoints or DEFAULT_ENDPOINTS
    results: List[Dict[str, Any]] = []

    for name, url in targets.items():
        res = ping_endpoint(name, url, timeout_seconds=timeout_seconds)
        results.append(res)
        status_label = "HEALTHY" if res["is_healthy"] else "DEGRADED/OFFLINE"
        logging.info("API Probe [%s]: %s (%s ms)", name, status_label, res["latency_ms"])

    all_healthy = all(r["is_healthy"] for r in results)
    return {
        "all_healthy": all_healthy,
        "checked_at": time.time(),
        "probes": results,
    }
