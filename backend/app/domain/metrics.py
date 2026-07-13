"""Pure, deterministic training metrics — the ground-truth layer.

Every number the coach ever states about the user's training comes from here
(computed in plain Python/SQL), never from an LLM. These functions are pure:
same input -> same output, no I/O, no DB — so they're trivially unit-testable,
which is the whole point (§9 Phase 8). The service layer projects DB rows into
`SetRecord`s and calls these.

Language discipline (§6.5): "estimate" is used for formula-derived values like
est-1RM; only directly-logged facts (max weight, rep counts) are "verified".
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta

# Epley (1RM = w * (1 + reps/30)) is reasonable up to ~10 reps; above that the
# estimate degrades and should be flagged low-confidence (§6.5).
_EPLEY_MAX_TRUSTED_REPS = 10

# Plateau thresholds (§6.6).
_PLATEAU_WINDOW = 4
_PLATEAU_IMPROVEMENT_THRESHOLD = 0.01  # 1%


@dataclass(frozen=True)
class SetRecord:
    """Minimal projection of a logged set needed for metrics. `primary_muscle`
    is None when the exercise is unmapped (surfaced separately, never counted
    into volume)."""

    exercise_slug: str
    exercise_name: str
    primary_muscle: str | None
    set_type: str
    weight_kg: float | None
    reps: int | None
    performed_at: datetime


@dataclass(frozen=True)
class WeeklyMuscleVolume:
    week_start: date  # Monday of the ISO week
    muscle: str
    hard_sets: int
    tonnage_kg: float


@dataclass(frozen=True)
class ExerciseSessionPoint:
    session_date: date
    top_weight_kg: float | None
    best_est_1rm: float | None


@dataclass(frozen=True)
class PersonalRecords:
    max_weight_kg: float | None
    max_reps: int | None
    best_est_1rm: float | None


@dataclass(frozen=True)
class PlateauResult:
    # "progressing" | "stalled" | "regressing" | "insufficient_data"
    status: str
    sessions_analyzed: int


def estimated_1rm(weight_kg: float | None, reps: int | None) -> float | None:
    """Epley one-rep-max *estimate*. At 1 rep the logged weight is the true
    1RM. Returns None when weight/reps are missing."""
    if weight_kg is None or reps is None or reps < 1:
        return None
    if reps == 1:
        return weight_kg
    return weight_kg * (1 + reps / 30)


def is_1rm_estimate_reliable(reps: int | None) -> bool:
    """Whether an Epley estimate at this rep count is trustworthy (§6.5)."""
    return reps is not None and 1 <= reps <= _EPLEY_MAX_TRUSTED_REPS


def is_hard_set(set_type: str) -> bool:
    """A working set that counts toward volume — everything except warmups."""
    return set_type.strip().lower() != "warmup"


def _week_start(moment: datetime) -> date:
    d = moment.date()
    return d - timedelta(days=d.weekday())


def weekly_volume(sets: Iterable[SetRecord]) -> list[WeeklyMuscleVolume]:
    """Hard-set count and tonnage per (week, muscle). Attribution rule (§5):
    credits the PRIMARY muscle only — secondary muscles are not fractionally
    counted. Warmups and unmapped-exercise sets are excluded."""
    hard_sets: dict[tuple[date, str], int] = defaultdict(int)
    tonnage: dict[tuple[date, str], float] = defaultdict(float)

    for s in sets:
        if s.primary_muscle is None or not is_hard_set(s.set_type):
            continue
        key = (_week_start(s.performed_at), s.primary_muscle)
        hard_sets[key] += 1
        if s.weight_kg is not None and s.reps is not None:
            tonnage[key] += s.weight_kg * s.reps

    return [
        WeeklyMuscleVolume(
            week_start=week, muscle=muscle, hard_sets=count, tonnage_kg=tonnage[(week, muscle)]
        )
        for (week, muscle), count in sorted(hard_sets.items())
    ]


def true_rep_capacity(
    sets: Iterable[SetRecord], exercise_slug: str, weight_kg: float
) -> int | None:
    """Max reps the user has ACTUALLY logged at exactly this weight — a
    verified fact, not an estimate. This is the metric a Gemini hallucination
    got wrong (prescribing 3-5 reps at a weight the user could only do 2)."""
    reps = [
        s.reps
        for s in sets
        if s.exercise_slug == exercise_slug and s.weight_kg == weight_kg and s.reps is not None
    ]
    return max(reps) if reps else None


def personal_records(sets: Iterable[SetRecord], exercise_slug: str) -> PersonalRecords:
    ex = [s for s in sets if s.exercise_slug == exercise_slug]
    weights = [s.weight_kg for s in ex if s.weight_kg is not None]
    reps = [s.reps for s in ex if s.reps is not None]
    est_1rms = [v for s in ex if (v := estimated_1rm(s.weight_kg, s.reps)) is not None]
    return PersonalRecords(
        max_weight_kg=max(weights) if weights else None,
        max_reps=max(reps) if reps else None,
        best_est_1rm=max(est_1rms) if est_1rms else None,
    )


def exercise_progression(
    sets: Iterable[SetRecord], exercise_slug: str
) -> list[ExerciseSessionPoint]:
    """Per-session top weight and best est-1RM over time, oldest first."""
    by_session: dict[datetime, list[SetRecord]] = defaultdict(list)
    for s in sets:
        if s.exercise_slug == exercise_slug:
            by_session[s.performed_at].append(s)

    points = []
    for performed_at, session_sets in sorted(by_session.items()):
        weights = [s.weight_kg for s in session_sets if s.weight_kg is not None]
        est_1rms = [
            v for s in session_sets if (v := estimated_1rm(s.weight_kg, s.reps)) is not None
        ]
        points.append(
            ExerciseSessionPoint(
                session_date=performed_at.date(),
                top_weight_kg=max(weights) if weights else None,
                best_est_1rm=max(est_1rms) if est_1rms else None,
            )
        )
    return points


def detect_plateau(
    sets: Iterable[SetRecord],
    exercise_slug: str,
    *,
    window: int = _PLATEAU_WINDOW,
    excluded_dates: frozenset[date] = frozenset(),
) -> PlateauResult:
    """Classify recent progression on one exercise (§6.6).

    - regressing: latest est-1RM has dropped below where the window started.
    - stalled: best est-1RM in the window never improved by >=1% over its start.
    - progressing: otherwise.

    Deload-aware: `excluded_dates` (planned deloads, decided by the caller) are
    dropped from the window so an intentional light week doesn't false-flag.
    """
    points = [
        p
        for p in exercise_progression(sets, exercise_slug)
        if p.best_est_1rm is not None and p.session_date not in excluded_dates
    ]
    if len(points) < window:
        return PlateauResult(status="insufficient_data", sessions_analyzed=len(points))

    recent = points[-window:]
    values = [p.best_est_1rm for p in recent if p.best_est_1rm is not None]
    baseline, latest, peak = values[0], values[-1], max(values)

    if latest < baseline:
        status = "regressing"
    elif (peak - baseline) / baseline < _PLATEAU_IMPROVEMENT_THRESHOLD:
        status = "stalled"
    else:
        status = "progressing"

    return PlateauResult(status=status, sessions_analyzed=window)
