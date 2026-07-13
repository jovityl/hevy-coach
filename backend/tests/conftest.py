import uuid
from collections.abc import Iterator

import pytest

from app.core.security import CurrentUser, get_current_user
from app.main import app


@pytest.fixture
def as_user() -> Iterator[uuid.UUID]:
    """Override auth with a fresh random user. Isolation is via the unique
    user_id (every query is user-scoped), so no cleanup is needed — the test
    database is disposable and rows never collide across runs."""
    user_id = uuid.uuid4()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=str(user_id), is_anonymous=True
    )
    try:
        yield user_id
    finally:
        app.dependency_overrides.clear()
