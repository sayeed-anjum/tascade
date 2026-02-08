# P5.M2.T6 Metrics Performance Benchmark

## Scope

This benchmark focuses on the metrics incremental compute path (`RUNNER.run`) for
`batch` mode with 10,000 task-state transition events in one run.

## Repro Command

```bash
python3 scripts/benchmark_metrics_jobs.py --transitions 10000 --iterations 12 --warmups 2
```

## Baseline (before optimization)

- p50: 94.15 ms
- p95: 100.69 ms
- mean: 93.23 ms

## After optimization

- p50: 33.85 ms
- p95: 37.77 ms
- mean: 31.90 ms

## Delta

- p95 improvement: 62.5% faster (100.69 ms -> 37.77 ms)
- p50 improvement: 64.1% faster (94.15 ms -> 33.85 ms)

## Implemented Optimizations

1. Streamlined event fetch query to load only `id` and `payload` columns.
2. Aggregated increments per state in-memory before updating counters.
3. Applied one counter update per state instead of one per event.
4. Added a composite event-log cursor index for PostgreSQL:
   `(project_id, entity_type, event_type, id)`.
