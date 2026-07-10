from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe — 200 as long as the process is up."""
    return {"status": "ok"}
