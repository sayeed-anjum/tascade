# Inspection Report: P3.M3.T3 API Key Auth and Role Scopes

> Historical dated document.
> Treat findings and status in this file as point-in-time and verify against current code/tests before acting.

- Date: 2026-02-08
- Inspected task: `P3.M3.T3` (`dea90bdc-8c35-4743-999e-68ba6da8527a`)
- Inspected branch/commit: `p3-m3-t3-api-key-auth` @ `5f4363a`
- Inspector task: `P3.M3.T11` (`cf09fd33-6afc-484f-8ad8-49edd2ddbe21`)

## Scope Checked

- Authentication dependency and role guard implementation (`app/auth.py`)
- Endpoint wiring and enforcement across `/v1/*` routes (`app/main.py`)
- API key persistence and lifecycle (`app/models.py`, `app/store.py`, `docs/db/migrations/0005_api_key.sql`)
- Key management API schema/handlers (`app/schemas.py`, `app/main.py`)
- Bootstrap script (`scripts/create_api_key.py`)
- Auth test coverage (`tests/test_auth.py`)
- Requirement/design alignment (`docs/prd/2026-02-06-agentic-task-orchestration-prd-v0.1.md`, `docs/srs/2026-02-06-agentic-task-orchestration-srs-v0.1.md`, `docs/plans/2026-02-06-agentic-task-orchestration-design.md`)

## Verification Run

- `pytest -q tests/test_auth.py` -> `13 passed`
- `pytest -q` -> `99 passed`

## Findings (ordered by severity)

### 1) High: Cross-project `apply_plan_changeset` is currently allowed

- Requirement impact:
  - Violates project-scoped isolation intent (PRD `FR-17`), and SRS security constraints requiring project-scoped keys to prevent cross-project access.
- Evidence:
  - `app/main.py:823` calls `require_role("apply_plan_changeset", auth)` without a `target_project_id`.
  - `app/auth.py:161-181` only enforces project isolation when `target_project_id` is provided.
  - Reproduction (executed during inspection): a planner key scoped to Project A successfully applied a changeset belonging to Project B and returned `200`.
- Risk:
  - A scoped planner can mutate planning state in other projects by knowing/guessing a changeset ID.
- Recommended fix:
  - Resolve `changeset_id -> project_id` first, then call `require_role("apply_plan_changeset", auth, target_project_id=<resolved_project_id>)` before apply.
  - Add a regression test asserting `403 PROJECT_SCOPE_VIOLATION` for cross-project apply attempts.

### 2) High: Project-scoped keys can create arbitrary new projects

- Requirement impact:
  - Conflicts with strict project-scoped key isolation model (PRD `FR-17`, SRS section 10).
- Evidence:
  - `app/main.py:74-76` calls `require_role("create_project", auth)` with no target project scope.
  - Reproduction (executed during inspection): a planner key scoped to one existing project successfully created a new project (`201`).
- Risk:
  - Any scoped planner/operator key can create projects outside intended ownership boundaries.
- Recommended fix:
  - Treat project creation as bootstrap/admin-only capability:
    - either require a special non-project bootstrap principal,
    - or disallow `create_project` for project-scoped keys and route project creation through trusted bootstrap flow.
  - Add negative test for scoped key attempting `POST /v1/projects`.

### 3) Medium: API contract drift for auth header format

- Requirement impact:
  - Integration contract inconsistency; client confusion and tool mismatch risk.
- Evidence:
  - Implementation expects `Authorization: Bearer <key>` (`app/auth.py:99-119`, tests in `tests/test_auth.py`).
  - OpenAPI spec declares `ApiKeyAuth` as `X-API-Key` header (`docs/api/openapi-v0.1.yaml:627-631`).
- Risk:
  - Generated clients and external consumers using the documented header will fail authentication.
- Recommended fix:
  - Either update OpenAPI to Bearer auth, or support both header forms in `get_auth_context` and document precedence.

### 4) Medium: Test suite misses key isolation regressions

- Evidence:
  - `tests/test_auth.py` covers 401/403/200, lifecycle, and denial logging.
  - No tests currently cover cross-project changeset apply or scoped-key project creation behavior.
- Risk:
  - Isolation regressions can ship while tests remain green.
- Recommended fix:
  - Add targeted tests:
    - `test_apply_changeset_cross_project_returns_403`
    - `test_scoped_key_cannot_create_project`

## What is aligned

- All current `/v1/*` handlers include `Depends(get_auth_context)` and a `require_role(...)` call.
- Role map is explicit and centralized (`ENDPOINT_ROLES` in `app/auth.py`).
- Denied access logging for scoped endpoints exists (`_emit_auth_event` on 403 paths).
- API key CRUD endpoints exist and behave as expected in happy path tests.
- Full repo test suite passes (`99 passed`).

## Overall Assessment

`P3.M3.T3` is partially complete: core auth scaffolding, endpoint wiring, key lifecycle, and baseline tests are in place, but two high-severity isolation gaps remain that violate the project-scoped security model. The task should not be considered fully aligned with requirements/design until those gaps and their regression tests are addressed.
