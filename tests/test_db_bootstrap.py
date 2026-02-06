import pytest
from sqlalchemy import create_engine

import app.db as db


def test_verify_schema_detects_missing_required_column():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE project (id TEXT PRIMARY KEY)")

    with pytest.raises(RuntimeError, match=r"project\.name"):
        db.verify_schema(engine, {"project": {"id", "name"}})


def test_init_db_calls_postgres_migration_path_for_non_sqlite(monkeypatch):
    called = {"migrate": False, "create_all": False, "verify": False}

    monkeypatch.setattr(db, "DATABASE_URL", "postgresql+psycopg://x:y@localhost:5432/tascade")
    monkeypatch.setattr(db, "_run_postgres_migrations", lambda engine: called.__setitem__("migrate", True))
    monkeypatch.setattr(db, "verify_schema", lambda engine, required=None: called.__setitem__("verify", True))
    monkeypatch.setattr(db.Base.metadata, "create_all", lambda bind=None: called.__setitem__("create_all", True))

    db.init_db()

    assert called["migrate"] is True
    assert called["verify"] is True
    assert called["create_all"] is False


def test_init_db_uses_sqlite_create_all_path(monkeypatch):
    called = {"migrate": False, "create_all": False, "verify": False}

    monkeypatch.setattr(db, "DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setattr(db, "_run_postgres_migrations", lambda engine: called.__setitem__("migrate", True))
    monkeypatch.setattr(db, "verify_schema", lambda engine, required=None: called.__setitem__("verify", True))
    monkeypatch.setattr(db.Base.metadata, "create_all", lambda bind=None: called.__setitem__("create_all", True))

    db.init_db()

    assert called["create_all"] is True
    assert called["verify"] is True
    assert called["migrate"] is False


def test_run_postgres_migrations_applies_only_pending_files(monkeypatch):
    calls: dict[str, list] = {"psql": [], "recorded": []}
    monkeypatch.setattr(db, "DATABASE_URL", "postgresql+psycopg://x:y@localhost:5432/tascade")
    monkeypatch.setattr(db, "_migration_sql_files", lambda: [db.Path("/tmp/0001_init.sql"), db.Path("/tmp/0002_extra.sql")])
    monkeypatch.setattr(db, "_ensure_schema_migrations_table", lambda conninfo: None)
    monkeypatch.setattr(db, "_applied_migration_versions", lambda conninfo: {"0001_init.sql"})
    monkeypatch.setattr(db, "_database_looks_initialized", lambda engine: False)
    monkeypatch.setattr(db, "_record_migration_version", lambda conninfo, version: calls["recorded"].append(version))
    monkeypatch.setattr(db, "_run_psql", lambda command: calls["psql"].append(command))

    db._run_postgres_migrations(db.ENGINE)

    assert len(calls["psql"]) == 1
    assert calls["psql"][0][-2:] == ["-f", "/tmp/0002_extra.sql"]
    assert calls["recorded"] == ["0002_extra.sql"]


def test_run_postgres_migrations_baselines_existing_schema(monkeypatch):
    calls: dict[str, list] = {"psql": [], "recorded": []}
    monkeypatch.setattr(db, "DATABASE_URL", "postgresql+psycopg://x:y@localhost:5432/tascade")
    monkeypatch.setattr(db, "_migration_sql_files", lambda: [db.Path("/tmp/0001_init.sql"), db.Path("/tmp/0002_extra.sql")])
    monkeypatch.setattr(db, "_ensure_schema_migrations_table", lambda conninfo: None)
    monkeypatch.setattr(db, "_applied_migration_versions", lambda conninfo: set())
    monkeypatch.setattr(db, "_database_looks_initialized", lambda engine: True)
    monkeypatch.setattr(db, "_record_migration_version", lambda conninfo, version: calls["recorded"].append(version))
    monkeypatch.setattr(db, "_run_psql", lambda command: calls["psql"].append(command))

    db._run_postgres_migrations(db.ENGINE)

    assert len(calls["psql"]) == 1
    assert calls["psql"][0][-2:] == ["-f", "/tmp/0002_extra.sql"]
    assert calls["recorded"] == ["0001_init.sql", "0002_extra.sql"]
