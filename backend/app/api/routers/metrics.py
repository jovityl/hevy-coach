import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import CurrentUser, get_current_user
from app.domain.metrics import (
    ExerciseSessionPoint,
    PersonalRecords,
    PlateauResult,
    WeeklyMuscleVolume,
)
from app.repositories.workout_repo import WorkoutRepository
from app.services.metrics_service import MetricsService

router = APIRouter(prefix="/metrics", tags=["metrics"])


def get_metrics_service(session: AsyncSession = Depends(get_db)) -> MetricsService:
    return MetricsService(WorkoutRepository(session))


@router.get("/volume")
async def volume(
    user: CurrentUser = Depends(get_current_user),
    service: MetricsService = Depends(get_metrics_service),
) -> list[WeeklyMuscleVolume]:
    """Weekly hard-set count and tonnage per muscle group."""
    return await service.weekly_volume(uuid.UUID(user.user_id))


@router.get("/progression")
async def progression(
    exercise_slug: str,
    user: CurrentUser = Depends(get_current_user),
    service: MetricsService = Depends(get_metrics_service),
) -> list[ExerciseSessionPoint]:
    """Per-session top weight and estimated 1RM over time for one exercise."""
    return await service.progression(uuid.UUID(user.user_id), exercise_slug)


@router.get("/plateau")
async def plateau(
    exercise_slug: str,
    user: CurrentUser = Depends(get_current_user),
    service: MetricsService = Depends(get_metrics_service),
) -> PlateauResult:
    """Plateau classification for one exercise."""
    return await service.plateau(uuid.UUID(user.user_id), exercise_slug)


@router.get("/records")
async def records(
    exercise_slug: str,
    user: CurrentUser = Depends(get_current_user),
    service: MetricsService = Depends(get_metrics_service),
) -> PersonalRecords:
    """Personal records for one exercise."""
    return await service.personal_records(uuid.UUID(user.user_id), exercise_slug)
