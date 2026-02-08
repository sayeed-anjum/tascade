from pathlib import Path

from app.metrics.reconciliation import (
    ReconciliationCase,
    reconcile_cases,
    run_reconciliation,
)


GOLDEN_DATASET_PATH = (
    Path(__file__).parent / "fixtures" / "metrics" / "golden_critical_metrics.json"
)


def test_reconciliation_passes_for_zero_delta_golden_dataset() -> None:
    report = run_reconciliation(GOLDEN_DATASET_PATH)

    assert report.passed is True
    assert report.total_cases == 3
    assert report.mismatch_count == 0
    assert report.to_dict()["status"] == "pass"


def test_reconciliation_fails_when_expected_output_mismatches() -> None:
    report = run_reconciliation(GOLDEN_DATASET_PATH)
    first_case = report.results[0]
    mutated_case = ReconciliationCase(
        case_id=first_case.case_id,
        metric=first_case.metric,
        inputs=first_case.inputs,
        expected_output=round(first_case.expected_output + 0.01, 6),
    )

    mismatch_report = reconcile_cases([mutated_case])

    assert mismatch_report.passed is False
    assert mismatch_report.total_cases == 1
    assert mismatch_report.mismatch_count == 1
    assert mismatch_report.to_dict()["status"] == "fail"
