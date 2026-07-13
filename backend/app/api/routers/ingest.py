import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.hevy_csv_adapter import HevyCsvAdapter
from app.core.db import get_db
from app.core.security import CurrentUser, get_current_user
from app.repositories.workout_repo import WorkoutRepository
from app.services.ingestion_service import IngestionService, IngestResult

router = APIRouter(prefix="/ingest", tags=["ingest"])


def get_ingestion_service(session: AsyncSession = Depends(get_db)) -> IngestionService:
    return IngestionService(WorkoutRepository(session))


@router.post("/csv")
async def ingest_csv(
    file: UploadFile,
    user: CurrentUser = Depends(get_current_user),
    service: IngestionService = Depends(get_ingestion_service),
) -> IngestResult:
    """Upload a Hevy CSV export -> parse, dedup, persist. Scoped to the
    authenticated user; re-uploading the same export won't double-count."""
    try:
        content = (await file.read()).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded.") from exc

    try:
        return await service.ingest(uuid.UUID(user.user_id), HevyCsvAdapter(content))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
