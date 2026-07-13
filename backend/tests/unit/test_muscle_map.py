from app.domain.muscle_map import get_exercise_info


def test_exact_match_from_hand_verified_map() -> None:
    info = get_exercise_info("Bench Press (Barbell)")

    assert info is not None
    assert info.primary_muscle == "chest"
    assert info.is_streetlift_lift is False


def test_exact_match_from_external_dataset() -> None:
    info = get_exercise_info("Cable Crossover")

    assert info is not None
    assert info.primary_muscle == "chest"


def test_fuzzy_match_resolves_the_more_general_candidate() -> None:
    """'Deadlift (Barbell)' should resolve to 'Barbell Deadlift', not the
    more specific 'Stiff-Legged Barbell Deadlift' — both fully contain the
    query's tokens, but the shorter one is the correct general match."""
    info = get_exercise_info("Deadlift (Barbell)")

    assert info is not None
    assert info.display_name == "Barbell Deadlift"
    assert info.primary_muscle == "back"


def test_fuzzy_match_declines_genuine_ambiguity() -> None:
    """'Leg Curl (Machine)' ties equally between Ball/Seated/Standing Leg
    Curl (same token count, same score) — no correct guess exists, so this
    must return None rather than silently picking one."""
    assert get_exercise_info("Leg Curl (Machine)") is None


def test_unrecognized_exercise_returns_none() -> None:
    assert get_exercise_info("asdkfjapsdoifj not a real exercise") is None
