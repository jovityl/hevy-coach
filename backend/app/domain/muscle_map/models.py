import re
from dataclasses import dataclass
from typing import TypedDict


@dataclass(frozen=True)
class ExerciseInfo:
    display_name: str
    primary_muscle: str
    secondary_muscles: tuple[str, ...]
    movement_pattern: str
    is_streetlift_lift: bool


class ExternalEntry(TypedDict):
    """Shape of one record in the external free-exercise-db dataset."""

    name: str
    equipment: str | None
    primary_muscles: list[str]
    secondary_muscles: list[str]


def slugify(name: str) -> str:
    """Deterministic slug derived from a Hevy `exercise_title` string."""
    slug = name.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")
