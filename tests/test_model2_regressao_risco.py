import pytest
from core.model2.model_inference_service import TechnicalSignalInferenceProvider


def test_fail_safe_on_model_unavailable():
    """
    Em indisponibilidade do modelo, deve ser fail-safe e auditavel.
    """
    provider = TechnicalSignalInferenceProvider()
    result = provider.infer(signal={'mode': 'shadow', 'action_source': None, 'rl_fallback': None, 'model_available': False})
    assert result['fail_safe'] is True
    assert result['audit_trail'] is not None


def test_idempotency_decision_id_preserved():
    """
    decision_id deve ser preservado e unico por decisao, mesmo em fallback.
    """
    provider = TechnicalSignalInferenceProvider()
    result1 = provider.infer(signal={'mode': 'shadow', 'decision_id': 'id1'})
    result2 = provider.infer(signal={'mode': 'shadow', 'decision_id': 'id1'})
    assert result1['decision_id'] == result2['decision_id']
