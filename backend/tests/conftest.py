"""Shared pytest fixtures for the HRECOS backend.

Environment variables must be set *before* importing ``app``:

* ``DATABASE_URL``      — point at a throwaway SQLite file (``db.py`` reads it
  at import time, otherwise the app would create ``backend/hrecos.db``).
* ``DISABLE_SCHEDULER`` — keep APScheduler's network-polling jobs out of tests.
"""

import os
import tempfile
from pathlib import Path

_TEST_DIR = tempfile.mkdtemp(prefix="hrecos-test-")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{Path(_TEST_DIR) / 'test.db'}"
os.environ["DISABLE_SCHEDULER"] = "1"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    """TestClient with the app's lifespan (table creation) executed once."""
    with TestClient(app) as test_client:
        yield test_client
