import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

# text-embedding-3-small dimensionality.
EMBEDDING_DIM = 1536


class WorkoutRow(Base):
    """`workouts` table. `user_id` is the Supabase JWT `sub` (a UUID) — there
    is no local users table and no FK to one, since Supabase owns identity.
    Per-user isolation is enforced in app code by always filtering on
    user_id (§3.1)."""

    __tablename__ = "workouts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID]
    source: Mapped[str]
    external_id: Mapped[str | None]
    content_hash: Mapped[str]
    title: Mapped[str]
    started_at: Mapped[datetime]
    ended_at: Mapped[datetime | None]
    notes: Mapped[str | None]
    raw_storage_key: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    sets: Mapped[list["WorkoutSetRow"]] = relationship(
        back_populates="workout", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # CSV dedup key (§4.5): the same logged session can't be inserted
        # twice for a user, regardless of re-upload.
        UniqueConstraint("user_id", "content_hash", name="uq_workouts_user_content_hash"),
        # API dedup key (Phase 6): Hevy's stable id, unique per user.
        UniqueConstraint("user_id", "external_id", name="uq_workouts_user_external_id"),
        Index("ix_workouts_user_started_at", "user_id", "started_at"),
    )


class WorkoutSetRow(Base):
    """`workout_sets` table — one row per logged set."""

    __tablename__ = "workout_sets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workout_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workouts.id", ondelete="CASCADE"), index=True
    )
    exercise_name: Mapped[str]
    exercise_slug: Mapped[str] = mapped_column(index=True)
    set_index: Mapped[int]
    set_type: Mapped[str]
    weight_kg: Mapped[float | None]
    reps: Mapped[int | None]
    rpe: Mapped[float | None]
    distance_m: Mapped[float | None]
    duration_s: Mapped[int | None]
    notes: Mapped[str | None]
    superset_id: Mapped[str | None]

    workout: Mapped["WorkoutRow"] = relationship(back_populates="sets")


class ScienceCorpusRow(Base):
    """`science_corpus` — condensed, cited research findings for RAG. Global
    (not user-scoped). `abstract_text` is the retained source for auditability
    (§6.2); `condensation_reviewed` flags whether the finding was checked
    against that source."""

    __tablename__ = "science_corpus"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    pubmed_id: Mapped[str]
    title: Mapped[str]
    finding_text: Mapped[str]
    abstract_text: Mapped[str]
    topic_tags: Mapped[list[str]] = mapped_column(JSONB)
    citation: Mapped[str]
    source_url: Mapped[str]
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM))
    condensation_reviewed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
