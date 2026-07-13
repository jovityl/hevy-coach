import csv
import io
from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime

from app.domain.models import Workout, WorkoutSet
from app.domain.muscle_map import slugify
from app.interfaces.workout_source import WorkoutSourceAdapter

# Hevy's export timestamp format, e.g. "6 Jul 2026, 20:10".
_HEVY_DATETIME_FORMAT = "%d %b %Y, %H:%M"

# Hevy's fixed export schema. We target exactly this one known layout (a
# deliberate choice over LiftShift's generic multi-vendor detection engine,
# per §4.3), so a missing column is a hard, clear error rather than a guess.
_REQUIRED_COLUMNS = frozenset(
    {
        "title",
        "start_time",
        "end_time",
        "description",
        "exercise_title",
        "superset_id",
        "exercise_notes",
        "set_index",
        "set_type",
        "weight_kg",
        "reps",
        "distance_km",
        "duration_seconds",
        "rpe",
    }
)


def _clean(value: str | None) -> str | None:
    stripped = (value or "").strip()
    return stripped or None


def _to_float(value: str | None) -> float | None:
    cleaned = _clean(value)
    return float(cleaned) if cleaned is not None else None


def _to_int(value: str | None) -> int | None:
    cleaned = _clean(value)
    return int(float(cleaned)) if cleaned is not None else None


class HevyCsvAdapter(WorkoutSourceAdapter):
    """Parses a Hevy CSV export into canonical Workouts.

    One workout = all rows sharing the same `start_time` (titles repeat and
    are not unique; start_time is the reliable grouping key, verified against
    a real 232-workout export).
    """

    def __init__(self, csv_content: str) -> None:
        self._csv_content = csv_content

    def fetch(self) -> list[Workout]:
        reader = csv.DictReader(io.StringIO(self._csv_content))
        self._validate_columns(reader.fieldnames)

        by_start_time: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in reader:
            by_start_time[row["start_time"]].append(row)

        return [self._build_workout(rows) for rows in by_start_time.values()]

    @staticmethod
    def _validate_columns(fieldnames: Sequence[str] | None) -> None:
        present = set(fieldnames or [])
        missing = _REQUIRED_COLUMNS - present
        if missing:
            raise ValueError(f"CSV is missing required Hevy columns: {sorted(missing)}")

    def _build_workout(self, rows: list[dict[str, str]]) -> Workout:
        first = rows[0]
        return Workout(
            source="hevy_csv",
            external_id=None,
            title=first["title"],
            started_at=self._parse_datetime(first["start_time"]),
            ended_at=self._parse_optional_datetime(first["end_time"]),
            notes=_clean(first["description"]),
            sets=[self._build_set(row) for row in rows],
        )

    def _build_set(self, row: dict[str, str]) -> WorkoutSet:
        exercise_name = row["exercise_title"].strip()
        distance_km = _to_float(row["distance_km"])
        return WorkoutSet(
            exercise_name=exercise_name,
            exercise_slug=slugify(exercise_name),
            set_index=_to_int(row["set_index"]) or 0,
            set_type=_clean(row["set_type"]) or "normal",
            weight_kg=_to_float(row["weight_kg"]),
            reps=_to_int(row["reps"]),
            rpe=_to_float(row["rpe"]),
            distance_m=distance_km * 1000 if distance_km is not None else None,
            duration_s=_to_int(row["duration_seconds"]),
            notes=_clean(row["exercise_notes"]),
            superset_id=_clean(row["superset_id"]),
        )

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        return datetime.strptime(value.strip(), _HEVY_DATETIME_FORMAT)

    @classmethod
    def _parse_optional_datetime(cls, value: str) -> datetime | None:
        cleaned = _clean(value)
        return cls._parse_datetime(cleaned) if cleaned is not None else None
