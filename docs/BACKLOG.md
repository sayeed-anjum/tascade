# Tascade Backlog (Current)

This backlog captures outstanding work identified by reconciling current code against PRD/SRS requirements.

## Must-Have

1. Add REST task context endpoint
- Gap: MCP exposes task context but REST does not.
- Requirement lineage: SRS API requirements (`GET /v1/tasks/{id}/context`).
- Current evidence:
  - context logic exists in `app/store.py`
  - MCP tool exists in `app/mcp_tools.py`
  - missing route in `app/main.py`
- Acceptance criteria:
  - Add `GET /v1/tasks/{task_id}/context` REST endpoint with auth and project-scope enforcement.
  - Support `ancestor_depth` and `dependent_depth` query parameters.
  - Add API + MCP parity tests.

2. Add execution snapshot retrieval endpoint
- Gap: snapshots are captured on claim but no REST retrieval endpoint exists.
- Requirement lineage: SRS API requirements (`GET /v1/tasks/{id}/execution-snapshots`).
- Current evidence:
  - snapshot capture exists in claim flow.
  - no retrieval route in `app/main.py`.
- Acceptance criteria:
  - Add `GET /v1/tasks/{task_id}/execution-snapshots`.
  - Return snapshots in deterministic order with project-scope auth checks.
  - Add endpoint tests.

3. Decide and implement canonical context default depths
- Gap: SRS calls for default `ancestor_depth=2`, `dependent_depth=1`; current defaults are effectively `1/1`.
- Current evidence:
  - `app/store.py`
  - `app/mcp_tools.py`
- Acceptance criteria:
  - Choose canonical defaults (`2/1` or updated spec), apply consistently across REST + MCP + docs.
  - Add regression tests for omitted-parameter defaults.

4. Add task changelog model and endpoints (or formally de-scope)
- Gap: append-only changelog is specified in design docs but not implemented.
- Requirement lineage: PRD `FR-27`, SRS changelog endpoints.
- Acceptance criteria (if implemented):
  - Introduce append-only changelog persistence model.
  - Add `POST /v1/tasks/{task_id}/changelog` and `GET /v1/tasks/{task_id}/changelog`.
  - Enforce append-only behavior and audit attribution.
  - Add tests.
- Acceptance criteria (if de-scoped):
  - Update current PRD/SRS to explicitly remove changelog endpoint commitment.
  - Add rationale and replacement approach (event log only).

## Optional / Legacy Compatibility

1. Add `unassign` endpoint
- Gap: SRS listed `POST /v1/tasks/{id}/unassign`.
- Current behavior: reservations can expire or be consumed; no direct unassign API.
- Acceptance criteria:
  - Either add explicit unassign operation + tests, or de-scope in current docs.

2. Add plan helper endpoints (`validate`, `current`)
- Gap: SRS listed:
  - `POST /v1/plans/changesets/{id}/validate`
  - `GET /v1/plans/current`
- Current behavior: create/apply exists; validate/current are absent.
- Acceptance criteria:
  - Implement these endpoints or document that preview is embedded in create/apply flow.

3. Add/decline legacy alias endpoints
- Gap: SRS used alias forms:
  - `/v1/integration/enqueue`
  - `/v1/gates/{id}/decision`
  - `/v1/views/graph`
  - `/v1/views/list`
- Current behavior: equivalent capabilities exist under different canonical paths.
- Acceptance criteria:
  - Decide whether to support aliases for compatibility.
  - If not, document canonical replacements in API docs.

4. Idempotency and outbox hardening at platform level
- Gap: SRS expects general mutating-request idempotency + outbox replay semantics.
- Current evidence:
  - no platform-wide idempotency-key handling.
  - no generic outbox publisher/replay subsystem.
  - metrics job idempotency exists but is scoped to metrics jobs only.
- Acceptance criteria:
  - Decide scope for v1.1:
    - full platform idempotency/outbox, or
    - explicit non-goal with narrow guarantees.
  - reflect decision in current PRD/SRS and runbook.

## Prioritization Recommendation

1. REST context endpoint parity.
2. Execution snapshot retrieval endpoint.
3. Context default-depth decision and alignment.
4. Changelog decision (implement vs de-scope).
5. Legacy alias and helper endpoint decisions.
6. Platform idempotency/outbox roadmap decision.
