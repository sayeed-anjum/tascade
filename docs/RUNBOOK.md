# Tascade Runbook (Current)

## Prerequisites

- Python 3.12+
- Node 18+
- PostgreSQL 15+ (recommended)

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cd web
npm install
cd ..
```

## Database

Default DB URL (if unset):

`postgresql+psycopg://postgres:postgres@localhost:5432/tascade`

Optional local SQLite:

```bash
export TASCADE_DATABASE_URL='sqlite+pysqlite:///tascade.db'
```

Migrations:
- Postgres startup applies SQL files from `docs/db/migrations/`.
- SQLite uses SQLAlchemy schema creation for local workflows.

## Run Backend

```bash
uvicorn app.main:app --reload --port 8010
```

Quick serve with built web UI:

```bash
make serve
```

## Run Tests

Backend:

```bash
pytest -q
```

Frontend:

```bash
cd web
npm run test
```

## MCP Server

Start with self-locating script:

```bash
./mcp-server.sh
```

MCP details: `docs/api/README.md`

## Task Lifecycle (Canonical)

Primary flow:

`backlog -> ready -> claimed -> in_progress -> implemented -> integrated`

Additional states used for exception/control lanes:

- `reserved`
- `blocked`
- `conflict`
- `abandoned`
- `cancelled`

Integration guardrails:

- `implemented -> integrated` requires explicit reviewer identity and evidence.
- Self-review is rejected.
- Gate-class tasks require approved gate decision before integration.

## Common Troubleshooting

1. Auth failures (`401`/`403`): verify bearer key, role scopes, and project scope.
2. Migration/schema errors: verify DB URL and that startup migration pass completed.
3. Missing UI assets: build frontend (`cd web && npm run build`) or use `make serve`.
4. Stale plan apply (`PLAN_STALE`): re-create changeset or apply with explicit rebase allowance.
