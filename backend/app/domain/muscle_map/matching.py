"""Fallback matching against the broader public-domain exercise dataset.

free-exercise-db (Unlicense/public domain, 873 exercises) covers exercises
outside our own hand-verified seed. Source:
https://github.com/yuhonas/free-exercise-db

Resolution here is two-stage: an exact (case-insensitive) lookup, then a
token-overlap fuzzy match. The fuzzy scoring is our own implementation of a
standard technique (normalize -> tokenize -> score by word-set similarity),
not copied from any third-party source.
"""

import json
import re
from functools import lru_cache
from pathlib import Path

from app.domain.muscle_map.models import ExerciseInfo, ExternalEntry

_DATA_DIR = Path(__file__).resolve().parent / "data"

# Maps free-exercise-db's muscle vocabulary onto our own smaller category
# set. Approximate by nature (e.g. adductors folded into quads) — same
# "defensible convention, not ground truth" spirit as the seed's attribution
# rule (CLAUDE.md §5).
_CATEGORY_MAP: dict[str, str] = {
    "quadriceps": "quads",
    "shoulders": "shoulders",
    "abdominals": "core",
    "chest": "chest",
    "hamstrings": "hamstrings",
    "triceps": "triceps",
    "biceps": "biceps",
    "lats": "back",
    "middle back": "back",
    "calves": "calves",
    "lower back": "back",
    "forearms": "forearms",
    "glutes": "glutes",
    "traps": "back",
    "adductors": "quads",
    "neck": "shoulders",
    "abductors": "glutes",
}

# Words dropped before token-overlap comparison — too common to discriminate
# between different exercise names.
_STOP_WORDS = {"the", "a", "an", "with", "on", "and"}

# A fuzzy match is only accepted if the best candidate clears this score AND
# beats the runner-up by at least this gap — otherwise it's too weak or too
# ambiguous to trust, and we return None (surfaced as "unmapped").
_MIN_SCORE = 0.6
_MIN_GAP = 0.05


@lru_cache
def _dataset() -> tuple[ExternalEntry, ...]:
    path = _DATA_DIR / "free_exercise_db.json"
    with path.open(encoding="utf-8") as f:
        return tuple(json.load(f))


@lru_cache
def _by_lower_name() -> dict[str, ExternalEntry]:
    return {d["name"].lower(): d for d in _dataset()}


@lru_cache
def _token_index() -> tuple[tuple[str, frozenset[str]], ...]:
    return tuple((d["name"], _tokenize(d["name"])) for d in _dataset())


def _to_exercise_info(entry: ExternalEntry) -> ExerciseInfo:
    primary_raw = entry["primary_muscles"][0] if entry["primary_muscles"] else "core"
    secondary = tuple(_CATEGORY_MAP.get(m, m) for m in entry["secondary_muscles"])
    return ExerciseInfo(
        display_name=entry["name"],
        primary_muscle=_CATEGORY_MAP.get(primary_raw, "core"),
        secondary_muscles=secondary,
        # free-exercise-db has no MPDS-equivalent flag; a conservative default
        # rather than guessing — worst case an MPDS lift isn't pinned on the
        # dashboard, which is a display nicety, not a correctness issue.
        movement_pattern="isolation",
        is_streetlift_lift=False,
    )


def _normalize(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[()\[\]{}]", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return s.strip()


def _tokenize(name: str) -> frozenset[str]:
    return frozenset(t for t in _normalize(name).split() if t and t not in _STOP_WORDS)


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _overlap_coefficient(a: frozenset[str], b: frozenset[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def exact_match(exercise_title: str) -> ExerciseInfo | None:
    """Case-insensitive exact lookup against the external dataset."""
    entry = _by_lower_name().get(exercise_title.lower())
    return _to_exercise_info(entry) if entry else None


def fuzzy_match(exercise_title: str) -> ExerciseInfo | None:
    """Token-overlap fuzzy match, accepted only when confident and unambiguous.

    Two kinds of "tie" get different treatment:
    - One candidate strictly contains the others (e.g. "Barbell Deadlift" vs
      "Stiff-Legged Barbell Deadlift") -> the shorter, more general one wins.
    - Multiple genuinely different, equally-specific candidates tie (e.g.
      "Ball" vs "Seated" vs "Standing Leg Curl") -> real ambiguity, no correct
      guess exists, so we return None rather than picking one arbitrarily.
    """
    query = _tokenize(exercise_title)
    if not query:
        return None

    scored = [
        (name, len(tokens), max(_jaccard(query, tokens), _overlap_coefficient(query, tokens)))
        for name, tokens in _token_index()
    ]
    best_score = max((score for _, _, score in scored), default=0.0)
    if best_score < _MIN_SCORE:
        return None

    # Among the top-scoring candidates, keep only the most general (fewest
    # tokens). If more than one shares that minimum, it's genuine ambiguity.
    top = [(name, token_count) for name, token_count, score in scored if score == best_score]
    fewest_tokens = min(token_count for _, token_count in top)
    most_general = [name for name, token_count in top if token_count == fewest_tokens]
    if len(most_general) != 1:
        return None

    runner_up = max((score for _, _, score in scored if score < best_score), default=0.0)
    if (best_score - runner_up) < _MIN_GAP:
        return None

    return _to_exercise_info(_by_lower_name()[most_general[0].lower()])
