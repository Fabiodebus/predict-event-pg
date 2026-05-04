import httpx
import respx

from app.llm.openai_provider import OpenAIProvider
from app.llm.provider import LLMMessage


def test_provider_name():
    assert OpenAIProvider(api_key="x").name == "openai"


@respx.mock
async def test_acomplete_returns_response():
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "cmpl-1",
                "object": "chat.completion",
                "created": 0,
                "model": "gpt-4o-mini",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "OK"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 7, "completion_tokens": 1, "total_tokens": 8},
            },
        )
    )

    provider = OpenAIProvider(api_key="x")
    response = await provider.acomplete(
        model="gpt-4o-mini",
        messages=[LLMMessage(role="user", content="ping")],
        max_tokens=8,
    )
    assert response.text == "OK"
    assert response.model == "gpt-4o-mini"
    assert response.input_tokens == 7
    assert response.output_tokens == 1
