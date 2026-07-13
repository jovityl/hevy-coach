import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.security import CurrentUser, get_current_user
from app.main import app

_FIXTURE = Path(__file__).parent.parent / "fixtures" / "hevy_sample.csv"


@pytest.fixture
def as_user() -> Iterator[uuid.UUID]:
    """Override auth with a fresh random user. Isolation is via the unique
    user_id (every query is user-scoped), so no cleanup is needed — the test
    database is disposable and rows never collide across runs."""
    user_id = uuid.uuid4()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=str(user_id), is_anonymous=True
    )
    try:
        yield user_id
    finally:
        app.dependency_overrides.clear()


def _upload(client: TestClient) -> dict[str, object]:
    files = {"file": ("workouts.csv", _FIXTURE.read_bytes(), "text/csv")}
    response = client.post("/ingest/csv", files=files)
    assert response.status_code == 200, response.text
    return response.json()


def test_ingest_inserts_workouts_then_dedups_on_reupload(as_user: uuid.UUID) -> None:
    client = TestClient(app)

    first = _upload(client)
    assert first["inserted"] == 2
    assert first["skipped_duplicates"] == 0
    assert first["unmapped_exercises"] == []  # all fixture exercises are in the seed

    second = _upload(client)
    assert second["inserted"] == 0
    assert second["skipped_duplicates"] == 2


def test_ingest_requires_auth() -> None:
    client = TestClient(app)
    files = {"file": ("workouts.csv", b"anything", "text/csv")}

    response = client.post("/ingest/csv", files=files)

    assert response.status_code in (401, 403)


def test_ingest_rejects_csv_missing_columns(as_user: uuid.UUID) -> None:
    client = TestClient(app)
    files = {"file": ("bad.csv", b'"title","start_time"\n"x","1 Jan 2026, 10:00"', "text/csv")}

    response = client.post("/ingest/csv", files=files)

    assert response.status_code == 400
    assert "missing required Hevy columns" in response.json()["detail"]
