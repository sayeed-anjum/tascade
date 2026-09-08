import os
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("TASCADE_DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("TASCADE_AUTH_DISABLED", "1")

from app.store import STORE


@pytest.fixture(autouse=True)
def reset_store():
    STORE.reset()
    yield


@pytest.fixture(autouse=True)
def isolated_cli_config(monkeypatch, tmp_path):
    """Keep the CLI's config resolution out of the developer's environment.

    Without this, a real TASCADE_API_KEY in the environment is sent as an
    Authorization header by every CLI test, and a real
    ~/.config/tascade/config.toml changes the endpoint under test.
    """
    from app.cli import config as cli_config

    monkeypatch.delenv("TASCADE_URL", raising=False)
    monkeypatch.delenv("TASCADE_API_KEY", raising=False)
    monkeypatch.setattr(cli_config, "DEFAULT_CONFIG_PATH", tmp_path / "absent-config.toml")
    yield
