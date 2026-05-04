from app.llm.roles import LLMRole


def test_llm_roles_cover_blueprint_categories():
    assert {r.value for r in LLMRole} == {
        "long_context_reasoning",
        "structured_extraction",
        "message_generation",
    }
