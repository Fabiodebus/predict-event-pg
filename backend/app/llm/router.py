from __future__ import annotations

from app.llm.provider import LLMMessage, LLMProvider, LLMResponse
from app.llm.roles import LLMRole


class LLMRouter:
    """Selects an LLMProvider + model based on a configured role mapping.

    role_models is a {role_value: "<provider>:<model_id>"} mapping. No model
    names are hardcoded in router/provider code; both come from settings.
    """

    def __init__(
        self,
        *,
        providers: list[LLMProvider],
        role_models: dict[str, str],
    ) -> None:
        self._providers = {p.name: p for p in providers}
        self._role_models: dict[str, tuple[LLMProvider, str]] = {}

        for role, value in role_models.items():
            provider_name, _, model = value.partition(":")
            if not provider_name or not model:
                raise ValueError(
                    f"role_models[{role!r}] must be '<provider>:<model_id>', got {value!r}"
                )
            try:
                provider = self._providers[provider_name]
            except KeyError as exc:
                raise ValueError(
                    f"role_models[{role!r}] references unknown provider {provider_name!r}"
                ) from exc
            self._role_models[role] = (provider, model)

    def _resolve(self, role: LLMRole) -> tuple[LLMProvider, str]:
        try:
            return self._role_models[role.value]
        except KeyError as exc:
            raise KeyError(f"no model configured for LLM role {role.value!r}") from exc

    async def acomplete(
        self,
        *,
        role: LLMRole,
        messages: list[LLMMessage],
        max_tokens: int,
        temperature: float = 0.0,
    ) -> LLMResponse:
        provider, model = self._resolve(role)
        return await provider.acomplete(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
