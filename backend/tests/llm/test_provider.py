import inspect

import pytest

from app.llm.provider import LLMMessage, LLMProvider, LLMResponse


def test_llm_provider_is_abstract():
    with pytest.raises(TypeError):
        LLMProvider()  # type: ignore[abstract]


def test_llm_provider_required_methods():
    abstracts = {
        n for n, m in inspect.getmembers(LLMProvider)
        if getattr(m, "__isabstractmethod__", False)
    }
    assert abstracts == {"acomplete", "name"}


def test_llm_message_round_trip():
    msg = LLMMessage(role="user", content="hi")
    assert msg.role == "user"
    assert msg.content == "hi"


def test_llm_response_round_trip():
    r = LLMResponse(text="hello", model="x", input_tokens=10, output_tokens=5)
    assert r.text == "hello"
    assert r.model == "x"
