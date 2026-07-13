from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

settings = get_settings()

# NullPool: don't keep our own connection pool. This is the recommended config
# when connecting through an external pooler (Supabase fronts Postgres with
# pgBouncer in production), and it also keeps each connection bound to a single
# event loop — which the sync TestClient relies on across tests.
engine = create_async_engine(settings.database_url, poolclass=NullPool)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Every ORM model inherits from this. Gives Alembic something to diff against."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields a request-scoped session, closed automatically after."""
    async with async_session_factory() as session:
        yield session
