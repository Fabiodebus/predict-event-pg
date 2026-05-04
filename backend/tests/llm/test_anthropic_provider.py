import httpx
import respx

from app.llm.anthropic_provider import AnthropicProvider
from app.llm.provider import LLMMessage


def test_provider_name():
    assert AnthropicProvider(api_key="x").name == "anthropic"


@respx.mock
async def test_acomplete_returns_response():
    respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "msg_1",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": "Paris"}],
                "model": "claude-3-7-sonnet-20250219",
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 12, "output_tokens": 3},
            },
        )
    )

    provider = AnthropicProvider(api_key="x")
    response = await provider.acomplete(
        model="claude-3-7-sonnet-20250219",
        messages=[LLMMessage(role="user", content="What is the capital of France?")],
        max_tokens=64,
    )
    assert response.text == "Paris"
    assert response.model == "claude-3-7-sonnet-20250219"
    assert response.input_tokens == 12
    assert response.output_tokens == 3
