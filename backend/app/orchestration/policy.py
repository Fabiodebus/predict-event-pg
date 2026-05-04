from pydantic import BaseModel, Field


class EscalationPolicy(BaseModel):
    """Per-workflow escalation policy.

    iteration_count is the number of completed automated attempts.
    score is the acceptance score from the most recent evaluator pass (0..1).
    Escalation triggers when iteration_count >= max AND score < threshold.
    """

    max_iteration_count: int = Field(gt=0)
    acceptance_threshold: float = Field(ge=0.0, le=1.0)

    def should_escalate(self, *, iteration_count: int, score: float) -> bool:
        return iteration_count >= self.max_iteration_count and score < self.acceptance_threshold
