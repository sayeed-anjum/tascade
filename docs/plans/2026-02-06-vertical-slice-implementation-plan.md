# Tascade Vertical Slice Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a minimal working coordinator vertical slice for core task execution, claiming, replanning, and dependency validation from the v0.1 contracts.

**Architecture:** Build a small FastAPI service backed by SQLite for local development and deterministic tests. Implement only required endpoints and invariants: dependency cycle detection, hard-reservation + claim behavior, plan change-set apply invalidation rules, and execution snapshot capture. Keep logic centralized in a service layer to preserve state-machine invariants.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Pydantic, pytest

---

### Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `app/__init__.py`
- Create: `app/main.py`
- Create: `app/db.py`
- Create: `app/models.py`
- Create: `app/schemas.py`

**Step 1: Write failing smoke test**
- Add test that imports app and calls health endpoint.

**Step 2: Run test to verify failure**
- Run: `pytest -q tests/test_smoke.py`

**Step 3: Implement minimal app**
- Add FastAPI app + `/health` endpoint.

**Step 4: Run test to verify pass**
- Run: `pytest -q tests/test_smoke.py`

### Task 2: Core task/dependency endpoints

**Files:**
- Create: `app/services.py`
- Create: `tests/test_tasks_dependencies.py`
- Modify: `app/main.py`
- Modify: `app/models.py`
- Modify: `app/schemas.py`

**Step 1: Write failing tests**
- Create task, create dependency, reject cyclic dependency.

**Step 2: Verify RED**
- Run targeted tests and confirm cycle-rejection failure first.

**Step 3: Implement minimal code**
- Add task/dependency persistence + app-layer cycle detection.

**Step 4: Verify GREEN**
- Run: `pytest -q tests/test_tasks_dependencies.py`

### Task 3: Ready/claim/heartbeat flow

**Files:**
- Create: `tests/test_claim_heartbeat.py`
- Modify: `app/services.py`
- Modify: `app/main.py`
- Modify: `app/models.py`
- Modify: `app/schemas.py`

**Step 1: Write failing tests**
- `GET /v1/tasks/ready`, `POST /claim`, `POST /heartbeat` with lease token checks.

**Step 2: Verify RED**
- Run targeted tests.

**Step 3: Implement minimal code**
- Add lease creation, active-lease constraints, heartbeat refresh.

**Step 4: Verify GREEN**
- Run: `pytest -q tests/test_claim_heartbeat.py`

### Task 4: Plan changeset apply + invalidation + snapshot

**Files:**
- Create: `tests/test_plan_changesets.py`
- Modify: `app/services.py`
- Modify: `app/main.py`
- Modify: `app/models.py`
- Modify: `app/schemas.py`

**Step 1: Write failing tests**
- Create changeset/apply, invalidate materially changed claimed/reserved tasks, preserve priority-only changes, snapshot captured at claim.

**Step 2: Verify RED**
- Run targeted tests.

**Step 3: Implement minimal code**
- Add changeset persistence/apply logic and `TaskExecutionSnapshot`.

**Step 4: Verify GREEN**
- Run: `pytest -q tests/test_plan_changesets.py`

### Task 5: Final verification

**Files:**
- Modify: `README.md` (if needed for run/test instructions)

**Step 1: Run full suite**
- Run: `pytest -q`

**Step 2: Run quick API import check**
- Run: `python3 -c "from app.main import app; print(app.title)"`

**Step 3: Confirm contract coverage**
- Ensure required endpoints are present in router.
