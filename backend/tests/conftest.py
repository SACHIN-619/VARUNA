import sys
import os
import pytest

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# SAFETY: never run the test-suite against the database configured in backend/.env
# (which may be a shared / production Neon instance). Tests always use an isolated
# SQLite file unless VARUNA_TEST_DATABASE_URL is set explicitly.
os.environ["DATABASE_URL"] = os.environ.get(
    "VARUNA_TEST_DATABASE_URL", "sqlite:///" + os.path.join(backend_dir, "varuna_test.db").replace("\\", "/")
)
os.environ.setdefault("ENABLE_GROK", "false")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.db.seed import init_db  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    init_db()


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
