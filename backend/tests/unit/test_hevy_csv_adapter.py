from datetime import datetime
from pathlib import Path

import pytest

from app.adapters.hevy_csv_adapter import HevyCsvAdapter

# Realistic Hevy export incl. edge cases seen in real data: a cardio set
# (no weight/reps, has distance/duration), a dropset, and an exercise note.
_FIXTURE = Path(__file__).parent.parent / "fixtures" / "hevy_sample.csv"


def _sample_csv() -> str:
    return _FIXTURE.read_text(encoding="utf-8")


def test_groups_rows_into_workouts_by_start_time() -> None:
    workouts = HevyCsvAdapter(_sample_csv()).fetch()

    assert len(workouts) == 2
    assert {w.title for w in workouts} == {"Cardio", "Upper"}


def test_workout_level_fields() -> None:
    upper = next(w for w in HevyCsvAdapter(_sample_csv()).fetch() if w.title == "Upper")

    assert upper.source == "hevy_csv"
    assert upper.external_id is None
    assert upper.started_at == datetime(2026, 7, 4, 17, 0)
    assert upper.ended_at == datetime(2026, 7, 4, 18, 30)
    assert upper.notes == "@ Home"  # from the description column
    assert len(upper.sets) == 3


def test_cardio_set_has_null_weight_reps_and_converts_distance_to_meters() -> None:
    cardio = next(w for w in HevyCsvAdapter(_sample_csv()).fetch() if w.title == "Cardio")
    treadmill = next(s for s in cardio.sets if s.exercise_name == "Treadmill")

    assert treadmill.weight_kg is None
    assert treadmill.reps is None
    assert treadmill.distance_m == 3000.0  # 3 km -> 3000 m
    assert treadmill.duration_s == 2700


def test_set_fields_parsed_including_slug_type_and_notes() -> None:
    upper = next(w for w in HevyCsvAdapter(_sample_csv()).fetch() if w.title == "Upper")

    dropset = next(s for s in upper.sets if s.set_index == 1)
    assert dropset.set_type == "dropset"
    assert dropset.weight_kg == 50.0
    assert dropset.exercise_slug == "bench_press_barbell"

    row = next(s for s in upper.sets if s.exercise_name == "T Bar Row")
    assert row.notes == "kelso"


def test_content_hash_is_deterministic() -> None:
    hashes_a = sorted(w.content_hash for w in HevyCsvAdapter(_sample_csv()).fetch())
    hashes_b = sorted(w.content_hash for w in HevyCsvAdapter(_sample_csv()).fetch())

    assert hashes_a == hashes_b


def test_content_hash_differs_when_a_rep_changes() -> None:
    original = next(w for w in HevyCsvAdapter(_sample_csv()).fetch() if w.title == "Upper")
    edited_csv = _sample_csv().replace('"normal",60,10', '"normal",60,11')  # 10 -> 11 reps
    edited = next(w for w in HevyCsvAdapter(edited_csv).fetch() if w.title == "Upper")

    assert original.content_hash != edited.content_hash


def test_missing_required_column_raises() -> None:
    bad_csv = '"title","start_time"\n"Upper","4 Jul 2026, 17:00"'

    with pytest.raises(ValueError, match="missing required Hevy columns"):
        HevyCsvAdapter(bad_csv).fetch()
