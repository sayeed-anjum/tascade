from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


OUTPUT_PRECISION = 6


def _clamp_ratio(value: float) -> float:
    return max(0.0, min(1.0, value))


def compute_ns1_delivery_predictability_index(
    schedule_reliability: float,
    cycle_time_stability: float,
    blocker_resolution_rate: float,
) -> float:
    weighted = (
        (schedule_reliability * 0.40)
        + (cycle_time_stability * 0.35)
        + (blocker_resolution_rate * 0.25)
    )
    return _clamp_ratio(weighted)


def compute_ns2_flow_efficiency_score(
    active_work_time: float,
    wait_time: float,
    blocked_time: float,
) -> float:
    denominator = active_work_time + wait_time + blocked_time
    if denominator == 0:
        return 0.0
    return _clamp_ratio(active_work_time / denominator)


def compute_ns3_integration_reliability_score(
    success_rate: float,
    recovery_speed_score: float,
) -> float:
    weighted = (success_rate * 0.60) + (recovery_speed_score * 0.40)
    return _clamp_ratio(weighted)


METRIC_COMPUTERS = {
    "NS-1": lambda inputs: compute_ns1_delivery_predictability_index(
        schedule_reliability=float(inputs["schedule_reliability"]),
        cycle_time_stability=float(inputs["cycle_time_stability"]),
        blocker_resolution_rate=float(inputs["blocker_resolution_rate"]),
    ),
    "NS-2": lambda inputs: compute_ns2_flow_efficiency_score(
        active_work_time=float(inputs["active_work_time"]),
        wait_time=float(inputs["wait_time"]),
        blocked_time=float(inputs["blocked_time"]),
    ),
    "NS-3": lambda inputs: compute_ns3_integration_reliability_score(
        success_rate=float(inputs["success_rate"]),
        recovery_speed_score=float(inputs["recovery_speed_score"]),
    ),
}


@dataclass(frozen=True)
class ReconciliationCase:
    case_id: str
    metric: str
    inputs: dict[str, Any]
    expected_output: float


@dataclass(frozen=True)
class ReconciliationResult:
    case_id: str
    metric: str
    inputs: dict[str, Any]
    expected_output: float
    computed_output: float
    delta: float
    is_match: bool


@dataclass(frozen=True)
class ReconciliationReport:
    results: list[ReconciliationResult]
    tolerance: float

    @property
    def total_cases(self) -> int:
        return len(self.results)

    @property
    def mismatch_count(self) -> int:
        return len([result for result in self.results if not result.is_match])

    @property
    def passed(self) -> bool:
        return self.mismatch_count == 0

    def to_dict(self) -> dict[str, Any]:
        mismatches = [
            {
                "case_id": result.case_id,
                "metric": result.metric,
                "expected_output": result.expected_output,
                "computed_output": result.computed_output,
                "delta": result.delta,
            }
            for result in self.results
            if not result.is_match
        ]

        return {
            "status": "pass" if self.passed else "fail",
            "total_cases": self.total_cases,
            "mismatch_count": self.mismatch_count,
            "tolerance": self.tolerance,
            "mismatches": sorted(
                mismatches,
                key=lambda item: (item["metric"], item["case_id"]),
            ),
        }


def load_reconciliation_cases(dataset_path: Path) -> list[ReconciliationCase]:
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    cases = payload["cases"]
    parsed = [
        ReconciliationCase(
            case_id=case["case_id"],
            metric=case["metric"],
            inputs=case["inputs"],
            expected_output=float(case["expected_output"]),
        )
        for case in cases
    ]
    return sorted(parsed, key=lambda case: (case.metric, case.case_id))


def reconcile_cases(
    cases: list[ReconciliationCase],
    tolerance: float = 1e-9,
) -> ReconciliationReport:
    results: list[ReconciliationResult] = []

    for case in sorted(cases, key=lambda item: (item.metric, item.case_id)):
        compute = METRIC_COMPUTERS.get(case.metric)
        if compute is None:
            raise ValueError(f"Unsupported metric for reconciliation: {case.metric}")

        computed_output = round(float(compute(case.inputs)), OUTPUT_PRECISION)
        expected_output = round(case.expected_output, OUTPUT_PRECISION)
        delta = round(computed_output - expected_output, OUTPUT_PRECISION)
        is_match = abs(delta) <= tolerance

        results.append(
            ReconciliationResult(
                case_id=case.case_id,
                metric=case.metric,
                inputs=case.inputs,
                expected_output=expected_output,
                computed_output=computed_output,
                delta=delta,
                is_match=is_match,
            )
        )

    return ReconciliationReport(results=results, tolerance=tolerance)


def run_reconciliation(dataset_path: Path) -> ReconciliationReport:
    return reconcile_cases(load_reconciliation_cases(dataset_path))
