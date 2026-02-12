# Tascade

Dependency-aware task orchestration for multi-agent software execution.

Tascade is a coordination substrate that lets multiple AI agents (or humans)
work on the same codebase in parallel without stepping on each other.
It enforces execution-safe invariants — cycle-free dependencies, lease-based
claiming, gate-controlled integration — through a REST API and an
MCP server that any LLM-based agent can call directly.

## Why Tascade

Standard task trackers treat tasks as flat lists with status labels.
That works for humans but breaks down when 10+ agents execute concurrently:

- **Merge conflicts** — two agents edit the same files without knowing.
- **Stale foundations** — agent B builds on code agent A is about to rewrite.
- **Review firehose** — all work lands at once with no batching or ordering.

Tascade prevents these structurally:

| Problem | How Tascade solves it |
|---|---|
| Merge conflicts | File-touch tracking, dependency edges, conflict detection |
| Stale foundations | Execution snapshots on claim, material-change invalidation |
| Review overload | First-class `review_gate` and `merge_gate` task types with checkpoint batching |
| Lost work | Lease-based claiming with heartbeat expiry, immutable artifact records |
| Integration chaos | Two-state completion (`implemented` then `integrated`), self-review structurally prevented |

## Quick start

### Prerequisites

- Python 3.12+
- PostgreSQL 15+ (or use SQLite for development)
- Node.js 20+ (for the web dashboard)

### Install and run

```bash
# Clone and install Python dependencies
git clone https://github.com/sayeed-anjum/tascade.git
cd tascade
pip install -e ".[dev]"

# Option A: Quick start with SQLite (no PostgreSQL needed)
TASCADE_DATABASE_URL=sqlite+pysqlite:///tascade.db \
TASCADE_AUTH_DISABLED=1 \
uvicorn app.main:app --reload --port 8010

# Option B: PostgreSQL (recommended for production)
export TASCADE_DATABASE_URL='postgresql+psycopg://postgres:postgres@localhost:5432/tascade'
export TASCADE_AUTH_DISABLED=1
uvicorn app.main:app --reload --port 8010
```

