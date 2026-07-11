from fastapi.testclient import TestClient
from supabase import create_client

from app.core.config import get_settings
from app.main import app

client = TestClient(app)
settings = get_settings()


def _get_anonymous_token() -> str:
    """Requires network access to Supabase and anonymous sign-ins enabled on the project."""
    supabase = create_client(settings.supabase_url, settings.supabase_anon_key)
    session = supabase.auth.sign_in_anonymously()
    assert session.session is not None
    return session.session.access_token


def test_me_with_valid_anonymous_token() -> None:
    token = _get_anonymous_token()

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["is_anonymous"] is True
    assert body["user_id"]


def test_me_without_token_is_rejected() -> None:
    response = client.get("/auth/me")

    assert response.status_code in (401, 403)
