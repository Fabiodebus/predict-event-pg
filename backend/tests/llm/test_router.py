import httpx
import pytest
import respx

from app.llm.anthropic_provider import AnthropicProvider
from app.llm.openai_provider import OpenAIProvider
from app.llm.provider import LLMMessage
from app.llm.roles import LLMRole
from app.llm.router import LLMRouter


def _router():
    return LLMRouter(
        providers=[AnthropicProvider(api_key="x"), OpenAIProvider(api_key="y")],
        role_models={
            "long_context_reasoning": "anthropic:claude-3-7-sonnet-20250219",
            "structured_extraction": "openai:gpt-4o-mini",
            "message_generation": "openai:gpt-4o-mini",
        },
    )


@respx.mock
async def test_router_dispatches_long_context_to_anthropic():
    route = respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "msg_1", "type": "message", "role": "assistant",
                "content": [{"type": "text", "text": "ok"}],
                "model": "claude-3-7-sonnet-20250219",
                "stop_reason": "end_turn", "stop_sequence": None,
                "usage": {"input_tokens": 1, "output_tokens": 1},
            },
        )
    )
    r = _router()
    await r.acomplete(
        role=LLMRole.LONG_CONTEXT_REASONING,
        messages=[LLMMessage(role="user", content="hi")],
        max_tokens=8,
    )
    assert route.called


@respx.mock
async def test_router_dispatches_structured_extraction_to_openai():
    route = respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "c1", "object": "chat.completion", "created": 0,
                "model": "gpt-4o-mini",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )
    )
    r = _router()
    await r.acomplete(
        role=LLMRole.STRUCTURED_EXTRACTION,
        messages=[LLMMessage(role="user", content="hi")],
        max_tokens=8,
    )
    assert route.called


def test_router_rejects_incomplete_role_mapping():
    # Construction must fail when role_models doesn't cover every LLMRole.
    with pytest.raises(ValueError, match="missing entries"):
        LLMRouter(
            providers=[AnthropicProvider(api_key="x")],
            role_models={"long_context_reasoning": "anthropic:m"},
        )


def test_router_raises_for_unknown_provider():
    with pytest.raises(ValueError):
        LLMRouter(
            providers=[AnthropicProvider(api_key="x")],
            role_models={"long_context_reasoning": "vertex:gemini-1.5"},
        )
