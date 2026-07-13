import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


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
