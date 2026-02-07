from __future__ import annotations

import os
import subprocess
from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base


DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/tascade"


def _database_url() -> str:
    return os.getenv("TASCADE_DATABASE_URL", DEFAULT_DATABASE_URL)


def _engine_kwargs(url: str) -> dict:
    if url.startswith("sqlite"):
        kwargs: dict = {"connect_args": {"check_same_thread": False}}
        if ":memory:" in url:
            kwargs["poolclass"] = StaticPool
        return kwargs
    return {"pool_pre_ping": True}


DATABASE_URL = _database_url()
ENGINE = create_engine(DATABASE_URL, future=True, **_engine_kwargs(DATABASE_URL))
SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False, expire_on_commit=False)


REQUIRED_SCHEMA: dict[str, set[str]] = {
    "project": {"id", "name", "status", "created_at", "updated_at"},
    "task": {
        "id",
        "project_id",
        "title",
        "state",
        "priority",
        "work_spec",
        "task_class",
        "version",
        "created_at",
        "updated_at",
    },
    "dependency_edge": {"id", "project_id", "from_task_id", "to_task_id", "unlock_on", "created_at"},
    "lease": {
        "id",
        "project_id",
        "task_id",
        "agent_id",
        "token",
        "status",
        "expires_at",
        "heartbeat_at",
        "fencing_counter",
        "created_at",
    },
    "task_reservation": {
        "id",
        "project_id",
        "task_id",
        "assignee_agent_id",
        "mode",
        "status",
        "ttl_seconds",
        "created_by",
        "created_at",
        "expires_at",
    },
    "plan_change_set": {
        "id",
        "project_id",
        "base_plan_version",
        "target_plan_version",
        "status",
        "operations",
        "impact_preview",
        "created_by",
        "created_at",
    },
    "plan_version": {
        "id",
        "project_id",
        "version_number",
        "change_set_id",
        "summary",
        "created_by",
        "created_at",
    },
    "task_execution_snapshot": {
        "id",
        "project_id",
        "task_id",
        "lease_id",
        "captured_plan_version",
        "work_spec_hash",
        "work_spec_payload",
        "captured_by",
        "captured_at",
    },
    "artifact": {
        "id",
        "project_id",
        "task_id",
        "agent_id",
        "branch",
        "commit_sha",
        "check_suite_ref",
        "check_status",
        "touched_files",
        "created_at",
    },
    "integration_attempt": {
        "id",
        "project_id",
        "task_id",
        "base_sha",
        "head_sha",
        "result",
        "diagnostics",
        "started_at",
        "ended_at",
    },
    "gate_rule": {
        "id",
        "project_id",
        "name",
        "scope",
        "conditions",
        "required_evidence",
        "required_reviewer_roles",
        "is_active",
        "created_at",
        "updated_at",
    },
    "gate_decision": {
        "id",
        "project_id",
        "gate_rule_id",
        "task_id",
        "phase_id",
        "outcome",
        "actor_id",
        "reason",
        "evidence_refs",
        "created_at",
    },
    "gate_candidate_link": {
        "id",
        "project_id",
        "gate_task_id",
        "candidate_task_id",
        "candidate_order",
        "created_at",
    },
}


def _is_sqlite_url(url: str) -> bool:
    return url.startswith("sqlite")


