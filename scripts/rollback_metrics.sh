#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# rollback_metrics.sh -- Rollback Tascade metrics subsystem
#
# Reverts metrics-related database migrations (0005-0008) and leaves the
# application in its pre-metrics state.  Safe to run multiple times
# (idempotent).
#
# Prerequisites:
#   - TASCADE_DATABASE_URL must point to the target PostgreSQL database
#   - psql must be available on PATH
#   - The operator should have stopped the application before running this
#
# Usage:
#   scripts/rollback_metrics.sh              # interactive (prompts for confirmation)
#   scripts/rollback_metrics.sh --confirm    # non-interactive
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATABASE_URL="${TASCADE_DATABASE_URL:-}"
DRY_RUN="${DRY_RUN:-}"

# Metrics migrations in reverse order (newest first)
METRICS_MIGRATIONS=(
    "0008_metrics_alerts.sql"
    "0007_metrics_event_log_cursor_index.sql"
    "0006_metrics_incremental_jobs.sql"
    "0005_metrics_read_model.sql"
)

# Tables introduced by metrics migrations
METRICS_TABLES=(
    "metrics_alert"
    "metrics_job_run"
    "metrics_state_transition_counter"
    "metrics_job_checkpoint"
    "metrics_drilldown"
    "metrics_breakdown_point"
    "metrics_trend_point"
    "metrics_summary"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

log()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
info() { log "INFO  $*"; }
warn() { log "WARN  $*"; }
err()  { log "ERROR $*" >&2; }

die() {
    err "$@"
    exit 1
}

require_psql() {
    if ! command -v psql >/dev/null 2>&1; then
        die "psql is required but not found on PATH"
    fi
}

require_database_url() {
    if [[ -z "${DATABASE_URL}" ]]; then
        die "TASCADE_DATABASE_URL is not set. Export it before running this script."
    fi
}

# Convert SQLAlchemy-style URL to psql-compatible conninfo.
# postgresql+psycopg://user:pass@host:port/db -> postgresql://user:pass@host:port/db
conninfo_from_url() {
    echo "${DATABASE_URL}" | sed -E 's|^postgresql\+[a-z]+://|postgresql://|'
}

run_sql() {
    local sql="$1"
    local conninfo
    conninfo="$(conninfo_from_url)"
    if [[ -n "${DRY_RUN}" ]]; then
        info "[DRY RUN] Would execute: ${sql}"
        return 0
    fi
    psql "${conninfo}" -v ON_ERROR_STOP=1 -t -A -c "${sql}" 2>/dev/null || true
}

run_sql_strict() {
    local sql="$1"
    local conninfo
    conninfo="$(conninfo_from_url)"
    if [[ -n "${DRY_RUN}" ]]; then
        info "[DRY RUN] Would execute: ${sql}"
        return 0
    fi
    psql "${conninfo}" -v ON_ERROR_STOP=1 -t -A -c "${sql}"
}

# ---------------------------------------------------------------------------
# Rollback steps
# ---------------------------------------------------------------------------

drop_metrics_tables() {
    info "Dropping metrics tables (if they exist)..."
    for table in "${METRICS_TABLES[@]}"; do
        info "  DROP TABLE IF EXISTS ${table}"
        run_sql "DROP TABLE IF EXISTS ${table} CASCADE;"
    done
}

remove_migration_records() {
    info "Removing metrics migration records from schema_migrations..."
    # Check if schema_migrations table exists first
    local has_table
    has_table="$(run_sql "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'schema_migrations');" | tr -d '[:space:]')"

    if [[ "${has_table}" != "t" ]]; then
        info "  schema_migrations table does not exist -- nothing to clean"
        return 0
    fi

    for migration in "${METRICS_MIGRATIONS[@]}"; do
        info "  DELETE ${migration}"
        run_sql "DELETE FROM schema_migrations WHERE version = '${migration}';"
    done
}

verify_rollback() {
    info "Verifying rollback..."
    local remaining=0
    for table in "${METRICS_TABLES[@]}"; do
        local exists
        exists="$(run_sql "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '${table}');" | tr -d '[:space:]')"
        if [[ "${exists}" == "t" ]]; then
            warn "  Table ${table} still exists after rollback!"
            remaining=$((remaining + 1))
        fi
    done

    if [[ ${remaining} -gt 0 ]]; then
        warn "${remaining} metrics table(s) still present -- manual cleanup may be needed"
        return 1
    fi

    info "Rollback verification passed -- all metrics tables removed"
    return 0
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
    local auto_confirm=false

    for arg in "$@"; do
        case "${arg}" in
            --confirm) auto_confirm=true ;;
            --dry-run) DRY_RUN=1 ;;
            --help|-h)
                echo "Usage: $0 [--confirm] [--dry-run]"
                echo ""
                echo "Rolls back Tascade metrics migrations (0005-0008)."
                echo ""
                echo "Options:"
                echo "  --confirm   Skip interactive confirmation prompt"
                echo "  --dry-run   Print SQL that would be executed without running it"
                echo "  --help      Show this help message"
                exit 0
                ;;
            *)
                die "Unknown option: ${arg}"
                ;;
        esac
    done

    require_psql
    require_database_url

    info "Tascade Metrics Rollback"
    info "Database: ${DATABASE_URL//:*@/:***@}"  # mask password
    info ""
    info "This will:"
    info "  1. Drop all metrics tables (${#METRICS_TABLES[@]} tables)"
    info "  2. Remove migration records (${#METRICS_MIGRATIONS[@]} migrations)"
    info ""

    if [[ "${auto_confirm}" != "true" && -z "${DRY_RUN}" ]]; then
        printf "Continue? [y/N] "
        read -r answer
        if [[ "${answer}" != "y" && "${answer}" != "Y" ]]; then
            info "Aborted by operator."
            exit 0
        fi
    fi

    drop_metrics_tables
    remove_migration_records

    if [[ -z "${DRY_RUN}" ]]; then
        verify_rollback
    fi

    info "Rollback complete."
}

main "$@"
