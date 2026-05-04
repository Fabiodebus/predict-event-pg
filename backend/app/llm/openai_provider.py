from openai import AsyncOpenAI

from app.llm.provider import LLMMessage, LLMProvider, LLMResponse


class OpenAIProvider(LLMProvider):
    @property
    def name(self) -> str:
        return "openai"

    def __init__(self, api_key: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)

    async def acomplete(
        self,
        *,
        model: str,
        messages: list[LLMMessage],
        max_tokens: int,
        temperature: float = 0.0,
    ) -> LLMResponse:
        result = await self._client.chat.completions.create(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        choice = result.choices[0]
        usage = result.usage
        return LLMResponse(
            text=choice.message.content or "",
            model=result.model,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
        )
