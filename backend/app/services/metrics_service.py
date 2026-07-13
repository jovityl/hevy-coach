import uuid

from app.domain import metrics
from app.domain.metrics import (
    ExerciseSessionPoint,
    PersonalRecords,
    PlateauResult,
    SetRecord,
    WeeklyMuscleVolume,
)
from app.domain.muscle_map import get_exercise_info
from app.repositories.workout_repo import WorkoutRepository


class MetricsService:
    """Reads a user's stored sets, projects them into `SetRecord`s (enriching
    each with its primary muscle), and runs the pure metric functions. All the
    actual math lives in domain.metrics — this only assembles the input."""

    def __init__(self, repo: WorkoutRepository) -> None:
        self._repo = repo

    async def _records(self, user_id: uuid.UUID) -> list[SetRecord]:
        rows = await self._repo.fetch_user_sets(user_id)
        records = []
        for row in rows:
            info = get_exercise_info(row.exercise_name)
            records.append(
                SetRecord(
                    exercise_slug=row.exercise_slug,
                    exercise_name=row.exercise_name,
                    primary_muscle=info.primary_muscle if info else None,
                    set_type=row.set_type,
                    weight_kg=row.weight_kg,
                    reps=row.reps,
                    performed_at=row.workout.started_at,
                )
            )
        return records

    async def weekly_volume(self, user_id: uuid.UUID) -> list[WeeklyMuscleVolume]:
        return metrics.weekly_volume(await self._records(user_id))

    async def progression(
        self, user_id: uuid.UUID, exercise_slug: str
    ) -> list[ExerciseSessionPoint]:
        return metrics.exercise_progression(await self._records(user_id), exercise_slug)

    async def plateau(self, user_id: uuid.UUID, exercise_slug: str) -> PlateauResult:
        return metrics.detect_plateau(await self._records(user_id), exercise_slug)

    async def personal_records(self, user_id: uuid.UUID, exercise_slug: str) -> PersonalRecords:
        return metrics.personal_records(await self._records(user_id), exercise_slug)
