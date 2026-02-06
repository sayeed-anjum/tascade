# Tascade (Vertical Slice)

Minimal FastAPI vertical slice implementing:
- task/dependency creation with cycle rejection
- ready queue, claim, heartbeat
- plan change-set create/apply
- material-change invalidation for claimed/reserved tasks
- task execution snapshot capture on claim/start

## Run Tests

```bash
pytest -q
```

## Run API

```bash
export TASCADE_DATABASE_URL='postgresql+psycopg://postgres:postgres@localhost:5432/tascade'
uvicorn app.main:app --reload --port 8010
```

If `TASCADE_DATABASE_URL` is not set, the app defaults to:

`postgresql+psycopg://postgres:postgres@localhost:5432/tascade`

## Migration bootstrap

For PostgreSQL, app startup applies pending SQL files in `docs/db/migrations` and records them in
`schema_migrations`. This makes restarts idempotent.

Optional overrides:

- `TASCADE_DB_MIGRATIONS_DIR`: directory containing ordered `*.sql` migrations.
- `TASCADE_DB_MIGRATION_SQL`: run a single SQL file instead of directory discovery.

## MCP server

An MCP server is available for agent setup + execution orchestration:

```bash
python -m app.mcp_server
```

Available tools:

- `create_project`
- `create_phase`
- `create_milestone`
- `create_task`
- `create_dependency`
- `list_ready_tasks`
- `claim_task`
- `heartbeat_task`
- `assign_task`
- `create_plan_changeset`
- `apply_plan_changeset`
- `get_task_context`
- `get_project_graph`
