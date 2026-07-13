from abc import ABC, abstractmethod

from app.domain.models import Workout


class WorkoutSourceAdapter(ABC):
    """Port for any workout data source. The only source-specific mapping
    code lives in implementations (HevyCsvAdapter now, HevyApiAdapter later);
    swapping sources changes only the DI binding, nothing in services/."""

    @abstractmethod
    def fetch(self) -> list[Workout]:
        """Return all workouts from this source, normalized to canonical shape."""
        ...
