import os
from pathlib import Path

import pytest

TEST_DB = Path(__file__).with_name("test.db")
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["JTA_DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["JTA_AUTO_SEED"] = "true"

from fastapi.testclient import TestClient  # noqa: E402

from app.db.session import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed.sample_data import seed_sample_data  # noqa: E402


Base.metadata.create_all(bind=engine)
with SessionLocal() as db:
    seed_sample_data(db)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
