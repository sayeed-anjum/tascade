from __future__ import annotations

import argparse
import os
import statistics
import sys
import time
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("TASCADE_DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.metrics_jobs import RUNNER
from app.models import MetricsJobMode
from app.store import STORE


def _seed_events(project_id: str, transitions: int) -> None:
    phase = STORE.create_phase(project_id=project_id, name="phase", sequence=0)
    milestone = STORE.create_milestone(
        project_id=project_id,
        name="milestone",
        sequence=0,
        phase_id=phase["id"],
    )
    task = STORE.create_task(
        {
            "project_id": project_id,
            "title": "bench-task",
            "task_class": "backend",
            "work_spec": {"objective": "bench", "acceptance_criteria": ["done"]},
            "phase_id": phase["id"],
            "milestone_id": milestone["id"],
        }
    )
    task_id = task["id"]

    STORE.transition_task_state(
        task_id=task_id,
        project_id=project_id,
        new_state="ready",
        actor_id="bench-agent",
        reason="benchmark-ready",
    )

    sequence = ["in_progress", "blocked"]
    for i in range(transitions):
        STORE.transition_task_state(
            task_id=task_id,
            project_id=project_id,
            new_state=sequence[i % len(sequence)],
            actor_id="bench-agent",
            reason=f"benchmark-{i}",
        )


def _measure_once(transitions: int) -> float:
    STORE.reset()
    project_id = STORE.create_project("metrics-benchmark")["id"]
    _seed_events(project_id=project_id, transitions=transitions)

    start = time.perf_counter()
    RUNNER.run(
        project_id=project_id,
        mode=MetricsJobMode.BATCH,
        idempotency_key=f"bench-{transitions}",
    )
    elapsed = time.perf_counter() - start
    return elapsed * 1000.0


def _percentile(samples: Sequence[float], p: float) -> float:
    if not samples:
        return 0.0
    if len(samples) == 1:
        return samples[0]
    rank = (len(samples) - 1) * p
    lo = int(rank)
    hi = min(lo + 1, len(samples) - 1)
    frac = rank - lo
    return samples[lo] * (1.0 - frac) + samples[hi] * frac


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark metrics incremental job run"
    )
    parser.add_argument("--transitions", type=int, default=10000)
    parser.add_argument("--iterations", type=int, default=12)
    parser.add_argument("--warmups", type=int, default=2)
    args = parser.parse_args()

    for _ in range(args.warmups):
        _measure_once(args.transitions)

    samples = sorted(_measure_once(args.transitions) for _ in range(args.iterations))
    p50 = _percentile(samples, 0.5)
    p95 = _percentile(samples, 0.95)
    mean = statistics.fmean(samples)

    print("metrics_jobs benchmark")
    print(f"transitions={args.transitions} iterations={args.iterations}")
    print(f"p50_ms={p50:.2f}")
    print(f"p95_ms={p95:.2f}")
    print(f"mean_ms={mean:.2f}")


if __name__ == "__main__":
    main()