def _migrations_dir() -> Path:
    configured = os.getenv("TASCADE_DB_MIGRATIONS_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[1] / "docs" / "db" / "migrations"


def _migration_sql_files() -> list[Path]:
    single = os.getenv("TASCADE_DB_MIGRATION_SQL")
    if single:
        migration_file = Path(single).expanduser().resolve()
        if not migration_file.is_file():
            raise RuntimeError(f"Migration SQL file not found: {migration_file}")
        return [migration_file]

    migrations_dir = _migrations_dir()
    if not migrations_dir.is_dir():
        raise RuntimeError(f"Migrations directory not found: {migrations_dir}")

    migration_files = sorted(path.resolve() for path in migrations_dir.glob("*.sql"))
    if not migration_files:
        raise RuntimeError(f"No SQL migration files found in: {migrations_dir}")
    return migration_files


def _postgres_conninfo_for_psql(database_url: str) -> str:
    parsed = make_url(database_url)
    if not parsed.drivername.startswith("postgresql"):
        raise RuntimeError(f"Non-Postgres URL cannot be migrated with psql: {database_url}")
    conninfo = parsed.set(drivername="postgresql")
    return conninfo.render_as_string(hide_password=False)


def _run_psql(command: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("psql is required to initialize PostgreSQL schema") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        raise RuntimeError(f"Postgres migration failed: {stderr}") from exc


def _ensure_schema_migrations_table(conninfo: str) -> None:
    _run_psql(
        [
            "psql",
            conninfo,
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            (
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "version TEXT PRIMARY KEY, "
                "applied_at TIMESTAMPTZ NOT NULL DEFAULT now()"
                ")"
            ),
        ]
    )


def _applied_migration_versions(conninfo: str) -> set[str]:
    result = _run_psql(
        [
            "psql",
            conninfo,
            "-v",
            "ON_ERROR_STOP=1",
            "-t",
            "-A",
            "-c",
            "SELECT version FROM schema_migrations ORDER BY version",
        ]
    )
    return {line.strip() for line in (result.stdout or "").splitlines() if line.strip()}


def _record_migration_version(conninfo: str, version: str) -> None:
    escaped_version = version.replace("'", "''")
    _run_psql(
        [
            "psql",
            conninfo,
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            (
                "INSERT INTO schema_migrations (version) "
                f"VALUES ('{escaped_version}') "
                "ON CONFLICT (version) DO NOTHING"
            ),
        ]
    )


def _database_looks_initialized(engine: Engine) -> bool:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    return "project" in existing_tables


def _run_postgres_migrations(engine: Engine) -> None:
    migration_files = _migration_sql_files()
    conninfo = _postgres_conninfo_for_psql(DATABASE_URL)
    _ensure_schema_migrations_table(conninfo)
    applied_versions = _applied_migration_versions(conninfo)

    # Backfill tracking for legacy DBs initialized before schema_migrations existed.
    # Only baseline the earliest migration, then apply remaining pending files.
    if not applied_versions and _database_looks_initialized(engine):
        baseline_version = migration_files[0].name
        _record_migration_version(conninfo, baseline_version)
        applied_versions.add(baseline_version)

    for migration_file in migration_files:
        version = migration_file.name
        if version in applied_versions:
            continue
        _run_psql(
            [
                "psql",
                conninfo,
                "-v",
                "ON_ERROR_STOP=1",
                "-1",
                "-f",
                str(migration_file),
            ]
        )
        _record_migration_version(conninfo, version)


def verify_schema(engine: Engine, required: dict[str, set[str]] | None = None) -> None:
    inspector = inspect(engine)
    required_schema = required or REQUIRED_SCHEMA
    existing_tables = set(inspector.get_table_names())
    missing_columns: list[str] = []
    for table_name, required_columns in required_schema.items():
        if table_name not in existing_tables:
            missing_columns.extend(f"{table_name}.{column}" for column in sorted(required_columns))
            continue
        existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
        for required_column in sorted(required_columns):
            if required_column not in existing_columns:
                missing_columns.append(f"{table_name}.{required_column}")
    if missing_columns:
        detail = ", ".join(missing_columns)
        raise RuntimeError(f"Schema verification failed; missing columns: {detail}")


def init_db() -> None:
    if _is_sqlite_url(DATABASE_URL):
        Base.metadata.create_all(bind=ENGINE)
    else:
        _run_postgres_migrations(ENGINE)
    verify_schema(ENGINE)


def reset_db() -> None:
    Base.metadata.drop_all(bind=ENGINE)
    Base.metadata.create_all(bind=ENGINE)
