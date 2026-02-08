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
