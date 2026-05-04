from anthropic import AsyncAnthropic

from app.llm.provider import LLMMessage, LLMProvider, LLMResponse


class AnthropicProvider(LLMProvider):
    @property
    def name(self) -> str:
        return "anthropic"

    def __init__(self, api_key: str) -> None:
        self._client = AsyncAnthropic(api_key=api_key)

    async def acomplete(
        self,
        *,
        model: str,
        messages: list[LLMMessage],
        max_tokens: int,
        temperature: float = 0.0,
    ) -> LLMResponse:
        # Anthropic separates the system prompt from messages.
        system_parts = [m.content for m in messages if m.role == "system"]
        chat_messages = [
            {"role": m.role, "content": m.content} for m in messages if m.role != "system"
        ]
        kwargs: dict[str, object] = {
            "model": model,
            "messages": chat_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_parts:
            kwargs["system"] = "\n\n".join(system_parts)

        result = await self._client.messages.create(**kwargs)
        text = "".join(block.text for block in result.content if block.type == "text")
        return LLMResponse(
            text=text,
            model=result.model,
            input_tokens=result.usage.input_tokens,
            output_tokens=result.usage.output_tokens,
        )
