from app.domain.muscle_map import matching
from app.domain.muscle_map.models import ExerciseInfo
from app.domain.muscle_map.seed_data import EXERCISE_MUSCLE_MAP


def get_exercise_info(exercise_title: str) -> ExerciseInfo | None:
    """Resolve a Hevy `exercise_title` to muscle-group info.

    Resolution order (first hit wins):
    1. Hand-verified seed — exact, most accurate, includes MPDS flags.
    2. Exact match in the broader external dataset.
    3. Fuzzy match against the external dataset.

    Returns None if nothing resolves confidently. Callers must surface that
    explicitly (e.g. metrics_service's `unmapped_exercises`), never silently
    drop the exercise from volume calculations.
    """
    if info := EXERCISE_MUSCLE_MAP.get(exercise_title):
        return info
    if info := matching.exact_match(exercise_title):
        return info
    return matching.fuzzy_match(exercise_title)
