import pytest

from app.orchestration.policy import EscalationPolicy


def test_policy_accepts_valid_thresholds():
    p = EscalationPolicy(max_iteration_count=2, acceptance_threshold=0.8)
    assert p.max_iteration_count == 2
    assert p.acceptance_threshold == 0.8


def test_policy_rejects_invalid_threshold():
    with pytest.raises(ValueError):
        EscalationPolicy(max_iteration_count=2, acceptance_threshold=1.5)


def test_policy_rejects_zero_iterations():
    with pytest.raises(ValueError):
        EscalationPolicy(max_iteration_count=0, acceptance_threshold=0.8)


def test_should_escalate_at_or_above_max():
    p = EscalationPolicy(max_iteration_count=2, acceptance_threshold=0.8)
    assert p.should_escalate(iteration_count=2, score=0.5) is True


def test_should_not_escalate_when_score_meets_threshold():
    p = EscalationPolicy(max_iteration_count=2, acceptance_threshold=0.8)
    assert p.should_escalate(iteration_count=2, score=0.9) is False


def test_should_not_escalate_below_max():
    p = EscalationPolicy(max_iteration_count=2, acceptance_threshold=0.8)
    assert p.should_escalate(iteration_count=1, score=0.5) is False
