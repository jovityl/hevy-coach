import hashlib
from datetime import datetime

from pydantic import BaseModel, field_validator


class WorkoutSet(BaseModel):
    """One logged set, normalized into our canonical shape. Every source
    (CSV now, API later) converges on this — services/metrics only ever see
    this, never source-specific rows."""

    exercise_name: str
    exercise_slug: str
    set_index: int
    set_type: str  # "normal" | "warmup" | "failure" | "dropset"
    weight_kg: float | None = None
    reps: int | None = None
    rpe: float | None = None
    distance_m: float | None = None
    duration_s: int | None = None
    notes: str | None = None  # per-exercise note (Hevy's exercise_notes)
    superset_id: str | None = None

    @field_validator("rpe")
    @classmethod
    def _rpe_in_range(cls, value: float | None) -> float | None:
        if value is not None and not 1.0 <= value <= 10.0:
            raise ValueError("rpe must be between 1 and 10")
        return value


class Workout(BaseModel):
    """One workout session — a group of sets sharing a start time."""

    source: str  # "hevy_csv" | "hevy_api"
    external_id: str | None = None  # stable id from the API; None for CSV
    title: str
    started_at: datetime
    ended_at: datetime | None = None
    notes: str | None = None
    sets: list[WorkoutSet]

    @property
    def content_hash(self) -> str:
        """Stable fingerprint over (start, title, sorted set contents), used
        as the CSV dedup key (§4.5). Identical logged sessions produce an
        identical hash regardless of upload order, so re-uploading the same
        export can't double-count."""
        set_fingerprints = sorted(
            f"{s.exercise_slug}|{s.set_index}|{s.weight_kg}|{s.reps}|{s.set_type}"
            for s in self.sets
        )
        payload = "\n".join([self.started_at.isoformat(), self.title, *set_fingerprints])
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
