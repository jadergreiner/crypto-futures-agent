from core.model2.thesis_state import (
    ALLOWED_TRANSITIONS,
    FINAL_THESIS_STATUSES,
    INITIAL_THESIS_STATUS,
    OFFICIAL_THESIS_STATUSES,
    ThesisStatus,
    is_valid_transition,
)


def test_official_statuses_are_exact_and_ordered() -> None:
    assert OFFICIAL_THESIS_STATUSES == (
        "IDENTIFICADA",
        "MONITORANDO",
        "VALIDADA",
        "INVALIDADA",
        "EXPIRADA",
    )


def test_initial_and_final_status_sets() -> None:
    assert INITIAL_THESIS_STATUS == ThesisStatus.IDENTIFICADA
    assert FINAL_THESIS_STATUSES == {
        ThesisStatus.VALIDADA,
        ThesisStatus.INVALIDADA,
        ThesisStatus.EXPIRADA,
    }


def test_allowed_transitions_matrix_matches_business_contract() -> None:
    assert ALLOWED_TRANSITIONS[None] == {ThesisStatus.IDENTIFICADA}
    assert ALLOWED_TRANSITIONS[ThesisStatus.IDENTIFICADA] == {ThesisStatus.MONITORANDO}
    assert ALLOWED_TRANSITIONS[ThesisStatus.MONITORANDO] == {
        ThesisStatus.VALIDADA,
        ThesisStatus.INVALIDADA,
        ThesisStatus.EXPIRADA,
    }
    assert ALLOWED_TRANSITIONS[ThesisStatus.VALIDADA] == set()
    assert ALLOWED_TRANSITIONS[ThesisStatus.INVALIDADA] == set()
    assert ALLOWED_TRANSITIONS[ThesisStatus.EXPIRADA] == set()


def test_is_valid_transition_accepts_valid_paths() -> None:
    assert is_valid_transition(None, ThesisStatus.IDENTIFICADA)
    assert is_valid_transition("IDENTIFICADA", "MONITORANDO")
    assert is_valid_transition("MONITORANDO", "VALIDADA")
    assert is_valid_transition("MONITORANDO", "INVALIDADA")
    assert is_valid_transition("MONITORANDO", "EXPIRADA")


def test_is_valid_transition_rejects_invalid_paths() -> None:
    assert not is_valid_transition(None, "MONITORANDO")
    assert not is_valid_transition("IDENTIFICADA", "VALIDADA")
    assert not is_valid_transition("VALIDADA", "MONITORANDO")
    assert not is_valid_transition("INVALIDADA", "IDENTIFICADA")
    assert not is_valid_transition("EXPIRADA", "VALIDADA")
    assert not is_valid_transition("DESCONHECIDA", "IDENTIFICADA")
    assert not is_valid_transition("MONITORANDO", "DESCONHECIDA")
