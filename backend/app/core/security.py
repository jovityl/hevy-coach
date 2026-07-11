import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from pydantic import BaseModel

from app.core.config import get_settings

settings = get_settings()

_jwks_client = PyJWKClient(
    f"{settings.supabase_url}/auth/v1/.well-known/jwks.json",
    # Supabase's API gateway rejects requests with no project identifier,
    # even for this public-keys endpoint.
    headers={"apikey": settings.supabase_anon_key},
)

bearer_scheme = HTTPBearer()


class CurrentUser(BaseModel):
    user_id: str
    is_anonymous: bool


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> CurrentUser:
    """Verifies a Supabase-issued JWT against the project's public signing keys (JWKS)."""
    token = credentials.credentials
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    return CurrentUser(
        user_id=payload["sub"],
        is_anonymous=payload.get("is_anonymous", False),
    )
