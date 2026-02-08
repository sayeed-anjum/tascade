# Tascade Runbook

Operational guide for running the Tascade task orchestration system.

Tascade is a coordinator for agentic task orchestration. It provides a REST API
and MCP server for managing projects, tasks, dependencies, gate rules, and plan
changes, plus a read-only web dashboard for reviewing project status.

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | >= 3.12 | Backend runtime |
| Node.js | >= 18 | Frontend build toolchain |
| PostgreSQL | >= 15 (recommended) | Production database |

SQLite is supported for local development and testing (no install required).

---

## 1. Installation

### Clone and enter the repo

```bash
git clone <repo-url>
cd tascade
```

### Backend (Python)

```bash
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
pip install -e ".[dev]"
```

This installs FastAPI, SQLAlchemy, uvicorn, psycopg, aiofiles, pytest, and the
MCP SDK.

### Frontend (Node)

```bash
cd web
npm install
cd ..
```

---

## 2. Database Setup

### Option A: SQLite (quickest for local dev)

```bash
export TASCADE_DATABASE_URL='sqlite+pysqlite:///tascade.db'
```

The SQLite schema is auto-created on first server start via SQLAlchemy
`create_all`. No manual migration step required.

### Option B: PostgreSQL (recommended for production)

Create the database:

```bash
createdb tascade
```

Set the connection string:

```bash
export TASCADE_DATABASE_URL='postgresql+psycopg://postgres:postgres@localhost:5432/tascade'
```

On first server start, Tascade applies SQL migrations from `docs/db/migrations/`
and records them in a `schema_migrations` table. Restarts are idempotent.

**Migration files:**

| File | Description |
|------|-------------|
| `0001_init.sql` | Base schema (projects, tasks, dependencies, artifacts, etc.) |
| `0002_task_class_gate_types.sql` | Gate task classes |
| `0003_short_ids.sql` | Human-readable short ID generation |
| `0004_gate_candidate_link.sql` | Gate candidate links |

**Optional overrides:**

| Variable | Purpose |
|----------|---------|
| `TASCADE_DB_MIGRATIONS_DIR` | Custom migrations directory |
| `TASCADE_DB_MIGRATION_SQL` | Run a single SQL file instead of directory scan |

---

## 3. Running the Server

### Quick start (builds frontend + serves everything)

```bash
make serve
```

This runs `npm install && npm run build` in `web/`, then starts uvicorn on
**port 8010**. Open http://localhost:8010 in your browser.

### Manual start (API only, no frontend build)

```bash
uvicorn app.main:app --reload --port 8010
```

Add `--host 0.0.0.0` to listen on all interfaces.

If `web/dist/` exists from a previous build, the server also serves the
dashboard. If it does not exist, only the API is available.

### Architecture

```
Browser ──► http://localhost:8010
              │
              ├── /v1/*          → FastAPI REST endpoints
              ├── /health        → Health check
              ├── /assets/*      → Vite-hashed JS/CSS bundles
              └── /*             → SPA fallback (index.html)
```

All API routes (`/v1/*`) take precedence. Any other path is resolved against
`web/dist/` first; if no matching file is found, `index.html` is returned for
React Router to handle client-side.

---

## 4. Development Workflow

For active frontend development, run the backend and Vite dev server
separately to get hot-module replacement:

**Terminal 1 — Backend:**

```bash
export TASCADE_DATABASE_URL='sqlite+pysqlite:///tascade.db'
uvicorn app.main:app --reload --port 8010
```

**Terminal 2 — Frontend dev server:**

```bash
cd web
npm run dev
```

Vite starts on http://localhost:5173 and proxies `/v1` and `/health` requests
to `localhost:8010` automatically.

---

## 5. Running Tests

### Backend

```bash
pytest -q
```

Tests use an in-memory SQLite database — no external database needed.

### Frontend

```bash
cd web
npm run test          # single run
npm run test:watch    # watch mode
```

Tests use vitest + jsdom + React Testing Library + MSW for API mocking +
vitest-axe for accessibility audits.

### All tests together

```bash
pytest -q && cd web && npm run test && cd ..
```

---

## 6. MCP Server (Agent Integration)

The MCP server lets AI agents interact with Tascade for task orchestration.
It uses the stdio transport — the agent tool launches the server process and
communicates over stdin/stdout.

### The launcher script

`mcp-server.sh` is a self-locating wrapper that `cd`s into the repo root
before starting the MCP server. Use its absolute path in all agent configs
so you never need to set `cwd` separately:

```bash
/absolute/path/to/tascade/mcp-server.sh
```

To start it manually (useful for debugging):

```bash
./mcp-server.sh
```

### Claude Code

Add to your project's `.mcp.json` (project-scoped) or
`~/.claude.json` (global):

```json
{
  "mcpServers": {
    "tascade": {
      "command": "/absolute/path/to/tascade/mcp-server.sh",
      "env": {
        "TASCADE_DATABASE_URL": "postgresql+psycopg://postgres:postgres@localhost:5432/tascade"
      }
    }
  }
}
```

The `env` block is optional — omit it to use the default PostgreSQL connection
string, or set it to a SQLite URL for local dev.

### Codex (OpenAI)

Add to `~/.codex/config.toml` (global) or `.codex/config.toml`
(project-scoped, requires trusted project):

```toml
[mcp_servers.tascade]
command = "/absolute/path/to/tascade/mcp-server.sh"

[mcp_servers.tascade.env]
TASCADE_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/tascade"
```

Verify with `codex mcp` or `/mcp` inside a Codex session.

### OpenCode

Add to `opencode.json` in the project root, or
`~/.config/opencode/opencode.json` (global):