The API is now at `http://localhost:8010`. Auth is disabled for local
development — see [Authentication](#authentication) to enable it.

### Build and serve with the web dashboard

```bash
make serve   # builds React UI + starts FastAPI on port 8010
```

Open `http://localhost:8010` for the dashboard.

### Run tests

```bash
pytest -q              # backend (257 tests)
cd web && npm test     # frontend (vitest)
```

## Core concepts

### Task lifecycle

```
backlog → ready → claimed → in_progress → implemented → integrated
```

Tasks move through states with enforced invariants at each transition.
The split between `implemented` and `integrated` is deliberate:

- **implemented** = code is done, tests pass, artifact published. Ready for review.
- **integrated** = reviewed, approved, merged. A different person must approve (self-review is structurally prevented).

Exception states: `reserved`, `blocked`, `conflict`, `abandoned`, `cancelled`.

### Project hierarchy

```
Project → Phase → Milestone → Task
```

Tasks live inside milestones. Dependencies are edges between tasks with
configurable unlock conditions (`implemented` or `integrated`).

### Roles

Five roles control who can do what:

| Role | Can do |
|---|---|
| `planner` | Create tasks, dependencies, changesets |
| `agent` | Claim tasks, heartbeat, publish artifacts |
| `reviewer` | Create gate decisions |
| `operator` | Manage integration attempts, assign tasks |
| `admin` | All of the above + API key management |

### Gates and checkpoints

Gate tasks (`review_gate`, `merge_gate`) act as synchronization barriers.
They batch related work at natural boundaries so reviewers see coherent
changesets instead of a stream of individual PRs.

## Interfaces

Tascade exposes three interfaces. All share the same backend state.

### REST API (47 endpoints)

Full CRUD for projects, tasks, dependencies, gates, artifacts, integration
attempts, plan changesets, API keys, and metrics.

```bash
# Create a project
curl -X POST http://localhost:8010/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "my-project"}'

# List ready tasks for an agent
curl "http://localhost:8010/v1/tasks/ready?project_id=<PROJECT_ID>&agent_id=agent-1"
```

See [docs/api/README.md](docs/api/README.md) for the full endpoint reference
and [docs/api/openapi-v0.1.yaml](docs/api/openapi-v0.1.yaml) for the OpenAPI spec.

### MCP server (32 tools)

The MCP (Model Context Protocol) server lets AI agents call Tascade directly.
Use the self-locating launcher:

```bash
./mcp-server.sh
```

**Agent configuration (Claude Code):**

```json
{
  "mcpServers": {
    "tascade": {
      "command": "/path/to/tascade/mcp-server.sh"
    }
  }
}
```

<details>
<summary>Full MCP tool list (32 tools)</summary>

**Project management:** `create_project`, `get_project`, `list_projects`, `create_phase`, `create_milestone`

**Task execution:** `create_task`, `get_task`, `list_tasks`, `list_ready_tasks`, `claim_task`, `heartbeat_task`, `assign_task`, `transition_task_state`, `create_task_artifact`, `list_task_artifacts`, `get_task_context`

**Dependencies:** `create_dependency`, `get_project_graph`

**Integration:** `enqueue_integration_attempt`, `update_integration_attempt_result`, `list_integration_attempts`

**Planning:** `create_plan_changeset`, `apply_plan_changeset`

**Gates:** `create_gate_rule`, `create_gate_decision`, `list_gate_decisions`, `evaluate_gate_policies`

**Metrics:** `get_metrics_summary`, `get_metrics_trends`, `get_metrics_alerts`

**Documentation:** `get_instructions`

</details>

### Web dashboard

A read-only React dashboard for operational visibility:

- Project overview with task state breakdown
- Kanban board with dependency links
- Task detail panel (artifacts, dependencies, timeline)
- Metrics dashboard (velocity, health, forecasts, alerts)

The dashboard is built with React 19, TypeScript, TailwindCSS, and Radix UI.
It is embedded in the FastAPI server — `make serve` builds and serves everything.

For frontend development:

```bash
cd web
npm install
npm run dev    # Vite dev server with API proxy to localhost:8010
```

## Authentication

Auth is disabled by default for local development (`TASCADE_AUTH_DISABLED=1`).

To enable project-scoped API key auth:

```bash
# 1. Unset the disable flag (or set to empty)
unset TASCADE_AUTH_DISABLED

# 2. Create an API key
python scripts/create_api_key.py --project-id <PROJECT_ID> --roles admin

# 3. Use the key in requests
curl -H "Authorization: Bearer tsk_<your_key>" http://localhost:8010/v1/projects
```

Keys are hashed with SHA-256 before storage. The raw key is shown only once
at creation time.

## Database

### PostgreSQL (recommended)

```bash
export TASCADE_DATABASE_URL='postgresql+psycopg://postgres:postgres@localhost:5432/tascade'
```

Migrations in `docs/db/migrations/` are applied automatically on startup and
tracked in `schema_migrations` for idempotency.

### SQLite (development)

```bash
export TASCADE_DATABASE_URL='sqlite+pysqlite:///tascade.db'
```

SQLite uses `CREATE ALL` from the ORM models. Good for local development and
testing; PostgreSQL is required for production.

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `TASCADE_DATABASE_URL` | Yes | Database connection string |
| `TASCADE_AUTH_DISABLED` | No | Set to `1` to disable auth (dev only) |
| `TASCADE_DB_MIGRATIONS_DIR` | No | Override migrations directory path |
| `VITE_API_BASE_URL` | No | Frontend API base URL (default: empty, uses proxy) |
| `VITE_API_TOKEN` | No | Frontend Bearer token for authenticated requests |

See [.env.example](.env.example) for a complete template.

## Project structure

```
app/
  main.py           # FastAPI routes (47 endpoints)
  store.py          # Core orchestration logic and state invariants
  models.py         # SQLAlchemy ORM models
  schemas.py        # Pydantic request/response schemas
  auth.py           # API key auth + role enforcement
  db.py             # Database connection + migration runner
  mcp_tools.py      # MCP tool handlers (32 tools)
  mcp_server.py     # MCP stdio server
  metrics/          # Metrics computation (materializer, alerts, forecast, actions)
docs/
  PRD.md            # Product requirements
  SRS.md            # System requirements specification
  ARCHITECTURE.md   # Architecture overview
  WHY.md            # Design philosophy
  RUNBOOK.md        # Operations guide
  BACKLOG.md        # Outstanding work items
  api/              # API reference + OpenAPI spec
  db/               # SQL schema + migrations
  metrics/          # Metrics rulebook
web/                # React + TypeScript dashboard
tests/              # 257 backend tests
scripts/            # Utilities (API key creation, smoke tests, benchmarks)
```

## Documentation

| Document | Description |
|---|---|
| [docs/PRD.md](docs/PRD.md) | Product requirements and success criteria |
| [docs/SRS.md](docs/SRS.md) | System requirements, domain model, API contract |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Architecture, state machine, auth model |
| [docs/WHY.md](docs/WHY.md) | Design philosophy — why Tascade exists |
| [docs/RUNBOOK.md](docs/RUNBOOK.md) | Installation, deployment, troubleshooting |
| [docs/api/README.md](docs/api/README.md) | REST API reference |
| [docs/api/openapi-v0.1.yaml](docs/api/openapi-v0.1.yaml) | OpenAPI 3.1 specification |
| [docs/BACKLOG.md](docs/BACKLOG.md) | Outstanding work items |
| [AGENTS.md](AGENTS.md) | Agent workflow guide (dogfooding SOP) |

## CI/CD

GitHub Actions runs on every PR and push to `main`:

1. **Unit tests** — full pytest suite against SQLite
2. **PostgreSQL E2E** — migrations + smoke tests against PostgreSQL 16
3. **MCP smoke test** — validates MCP server starts and tools respond

## Contributing

1. Fork the repository
2. Create a feature branch
3. Run tests: `pytest -q && cd web && npm test`
4. Open a pull request

## License

[MIT](LICENSE)
