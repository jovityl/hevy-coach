import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.models import Workout
from app.repositories.models import WorkoutRow, WorkoutSetRow


class WorkoutRepository:
    """Persistence for workouts. Every query is scoped by user_id — the only
    thing enforcing per-user isolation locally (no DB-level RLS here; §3.1)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def existing_content_hashes(
        self, user_id: uuid.UUID, content_hashes: list[str]
    ) -> set[str]:
        """Which of the given hashes this user already has — the dedup lookup."""
        if not content_hashes:
            return set()
        stmt = select(WorkoutRow.content_hash).where(
            WorkoutRow.user_id == user_id,
            WorkoutRow.content_hash.in_(content_hashes),
        )
        result = await self._session.execute(stmt)
        return set(result.scalars().all())

    def add(self, user_id: uuid.UUID, workout: Workout) -> None:
        """Stage a canonical Workout for insert (sets cascade). Not committed
        until commit() — the service controls the transaction boundary."""
        self._session.add(self._to_row(user_id, workout))

    async def commit(self) -> None:
        await self._session.commit()

    async def fetch_user_sets(self, user_id: uuid.UUID) -> Sequence[WorkoutSetRow]:
        """All of a user's sets, each with its parent workout eagerly loaded
        (for the session date). selectinload avoids an N+1 query."""
        stmt = (
            select(WorkoutSetRow)
            .join(WorkoutRow, WorkoutSetRow.workout_id == WorkoutRow.id)
            .where(WorkoutRow.user_id == user_id)
            .options(selectinload(WorkoutSetRow.workout))
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    def _to_row(user_id: uuid.UUID, workout: Workout) -> WorkoutRow:
        return WorkoutRow(
            user_id=user_id,
            source=workout.source,
            external_id=workout.external_id,
            content_hash=workout.content_hash,
            title=workout.title,
            started_at=workout.started_at,
            ended_at=workout.ended_at,
            notes=workout.notes,
            sets=[
                WorkoutSetRow(
                    exercise_name=s.exercise_name,
                    exercise_slug=s.exercise_slug,
                    set_index=s.set_index,
                    set_type=s.set_type,
                    weight_kg=s.weight_kg,
                    reps=s.reps,
                    rpe=s.rpe,
                    distance_m=s.distance_m,
                    duration_s=s.duration_s,
                    notes=s.notes,
                    superset_id=s.superset_id,
                )
                for s in workout.sets
            ],
        )
