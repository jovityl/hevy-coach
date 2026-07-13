import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

_FIXTURE = Path(__file__).parent.parent / "fixtures" / "hevy_sample.csv"


def _ingest_fixture(client: TestClient) -> None:
    files = {"file": ("workouts.csv", _FIXTURE.read_bytes(), "text/csv")}
    response = client.post("/ingest/csv", files=files)
    assert response.status_code == 200, response.text


def test_volume_reflects_ingested_data(as_user: uuid.UUID) -> None:
    client = TestClient(app)
    _ingest_fixture(client)

    response = client.get("/metrics/volume")

    assert response.status_code == 200
    volumes = response.json()
    # Fixture has a chest bench workout -> at least one chest hard set.
    chest = [v for v in volumes if v["muscle"] == "chest"]
    assert chest
    assert chest[0]["hard_sets"] >= 1


def test_records_for_a_known_exercise(as_user: uuid.UUID) -> None:
    client = TestClient(app)
    _ingest_fixture(client)

    response = client.get("/metrics/records", params={"exercise_slug": "bench_press_barbell"})

    assert response.status_code == 200
    body = response.json()
    assert body["max_weight_kg"] == 60.0  # heaviest bench set in the fixture
    assert body["best_est_1rm"] is not None


def test_metrics_require_auth() -> None:
    client = TestClient(app)
    assert client.get("/metrics/volume").status_code in (401, 403)


def test_metrics_are_isolated_per_user(as_user: uuid.UUID) -> None:
    """A fresh user with no ingested data gets empty metrics — proof the
    user_id scoping actually isolates data."""
    client = TestClient(app)

    response = client.get("/metrics/volume")

    assert response.status_code == 200
    assert response.json() == []