```json
{
  "mcp": {
    "tascade": {
      "type": "local",
      "command": ["/absolute/path/to/tascade/mcp-server.sh"],
      "environment": {
        "TASCADE_DATABASE_URL": "postgresql+psycopg://postgres:postgres@localhost:5432/tascade"
      }
    }
  }
}
```

Note: OpenCode uses `"command"` as an array and `"environment"` instead of
`"env"`.

### Available MCP tools

**Projects:**
`create_project`, `get_project`, `list_projects`, `get_project_graph`

**Structure:**
`create_phase`, `create_milestone`

**Tasks:**
`create_task`, `get_task`, `list_tasks`, `list_ready_tasks`,
`claim_task`, `heartbeat_task`, `assign_task`, `transition_task_state`,
`create_dependency`, `get_task_context`

**Artifacts & Integration:**
`create_task_artifact`, `list_task_artifacts`,
`enqueue_integration_attempt`, `update_integration_attempt_result`,
`list_integration_attempts`

**Gates:**
`create_gate_rule`, `create_gate_decision`, `list_gate_decisions`,
`evaluate_gate_policies`

**Planning:**
`create_plan_changeset`, `apply_plan_changeset`

---

## 7. REST API Reference

Base URL: `http://localhost:8010/v1`

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Returns `{"status": "ok"}` |

### Projects

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/projects` | Create a project |
| GET | `/v1/projects` | List projects |
| GET | `/v1/projects/{id}` | Get project by ID |
| GET | `/v1/projects/{id}/graph` | Get full task dependency graph |

### Tasks

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/tasks` | Create a task |
| GET | `/v1/tasks` | List tasks (filterable by state, phase, capability) |
| GET | `/v1/tasks/{id}` | Get task by ID |
| GET | `/v1/tasks/ready` | List tasks ready for agent pickup |
| POST | `/v1/tasks/{id}/claim` | Claim a task (acquire lease) |
| POST | `/v1/tasks/{id}/heartbeat` | Renew task lease |
| POST | `/v1/tasks/{id}/assign` | Assign task to an agent |
| POST | `/v1/tasks/{id}/state` | Transition task state |

### Dependencies

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/dependencies` | Create a dependency edge (with cycle detection) |

### Artifacts

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/tasks/{id}/artifacts` | Create artifact (branch, SHA, files) |
| GET | `/v1/tasks/{id}/artifacts` | List artifacts for a task |

### Integration Attempts

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/tasks/{id}/integration-attempts` | Enqueue integration attempt |
| GET | `/v1/tasks/{id}/integration-attempts` | List integration attempts |
| POST | `/v1/integration-attempts/{id}/result` | Record attempt result |

### Gate Rules & Decisions

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/gate-rules` | Create a gate rule |
| POST | `/v1/gate-decisions` | Create a gate decision |
| GET | `/v1/gate-decisions` | List gate decisions |
| GET | `/v1/gates/checkpoints` | List gate checkpoints |

### Plan Management

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/plans/changesets` | Create plan changeset |
| POST | `/v1/plans/changesets/{id}/apply` | Apply changeset (with conflict detection) |

---

## 8. Web Dashboard

The dashboard is a read-only reviewer interface. It does not expose any
mutation controls — all changes go through the API or MCP server.

### Pages

| URL | View | Description |
|-----|------|-------------|
| `/projects` | Project List | All projects with task count and health indicator |
| `/projects/:id/tasks` | Kanban Board | Tasks organized by state columns with filtering |
| `/projects/:id/checkpoints` | Checkpoint List | Gate checkpoints with status and task links |
| `/projects/:id/tasks/:taskId` | Task Detail | Slide-in panel with work spec, dependencies, artifacts, gate decisions |

### Filtering (Kanban Board)

The filter bar supports narrowing tasks by:
- Phase
- Milestone
- State
- Task class
- Capability tag
- Free-text search

### Keyboard navigation

All interactive elements (task cards, filter controls, links) support keyboard
focus with visible focus rings. Task cards respond to Enter and Space keys.

---

## 9. Task Lifecycle

States flow in this order:

```
pending → reserved → in_progress → implemented → integrated
```

| State | Meaning |
|-------|---------|
| `pending` | Created, not yet picked up |
| `reserved` | Assigned/reserved for a specific agent |
| `in_progress` | Actively being worked on (lease held) |
| `implemented` | Work complete, awaiting review |
| `integrated` | Reviewed and merged |

Gate tasks (`review_gate`, `merge_gate`) follow the same lifecycle. The
`implemented → integrated` transition requires `reviewed_by` to be set to a
value different from `actor_id` (no self-review).

---

## 10. Troubleshooting

### Server won't start

**`ModuleNotFoundError: aiofiles`** — Run `pip install -e ".[dev]"` to install
all dependencies including `aiofiles` (required for static file serving).

**`connection refused` on PostgreSQL** — Verify PostgreSQL is running and the
`TASCADE_DATABASE_URL` connection string is correct. For quick local dev, use
SQLite instead.

### Frontend build fails

**`tsc: command not found`** — Run `npm install` in the `web/` directory first.

### Dashboard shows blank page

The SPA is only served when `web/dist/` exists. Run `make build-web` or
`cd web && npm run build` to create the production bundle.

### Tests fail with missing `web/dist`

Backend static-serving tests are skipped automatically when `web/dist/` is
absent. If you need them to run, build the frontend first.

### axe-core `region` violations in tests

Component tests render without the full `PageShell` landmark structure.
The test suite disables the axe `region` rule for isolated component tests.
This is expected and does not indicate an accessibility problem.
