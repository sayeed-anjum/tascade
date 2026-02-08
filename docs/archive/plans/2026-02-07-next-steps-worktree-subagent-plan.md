# Next-Step Hardening Bundle Implementation Plan

> Historical dated document.
> Treat scope and sequencing in this file as point-in-time planning context; verify current implementation in code/tests.

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver four hardening items: review-evidence enforcement, short-id read lookup, implemented-task readiness report, and one subagent worktree trial.

**Architecture:** Implement each item in an isolated `codex/*` worktree lane, then merge lanes back to `main` by cherry-picking validated commits. Keep API/MCP behavior backward-compatible where possible and add targeted tests for each feature.

**Tech Stack:** Python, FastAPI, SQLAlchemy, pytest, git worktrees, Tascade MCP tools.

---

### Task 1: Review Evidence Gate (lane 1)

**Files:**
- Modify: `app/schemas.py`
- Modify: `app/store.py`
- Modify: `app/main.py`
- Modify: `app/mcp_tools.py`
- Modify: `app/mcp_server.py`
- Modify: `tests/test_task_state_transitions.py`
- Modify: `tests/test_mcp_tools.py`

Steps:
1. Add failing tests for `implemented -> integrated` without explicit review evidence.
2. Add request/schema fields for review evidence.
3. Enforce invariant in store transition logic.
4. Map domain errors in API/MCP handlers.
5. Re-run focused then full tests.

### Task 2: Short-ID Lookup in Read Paths (lane 2)

**Files:**
- Modify: `app/store.py`
- Modify: `app/mcp_tools.py`
- Modify: `app/main.py`
- Modify: `app/mcp_server.py`
- Modify: `tests/test_mcp_tools.py`
- Modify: `tests/test_tasks_dependencies.py` (if endpoint behavior requires)

Steps:
1. Add failing tests for `get_task` using short ID.
2. Implement resolver in store (`UUID or short_id`, with ambiguity guard).
3. Wire MCP/API read paths to resolver.
4. Add error code for ambiguous short-id references.
5. Run focused then full tests.

### Task 3: Implemented Readiness Scan Report (lane 3)

**Files:**
- Create: `scripts/report_implemented_readiness.py`
- Create: `tests/test_report_implemented_readiness.py`
- Optional docs: `README.md` command snippet

Steps:
1. Add failing test(s) for report output and missing-field detection.
2. Implement script to list `implemented` tasks missing review package fields.
3. Include machine-readable mode (JSON) and human summary mode.
4. Run focused tests and script smoke check.

### Task 4: Subagent Worktree Trial + SOP Adjustments (lane 4)

**Files:**
- Create: `docs/reviews/2026-02-07-subagent-worktree-trial.md`
- Modify: `AGENTS.task.md` (only if friction found)
- Modify: `AGENTS.md` (only if orchestration friction found)

Steps:
1. Execute one representative task flow in isolated worktree with AGENTS.task rules.
2. Record observed friction points.
3. Apply minimal SOP adjustments.
4. Validate docs references and consistency.

### Integration Steps

1. Create `.worktrees/` and ensure it is gitignored.
2. Create four branches: 
   - `codex/review-evidence-gate`
   - `codex/shortid-read-lookup`
   - `codex/implemented-readiness-report`
   - `codex/subagent-trial`
3. Run each task lane in its worktree.
4. Cherry-pick each lane commit into `main`.
5. Run `pytest -q` on `main`.
6. Publish artifact summary and transition task status.
