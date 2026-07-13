import uuid

from pydantic import BaseModel

from app.domain.muscle_map import get_exercise_info
from app.interfaces.workout_source import WorkoutSourceAdapter
from app.repositories.workout_repo import WorkoutRepository


class IngestResult(BaseModel):
    inserted: int
    skipped_duplicates: int
    # Exercises that resolved to no muscle group — surfaced explicitly so an
    # incomplete muscle map is visible, never silently dropped from volume.
    unmapped_exercises: list[str]


class IngestionService:
    """Orchestrates: source.fetch() -> dedup -> persist. Depends only on the
    WorkoutSourceAdapter interface, so CSV vs API is just a different source."""

    def __init__(self, repo: WorkoutRepository) -> None:
        self._repo = repo

    async def ingest(self, user_id: uuid.UUID, source: WorkoutSourceAdapter) -> IngestResult:
        workouts = source.fetch()

        # Dedup within the upload itself first (identical logged sessions share
        # a content_hash), then against what's already stored for this user.
        seen: set[str] = set()
        batch = []
        for workout in workouts:
            if workout.content_hash not in seen:
                seen.add(workout.content_hash)
                batch.append(workout)

        already_stored = await self._repo.existing_content_hashes(
            user_id, [w.content_hash for w in batch]
        )
        new_workouts = [w for w in batch if w.content_hash not in already_stored]
        for workout in new_workouts:
            self._repo.add(user_id, workout)
        await self._repo.commit()

        unmapped = sorted(
            {
                s.exercise_name
                for w in workouts
                for s in w.sets
                if get_exercise_info(s.exercise_name) is None
            }
        )
        return IngestResult(
            inserted=len(new_workouts),
            skipped_duplicates=len(workouts) - len(new_workouts),
            unmapped_exercises=unmapped,
        )
