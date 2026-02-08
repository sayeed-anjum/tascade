# API and MCP Reference (Current)

## OpenAPI

- Spec file: `/Users/sayeedanjum/projects/tascade/docs/api/openapi-v0.1.yaml`
- Source of truth: generated from live FastAPI app.

Regenerate:

```bash
python - <<'PY'
from pathlib import Path
import yaml
from app.main import app
Path('docs/api/openapi-v0.1.yaml').write_text(
    yaml.safe_dump(app.openapi(), sort_keys=False),
    encoding='utf-8',
)
PY
```

## Authentication

All protected endpoints use Bearer API key auth:

```http
Authorization: Bearer tsk_<raw_key>
```

## REST Endpoint Groups

- Health: `/health`
- Projects: `/v1/projects*`
- Tasks: `/v1/tasks*`
- Dependencies: `/v1/dependencies`
- Planning: `/v1/plans/changesets*`
- Gates: `/v1/gate-rules`, `/v1/gate-decisions`, `/v1/gates/checkpoints`
- Artifacts/Integration: task artifacts and integration-attempt endpoints
- API keys: `/v1/api-keys*`
- Metrics: `/v1/metrics/*`

## MCP Tools

Registered tools:

- `create_project`
- `create_gate_rule`
- `create_gate_decision`
- `list_gate_decisions`
- `evaluate_gate_policies`
- `get_project`
- `list_projects`
- `create_phase`
- `create_milestone`
- `create_task`
- `get_task`
- `transition_task_state`
- `create_dependency`
- `list_tasks`
- `create_task_artifact`
- `list_task_artifacts`
- `enqueue_integration_attempt`
- `update_integration_attempt_result`
- `list_integration_attempts`
- `list_ready_tasks`
- `claim_task`
- `heartbeat_task`
- `assign_task`
- `create_plan_changeset`
- `apply_plan_changeset`
- `get_task_context`
- `get_project_graph`

## Compatibility Note

`list_ready_tasks.capabilities` accepts both:

- `list[str]` (preferred)
- comma-delimited `string`

See `/Users/sayeedanjum/projects/tascade/docs/api/mcp-list-ready-tasks.md`.
