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
}


def _is_sqlite_url(url: str) -> bool:
    return url.startswith("sqlite")


def _migration_sql_path() -> Path:
    configured = os.getenv("TASCADE_DB_MIGRATION_SQL")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[1] / "docs" / "db" / "migrations" / "0001_init.sql"


def _postgres_conninfo_for_psql(database_url: str) -> str:
    parsed = make_url(database_url)
    if not parsed.drivername.startswith("postgresql"):
        raise RuntimeError(f"Non-Postgres URL cannot be migrated with psql: {database_url}")
    conninfo = parsed.set(drivername="postgresql")
    return conninfo.render_as_string(hide_password=False)


def _run_postgres_migrations(engine: Engine) -> None:
    del engine
    migration_sql = _migration_sql_path()
    if not migration_sql.is_file():
        raise RuntimeError(f"Migration SQL file not found: {migration_sql}")

    conninfo = _postgres_conninfo_for_psql(DATABASE_URL)
    command = ["psql", conninfo, "-v", "ON_ERROR_STOP=1", "-f", str(migration_sql)]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("psql is required to initialize PostgreSQL schema") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        raise RuntimeError(f"Postgres migration failed: {stderr}") from exc


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
