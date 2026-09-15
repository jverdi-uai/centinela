import os
from pathlib import Path

os.environ["MOCK_MODE"] = "true"
os.environ["SHADOW_MODE"] = "false"
os.environ["DATABASE_URL"] = "sqlite:///data/centinela-test.db"

import pytest
from sqlalchemy import delete
from sqlalchemy.orm import Session

from centinela.db import FeedbackRecord, TraceRecord, VectorRecord, engine, init_db


@pytest.fixture(autouse=True)
def clean_database():
    init_db()
    with Session(engine) as session:
        session.execute(delete(FeedbackRecord))
        session.execute(delete(TraceRecord))
        session.execute(delete(VectorRecord))
        session.commit()
    yield


@pytest.fixture(scope="session", autouse=True)
def remove_test_database_at_end():
    yield
    engine.dispose()
    path = Path("data/centinela-test.db")
    if path.exists():
        path.unlink()

