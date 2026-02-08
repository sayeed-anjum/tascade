#!/usr/bin/env python3
"""End-to-end smoke test for Tascade metrics endpoints.

Verifies all metrics API endpoints respond correctly and return
well-formed responses that match the expected contract.

Usage:
    python scripts/smoke_test_metrics.py --base-url http://localhost:8000 --project-id <uuid>
"""
from __future__ import annotations

import argparse
import sys
from typing import Any

import requests


# ---------------------------------------------------------------------------
# Expected response structure validators
# ---------------------------------------------------------------------------

def _has_keys(data: dict[str, Any], keys: set[str], label: str) -> list[str]:
    """Return a list of error messages for missing keys."""
    missing = keys - set(data.keys())
    if missing:
        return [f"{label}: missing keys {sorted(missing)}"]
    return []


def validate_summary(body: dict[str, Any]) -> list[str]:
    """Validate /v1/metrics/summary response structure."""
    return _has_keys(body, {"version", "project_id", "timestamp", "metrics"}, "summary")


def validate_trends(body: dict[str, Any]) -> list[str]:
    """Validate /v1/metrics/trends response structure."""
    errors = _has_keys(
        body,
        {"version", "project_id", "metric", "granularity", "start_date", "end_date", "data"},
        "trends",
    )
    if "data" in body and not isinstance(body["data"], list):
        errors.append("trends: 'data' should be a list")
    return errors


def validate_breakdown(body: dict[str, Any]) -> list[str]:
    """Validate /v1/metrics/breakdown response structure."""
    errors = _has_keys(
        body,
        {"version", "project_id", "metric", "dimension", "time_range", "total", "breakdown"},
        "breakdown",
    )
    if "breakdown" in body and not isinstance(body["breakdown"], list):
        errors.append("breakdown: 'breakdown' should be a list")
    return errors


def validate_drilldown(body: dict[str, Any]) -> list[str]:
    """Validate /v1/metrics/drilldown response structure."""
    errors = _has_keys(
        body,
        {"version", "project_id", "metric", "filters_applied", "items", "pagination", "aggregation"},
        "drilldown",
    )
    if "items" in body and not isinstance(body["items"], list):
        errors.append("drilldown: 'items' should be a list")
    return errors


def validate_alerts(body: dict[str, Any]) -> list[str]:
    """Validate /v1/metrics/alerts response structure."""
    errors = _has_keys(body, {"items"}, "alerts")
    if "items" in body and not isinstance(body["items"], list):
        errors.append("alerts: 'items' should be a list")
    return errors


def validate_actions(body: dict[str, Any]) -> list[str]:
    """Validate /v1/metrics/actions response structure."""
    errors = _has_keys(body, {"version", "project_id", "suggestions"}, "actions")
    if "suggestions" in body and not isinstance(body["suggestions"], list):
        errors.append("actions: 'suggestions' should be a list")
    return errors


def validate_health(body: dict[str, Any]) -> list[str]:
    """Validate /v1/metrics/health response structure."""
    # Minimal validation -- just check it returned a dict.
    if not isinstance(body, dict):
        return ["health: expected a JSON object"]
    return []


# ---------------------------------------------------------------------------
# Endpoint test definitions
# ---------------------------------------------------------------------------

ENDPOINT_TESTS: list[dict[str, Any]] = [
    {
        "name": "GET /v1/metrics/summary",
        "method": "GET",
        "path": "/v1/metrics/summary",
        "params_fn": lambda pid: {"project_id": pid},
        "validator": validate_summary,
    },
    {
        "name": "GET /v1/metrics/trends",
        "method": "GET",
        "path": "/v1/metrics/trends",
        "params_fn": lambda pid: {
            "project_id": pid,
            "metric": "cycle_time",
            "start_date": "2026-01-01",
            "end_date": "2026-02-08",
            "granularity": "day",
        },
        "validator": validate_trends,
    },
    {
        "name": "GET /v1/metrics/breakdown",
        "method": "GET",
        "path": "/v1/metrics/breakdown",
        "params_fn": lambda pid: {
            "project_id": pid,
            "metric": "cycle_time",
            "dimension": "phase",
        },
        "validator": validate_breakdown,
    },
    {
        "name": "GET /v1/metrics/drilldown",
        "method": "GET",
        "path": "/v1/metrics/drilldown",
        "params_fn": lambda pid: {
            "project_id": pid,
            "metric": "cycle_time",
        },
        "validator": validate_drilldown,
    },
    {
        "name": "GET /v1/metrics/health",
        "method": "GET",
        "path": "/v1/metrics/health",
        "params_fn": lambda pid: {"project_id": pid},
        "validator": validate_health,
    },
    {
        "name": "GET /v1/metrics/alerts",
        "method": "GET",
        "path": "/v1/metrics/alerts",
        "params_fn": lambda pid: {"project_id": pid},
        "validator": validate_alerts,
    },
    {
        "name": "GET /v1/metrics/actions",
        "method": "GET",
        "path": "/v1/metrics/actions",
        "params_fn": lambda pid: {"project_id": pid},
        "validator": validate_actions,
    },
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_smoke_tests(base_url: str, project_id: str) -> bool:
    """Execute all smoke tests and return True if all passed."""
    base_url = base_url.rstrip("/")
    passed = 0
    failed = 0
    results: list[tuple[str, bool, str]] = []

    for test in ENDPOINT_TESTS:
        name = test["name"]
        url = f"{base_url}{test['path']}"
        params = test["params_fn"](project_id)
        validator = test["validator"]

        try:
            resp = requests.get(url, params=params, timeout=30)
        except requests.RequestException as exc:
            results.append((name, False, f"Connection error: {exc}"))
            failed += 1
            continue

        errors: list[str] = []

        # Check HTTP status
        if resp.status_code != 200:
            errors.append(f"HTTP {resp.status_code} (expected 200)")

        # Check X-API-Version header
        api_version = resp.headers.get("X-API-Version")
        if api_version != "1.0":
            errors.append(
                f"X-API-Version header: got {api_version!r} (expected '1.0')"
            )

        # Validate response body structure (only if 200)
        if resp.status_code == 200:
            try:
                body = resp.json()
            except ValueError:
                errors.append("Response is not valid JSON")
                body = None

            if body is not None:
                structure_errors = validator(body)
                errors.extend(structure_errors)

        if errors:
            results.append((name, False, "; ".join(errors)))
            failed += 1
        else:
            results.append((name, True, "OK"))
            passed += 1

    # Print summary
    print()
    print("=" * 60)
    print("METRICS SMOKE TEST RESULTS")
    print("=" * 60)
    print(f"Base URL   : {base_url}")
    print(f"Project ID : {project_id}")
    print("-" * 60)

    for name, success, detail in results:
        status = "PASS" if success else "FAIL"
        print(f"  [{status}] {name}")
        if not success:
            print(f"         {detail}")

    print("-" * 60)
    print(f"Total: {passed + failed} | Passed: {passed} | Failed: {failed}")
    print("=" * 60)

    return failed == 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Smoke test for Tascade metrics endpoints",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the Tascade API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--project-id",
        required=True,
        help="Project ID to use for metrics queries",
    )
    args = parser.parse_args()

    all_passed = run_smoke_tests(args.base_url, args.project_id)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
