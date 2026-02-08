# P5.M3 Metrics Subsystem -- Deployment and Rollback Runbook

## Overview

This runbook covers the end-to-end deployment, verification, and rollback
procedures for the Tascade metrics subsystem (P5.M3). The metrics subsystem
adds seven REST endpoints and eight database migrations.

---

## Table of Contents

1. [Pre-deployment Checklist](#1-pre-deployment-checklist)
2. [Environment Variable Manifest](#2-environment-variable-manifest)
3. [Database Migrations](#3-database-migrations)
4. [Staging Deployment](#4-staging-deployment)
5. [Staging Smoke Tests](#5-staging-smoke-tests)
6. [Production Deployment](#6-production-deployment)
7. [Post-deployment Verification](#7-post-deployment-verification)
8. [Rollback Procedure](#8-rollback-procedure)
9. [Rollback Rehearsal](#9-rollback-rehearsal)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Pre-deployment Checklist

Complete every item before proceeding to deployment.

- [ ] All P5.M3 task branches (T1--T6) merged into the release branch
- [ ] Full test suite passes (`python -m pytest tests/ -v --timeout=60`)
- [ ] Database backup taken (staging and production)
- [ ] `psql` available on the deployment host
- [ ] All required environment variables set (see Section 2)
- [ ] Migration files present in `docs/db/migrations/` (0001--0008)
- [ ] Rollback script available at `scripts/rollback_metrics.sh`
- [ ] Smoke test script available at `scripts/smoke_test_metrics.py`
- [ ] `requests` Python package installed in the deployment environment
- [ ] Communication sent to on-call team about planned deployment window

---

## 2. Environment Variable Manifest

All `TASCADE_*` variables required for production operation:

| Variable | Required | Description | Example |
|---|---|---|---|
| `TASCADE_DATABASE_URL` | Yes | PostgreSQL connection string | `postgresql+psycopg://user:pass@host:5432/tascade` |
| `TASCADE_AUTH_DISABLED` | No | Set to empty or unset in production; set to `1` only in test environments | _(unset)_ |
| `TASCADE_API_KEY` | Yes (prod) | API key for Bearer token authentication | `sk-tascade-...` |
| `VITE_API_BASE_URL` | Yes (web) | Frontend API base URL | `https://tascade.example.com` |
| `VITE_API_TOKEN` | Yes (web) | Frontend auth token for API requests | `sk-tascade-...` |
| `TASCADE_DB_MIGRATIONS_DIR` | No | Override path to migrations directory | `/opt/tascade/docs/db/migrations` |

**Important**: `TASCADE_AUTH_DISABLED` must NOT be set to `1` in production.

---

## 3. Database Migrations

The metrics subsystem adds migrations 0005 through 0008. All migrations are
applied automatically by `app.db.init_db()` on application startup.

### Migration Order

| File | Description | Tables Created |
|---|---|---|
| `0001_init.sql` | Base schema (projects, tasks, etc.) | core tables |
| `0002_task_class_gate_types.sql` | Task class and gate types | -- |
| `0003_short_ids.sql` | Short ID support | -- |
| `0004_gate_candidate_link.sql` | Gate candidate links | `gate_candidate_link` |
| `0005_metrics_read_model.sql` | Metrics read model tables | `metrics_summary`, `metrics_trend_point`, `metrics_breakdown_point`, `metrics_drilldown` |
| `0006_metrics_incremental_jobs.sql` | Incremental job tracking | `metrics_job_checkpoint`, `metrics_state_transition_counter`, `metrics_job_run` |
| `0007_metrics_event_log_cursor_index.sql` | Performance index | -- |
| `0008_metrics_alerts.sql` | Alerting system | `metrics_alert` |

### Manual Migration (if needed)

If automatic migration fails, apply manually:

```bash
export CONNINFO="postgresql://user:pass@host:5432/tascade"

for f in 0005_metrics_read_model.sql \
         0006_metrics_incremental_jobs.sql \
         0007_metrics_event_log_cursor_index.sql \
         0008_metrics_alerts.sql; do
    psql "${CONNINFO}" -v ON_ERROR_STOP=1 -1 -f "docs/db/migrations/${f}"
done
```

---

## 4. Staging Deployment

### Step 1: Take a database backup

```bash
pg_dump "${STAGING_DATABASE_URL}" -Fc -f "tascade_staging_$(date +%Y%m%d_%H%M%S).dump"
```

### Step 2: Deploy the application

```bash
# Pull the release branch
git checkout <release-branch>
git pull origin <release-branch>

# Install dependencies
pip install -e ".[dev]"

# Start the application (migrations run automatically on startup)
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Step 3: Verify application startup

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
# Expected: {"status": "ok"}
```

### Step 4: Verify migrations applied

```bash
psql "${CONNINFO}" -c "SELECT version, applied_at FROM schema_migrations ORDER BY version;"
```

Expected output should include all migrations through `0008_metrics_alerts.sql`.

---

## 5. Staging Smoke Tests

### Automated smoke test

```bash
python scripts/smoke_test_metrics.py \
    --base-url http://localhost:8000 \
    --project-id <staging-project-id>
```

The script tests all seven metrics endpoints and verifies:
- HTTP 200 status codes
- `X-API-Version: 1.0` header present
- Response body matches expected structure

Exit code 0 means all tests passed; exit code 1 means one or more failed.

### Manual spot checks

```bash
# Summary
curl -s "http://localhost:8000/v1/metrics/summary?project_id=<id>" \
    -H "Authorization: Bearer ${TASCADE_API_KEY}" | python3 -m json.tool

# Trends
curl -s "http://localhost:8000/v1/metrics/trends?project_id=<id>&metric=cycle_time&start_date=2026-01-01&end_date=2026-02-08&granularity=day" \
    -H "Authorization: Bearer ${TASCADE_API_KEY}" | python3 -m json.tool

# Alerts
curl -s "http://localhost:8000/v1/metrics/alerts?project_id=<id>" \
    -H "Authorization: Bearer ${TASCADE_API_KEY}" | python3 -m json.tool

# Actions
curl -s "http://localhost:8000/v1/metrics/actions?project_id=<id>" \
    -H "Authorization: Bearer ${TASCADE_API_KEY}" | python3 -m json.tool
```

---

## 6. Production Deployment

### Pre-production gate

- [ ] Staging smoke tests all PASS
- [ ] Staging rollback rehearsal completed (see Section 9)
- [ ] On-call team notified and standing by
- [ ] Production database backup taken

### Step 1: Take a production database backup

```bash
pg_dump "${PRODUCTION_DATABASE_URL}" -Fc -f "tascade_prod_$(date +%Y%m%d_%H%M%S).dump"
```

### Step 2: Deploy

Follow the same deployment steps as staging (Section 4, Steps 2-4), targeting
the production environment.

### Step 3: Verify

Run the smoke test against production:

```bash
python scripts/smoke_test_metrics.py \
    --base-url https://tascade.example.com \
    --project-id <production-project-id>
```

---

## 7. Post-deployment Verification

After deploying to either environment, verify:

### Health check

```bash
curl -sf http://localhost:8000/health
# Expected: {"status": "ok"}
```

### Metrics endpoints respond

```bash
# Quick check -- should return 200 with version header
curl -sI "http://localhost:8000/v1/metrics/summary?project_id=<id>" \
    | grep -i "x-api-version"
# Expected: X-API-Version: 1.0
```

### Database schema verification

```bash
psql "${CONNINFO}" -c "\dt metrics_*"
```

Expected tables:
- `metrics_summary`
- `metrics_trend_point`
- `metrics_breakdown_point`
- `metrics_drilldown`
- `metrics_job_checkpoint`
- `metrics_state_transition_counter`
- `metrics_job_run`
- `metrics_alert`

---

## 8. Rollback Procedure

Use the rollback script to revert the metrics subsystem. This drops all
metrics tables and removes migration tracking records so they can be
re-applied later.

### Automated rollback

```bash
# Stop the application first
# Then run rollback:
export TASCADE_DATABASE_URL="postgresql+psycopg://user:pass@host:5432/tascade"

# Interactive (prompts for confirmation)
bash scripts/rollback_metrics.sh

# Non-interactive
bash scripts/rollback_metrics.sh --confirm

# Dry run (shows what would be done, no changes)
bash scripts/rollback_metrics.sh --dry-run
```

### What the rollback does

1. Drops all 8 metrics tables (`metrics_summary`, `metrics_trend_point`,
   `metrics_breakdown_point`, `metrics_drilldown`, `metrics_job_checkpoint`,
   `metrics_state_transition_counter`, `metrics_job_run`, `metrics_alert`)
2. Removes migration records for 0005--0008 from `schema_migrations`
3. Verifies that all metrics tables have been removed

### Manual rollback (if script fails)

```bash
export CONNINFO="postgresql://user:pass@host:5432/tascade"

psql "${CONNINFO}" -v ON_ERROR_STOP=1 <<'SQL'
DROP TABLE IF EXISTS metrics_alert CASCADE;
DROP TABLE IF EXISTS metrics_job_run CASCADE;
DROP TABLE IF EXISTS metrics_state_transition_counter CASCADE;
DROP TABLE IF EXISTS metrics_job_checkpoint CASCADE;
DROP TABLE IF EXISTS metrics_drilldown CASCADE;
DROP TABLE IF EXISTS metrics_breakdown_point CASCADE;
DROP TABLE IF EXISTS metrics_trend_point CASCADE;
DROP TABLE IF EXISTS metrics_summary CASCADE;

DELETE FROM schema_migrations WHERE version IN (
    '0005_metrics_read_model.sql',
    '0006_metrics_incremental_jobs.sql',
    '0007_metrics_event_log_cursor_index.sql',
    '0008_metrics_alerts.sql'
);
SQL
```

### After rollback

- Restart the application. It will start without metrics endpoints still being
  registered (the routes exist but will return empty results or 404 for
  missing projects, which is acceptable).
- If a full removal of endpoint routes is needed, deploy a previous release
  that does not include the P5.M3 code.

---

## 9. Rollback Rehearsal

Perform this rehearsal in staging before every production deployment.

### Procedure

1. Deploy the metrics release to staging (Section 4)
2. Run smoke tests to confirm endpoints work (Section 5)
3. Execute the rollback script:
   ```bash
   bash scripts/rollback_metrics.sh --confirm
   ```
4. Verify all metrics tables are gone:
   ```bash
   psql "${CONNINFO}" -c "\dt metrics_*"
   # Expected: "Did not find any relations."
   ```
5. Restart the application and verify `/health` returns `{"status": "ok"}`
6. Re-deploy and re-run smoke tests to confirm forward migration works after rollback

### Success criteria

- Rollback completes without errors
- All metrics tables are removed after rollback
- Application starts and passes health check after rollback
- Forward migration applies cleanly after rollback

---

## 10. Troubleshooting

### Migration fails on startup

**Symptom**: Application crashes with "Postgres migration failed" error.

**Resolution**:
1. Check `psql` is installed and accessible
2. Verify `TASCADE_DATABASE_URL` is correct
3. Try applying the failing migration manually:
   ```bash
   psql "${CONNINFO}" -v ON_ERROR_STOP=1 -1 -f docs/db/migrations/<failing_file>.sql
   ```
4. Check for conflicting table/column names with `\dt` and `\d <table>`

### Smoke test reports FAIL

**Symptom**: `smoke_test_metrics.py` exits with code 1.

**Resolution**:
1. Check the specific endpoint(s) that failed
2. Verify the project ID exists: `curl http://localhost:8000/v1/projects/<id>`
3. Check application logs for error details
4. If auth is enabled, ensure the request includes proper Authorization header

### Rollback script fails

**Symptom**: `rollback_metrics.sh` exits with an error.

**Resolution**:
1. Verify `TASCADE_DATABASE_URL` is set
2. Verify `psql` is installed: `which psql`
3. Try the manual rollback SQL (Section 8)
4. Check database connectivity: `psql "${CONNINFO}" -c "SELECT 1"`

### Tables already exist error during migration

**Symptom**: Migration fails because metrics tables already exist.

**Resolution**:
1. Run the rollback script to clean up partial state:
   ```bash
   bash scripts/rollback_metrics.sh --confirm
   ```
2. Restart the application to re-apply migrations from a clean state
