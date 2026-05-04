from __future__ import annotations

import abc
from typing import Literal

from pydantic import BaseModel


class LLMMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class LLMResponse(BaseModel):
    text: str
    model: str
    input_tokens: int
    output_tokens: int


class LLMProvider(abc.ABC):
    """Abstract LLM provider. Concrete impls call vendor SDKs."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Provider identifier used by the router (e.g. 'anthropic', 'openai')."""

    @abc.abstractmethod
    async def acomplete(
        self,
        *,
        model: str,
        messages: list[LLMMessage],
        max_tokens: int,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Issue a completion request and return the response."""
