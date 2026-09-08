# API and CLI Reference (Current)

## OpenAPI

- Spec file: `docs/api/openapi-v0.1.yaml`
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
- Phases: `POST /v1/phases`
- Milestones: `POST /v1/milestones`
- Tasks: `/v1/tasks*`
- Dependencies: `/v1/dependencies`
- Planning: `/v1/plans/changesets*`
- Gates: `/v1/gate-rules`, `/v1/gate-decisions`, `/v1/gates/checkpoints`,
  `/v1/gates/evaluate`
- Artifacts/Integration: task artifacts and integration-attempt endpoints
- API keys: `/v1/api-keys*`
- Metrics: `/v1/metrics/*`
- Task context: `GET /v1/tasks/{task_id}/context`
- Protocol guide: `GET /v1/instructions` (unauthenticated)

## CLI

`tascade` is the primary agent interface (design decision D2). It is a thin
client over the REST endpoints above and never touches the store.

- Skill file for agents: [`docs/cli-skill.md`](../cli-skill.md), printable with
  `tascade --skill`.
- Config: `~/.config/tascade/config.toml`, overridden by `TASCADE_URL` /
  `TASCADE_API_KEY`, overridden by `--url` / `--api-key`.
- Every subcommand accepts `--json`.

Coverage is enforced against the routes themselves. `tests/test_cli_commands.py`
fails if a route registered on the FastAPI app has neither a subcommand nor an
entry in `ROUTE_EXEMPTIONS` (`app/cli/commands.py`), which records the reason
each excluded route is excluded. The two surfaces cannot drift.

## Compatibility Note

`GET /v1/tasks/ready` accepts `capabilities` as either:

- repeated query parameters (preferred)
- one comma-delimited `string`

The CLI's repeatable `--capability` flag sends the comma-delimited form.
