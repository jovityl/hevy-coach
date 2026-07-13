from datetime import date, datetime

import pytest

from app.domain.metrics import (
    SetRecord,
    detect_plateau,
    estimated_1rm,
    is_1rm_estimate_reliable,
    personal_records,
    true_rep_capacity,
    weekly_volume,
)


def _set(
    *,
    slug: str = "bench_press_barbell",
    muscle: str | None = "chest",
    set_type: str = "normal",
    weight: float | None = None,
    reps: int | None = None,
    at: datetime,
) -> SetRecord:
    return SetRecord(
        exercise_slug=slug,
        exercise_name=slug,
        primary_muscle=muscle,
        set_type=set_type,
        weight_kg=weight,
        reps=reps,
        performed_at=at,
    )


# --- estimated_1rm ---


def test_est_1rm_at_one_rep_is_the_logged_weight() -> None:
    assert estimated_1rm(100.0, 1) == 100.0


def test_est_1rm_uses_epley_above_one_rep() -> None:
    # 100 * (1 + 5/30) = 116.666...
    assert estimated_1rm(100.0, 5) == pytest.approx(116.6667, abs=1e-3)


def test_est_1rm_is_none_without_weight_or_reps() -> None:
    assert estimated_1rm(None, 5) is None
    assert estimated_1rm(100.0, None) is None
    assert estimated_1rm(100.0, 0) is None


def test_1rm_reliability_flag() -> None:
    assert is_1rm_estimate_reliable(8) is True
    assert is_1rm_estimate_reliable(15) is False
    assert is_1rm_estimate_reliable(None) is False


# --- weekly_volume ---


def test_weekly_volume_counts_hard_sets_and_tonnage_per_muscle() -> None:
    # Same ISO week (Mon 6 Jul 2026 .. Sun): two chest working sets.
    sets = [
        _set(weight=60, reps=10, at=datetime(2026, 7, 6, 18, 0)),  # 600
        _set(weight=50, reps=8, at=datetime(2026, 7, 8, 18, 0)),  # 400
    ]
    result = weekly_volume(sets)

    assert len(result) == 1
    vol = result[0]
    assert vol.week_start == date(2026, 7, 6)  # Monday
    assert vol.muscle == "chest"
    assert vol.hard_sets == 2
    assert vol.tonnage_kg == pytest.approx(1000.0)


def test_weekly_volume_excludes_warmups_and_unmapped() -> None:
    sets = [
        _set(weight=60, reps=10, at=datetime(2026, 7, 6, 18, 0)),  # counts
        _set(weight=20, reps=10, set_type="warmup", at=datetime(2026, 7, 6, 18, 0)),  # excluded
        _set(muscle=None, weight=40, reps=10, at=datetime(2026, 7, 6, 18, 0)),  # unmapped, excluded
    ]
    result = weekly_volume(sets)

    assert len(result) == 1
    assert result[0].hard_sets == 1


# --- true_rep_capacity ---


def test_true_rep_capacity_returns_max_logged_reps_at_that_weight() -> None:
    sets = [
        _set(slug="weighted_pull_up", weight=40, reps=2, at=datetime(2026, 7, 1)),
        _set(slug="weighted_pull_up", weight=40, reps=1, at=datetime(2026, 7, 3)),
        _set(slug="weighted_pull_up", weight=30, reps=8, at=datetime(2026, 7, 5)),
    ]
    # The Gemini-failure case: true capacity at 40kg is 2, not a prescribed 3-5.
    assert true_rep_capacity(sets, "weighted_pull_up", 40.0) == 2


def test_true_rep_capacity_is_none_when_weight_never_logged() -> None:
    sets = [_set(slug="weighted_pull_up", weight=40, reps=2, at=datetime(2026, 7, 1))]
    assert true_rep_capacity(sets, "weighted_pull_up", 100.0) is None


# --- personal_records ---


def test_personal_records() -> None:
    sets = [
        _set(weight=100, reps=1, at=datetime(2026, 7, 1)),  # est 1rm 100
        _set(weight=80, reps=8, at=datetime(2026, 7, 3)),  # est 1rm 101.33
        _set(weight=60, reps=12, at=datetime(2026, 7, 5)),  # est 1rm 84
    ]
    pr = personal_records(sets, "bench_press_barbell")

    assert pr.max_weight_kg == 100
    assert pr.max_reps == 12
    assert pr.best_est_1rm == pytest.approx(80 * (1 + 8 / 30))  # the 80x8 set wins


# --- detect_plateau ---


def _progression_sets(est_1rm_weights: list[float]) -> list[SetRecord]:
    # one 1-rep set per session so est-1RM == weight, on distinct dates
    return [
        _set(weight=w, reps=1, at=datetime(2026, 6, day, 18, 0))
        for day, w in enumerate(est_1rm_weights, start=1)
    ]


def test_plateau_insufficient_data() -> None:
    result = detect_plateau(_progression_sets([100, 102]), "bench_press_barbell")
    assert result.status == "insufficient_data"


def test_plateau_progressing() -> None:
    result = detect_plateau(_progression_sets([100, 102, 104, 106]), "bench_press_barbell")
    assert result.status == "progressing"


def test_plateau_stalled() -> None:
    # never improves >=1% above the window's start (100)
    result = detect_plateau(_progression_sets([100, 100, 100.5, 100]), "bench_press_barbell")
    assert result.status == "stalled"


def test_plateau_regressing() -> None:
    result = detect_plateau(_progression_sets([100, 99, 98, 97]), "bench_press_barbell")
    assert result.status == "regressing"


def test_plateau_excludes_deload_dates() -> None:
    # The deload is the latest session: unfiltered it reads as regression;
    # excluding it reveals the underlying progression.
    sets = _progression_sets([100, 102, 104, 106, 70])  # day 5 (2026-06-05) is the deload

    unfiltered = detect_plateau(sets, "bench_press_barbell")
    assert unfiltered.status == "regressing"

    filtered = detect_plateau(
        sets, "bench_press_barbell", excluded_dates=frozenset({date(2026, 6, 5)})
    )
    assert filtered.status == "progressing"
