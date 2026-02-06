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
