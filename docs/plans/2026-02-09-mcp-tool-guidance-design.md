# MCP Tool Guidance — Design Doc

**Date:** 2026-02-09
**Problem:** Agents using the Tascade MCP server fail repeatedly when setting up projects because tools provide no workflow guidance, signatures lie about required params, and errors are generic.

## Root Causes

1. **Zero docstrings** on all 25 MCP tools — agents get param names/types only
2. **Lying signatures** — `phase_id` and `milestone_id` typed as `str | None = None` but rejected at runtime
3. **Swallowed errors** — invalid `task_class` enum and malformed `work_spec` both become `INVARIANT_VIOLATION`
4. **Undiscoverable enums** — valid `task_class` values and `work_spec` schema buried in model code

## Changes

### 1. Fix Signatures (`app/mcp_tools.py`)

**`create_milestone`:** `phase_id: str` (was `str | None = None`)

**`create_task`:** `milestone_id: str` (was `str | None = None`), moved before optional params. `phase_id` stays optional (inferred from milestone).

### 2. Add Validation (`app/mcp_tools.py`)

**task_class validation:** Check against `TaskClass` enum values before hitting store. Raise `ValueError("INVALID_TASK_CLASS")` on mismatch.

**work_spec validation:** Check that `objective` key exists and is a string. Raise `ValueError("INVALID_WORK_SPEC")` on mismatch.

### 3. Register New Errors (`app/mcp_server.py`)

Add to `_DOMAIN_ERRORS`:

```python
"INVALID_TASK_CLASS": (
    "Invalid task_class. Valid: architecture, db_schema, security, "
    "cross_cutting, review_gate, merge_gate, frontend, backend, crud, other",
    False,
),
"INVALID_WORK_SPEC": (
    "work_spec must include 'objective' (string). Optional: "
    "'acceptance_criteria' (list[str]), 'constraints' (list[str]), "
    "'interfaces' (list[str]), 'path_hints' (list[str])",
    False,
),
```

### 4. Add Docstrings (`app/mcp_tools.py`)

Short, factual docstrings on all 25 tools. Key ones:

- `create_project` → mentions next step is `create_phase`
- `create_phase` → mentions `sequence`, short_id format, next step is `create_milestone`
- `create_milestone` → mentions `sequence`, short_id format, next step is `create_task`
- `create_task` → lists valid `task_class` values, `work_spec` schema, initial state
- `transition_task_state` → lists states, gate/review requirements
- All other tools get 1-3 line docstrings with essential usage info

### 5. No Changes to `app/store.py`

Guards remain for REST API path. MCP agents never hit them since FastMCP enforces required params.

## Test Plan

- Existing tests pass unchanged (all already provide required params)
- Add test: `create_task` with invalid `task_class` → `INVALID_TASK_CLASS`
- Add test: `create_task` with missing `work_spec.objective` → `INVALID_WORK_SPEC`
