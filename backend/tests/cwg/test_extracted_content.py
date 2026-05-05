"""Schema-only tests (no DB or LLM) for ExtractedContent."""

import pytest
from pydantic import ValidationError

from app.cwg.tasks import ExtractedContent


def test_round_trip_with_all_fields():
    payload = {
        "solution_description": "Outreach automation",
        "proof_points": ["+30% conversion at X"],
        "use_cases": ["B2B sales"],
        "customer_references": ["Acme"],
        "communication_style_indicators": ["direct"],
    }
    parsed = ExtractedContent.model_validate(payload)
    assert parsed.model_dump() == payload


def test_defaults_when_only_solution_description_given():
    parsed = ExtractedContent.model_validate({"solution_description": "X"})
    assert parsed.proof_points == []
    assert parsed.use_cases == []
    assert parsed.customer_references == []
    assert parsed.communication_style_indicators == []


def test_solution_description_can_be_null():
    parsed = ExtractedContent.model_validate({"solution_description": None})
    assert parsed.solution_description is None


def test_rejects_non_string_in_array_field():
    with pytest.raises(ValidationError):
        ExtractedContent.model_validate({"proof_points": [{"oops": 1}]})


def test_parses_from_json_string():
    parsed = ExtractedContent.model_validate_json(
        '{"solution_description": "X", "proof_points": ["a"]}'
    )
    assert parsed.solution_description == "X"
    assert parsed.proof_points == ["a"]
