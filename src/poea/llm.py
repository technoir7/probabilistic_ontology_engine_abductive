"""
Provider-agnostic LLM client abstraction.

The LLMClient protocol defines a single method — complete() — that all
provider implementations must satisfy.  The only concrete implementation
shipped here is FireworksClient, which targets Fireworks AI's
OpenAI-compatible endpoint.  Any other OpenAI-compatible provider
(Together AI, OpenAI itself, a local LM Studio server, …) can be used by
passing a custom base_url and api_key to FireworksClient or by
implementing the protocol directly.
"""
from __future__ import annotations

import os
from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    """Minimal contract for a synchronous text-completion client."""

    def complete(self, system: str, user: str, max_tokens: int = 4096) -> str:
        """Return the model's text response given system and user messages."""
        ...


class FireworksClient:
    """
    LLM client for Fireworks AI using their OpenAI-compatible REST endpoint.

    Authentication is read from the FIREWORKS_API_KEY environment variable
    unless an explicit api_key is supplied.

    Usage::

        client = FireworksClient.from_env("accounts/fireworks/models/deepseek-v4-pro")
        text = client.complete(system="You are…", user="Identify concepts…")
    """

    BASE_URL = "https://api.fireworks.ai/inference/v1"
    API_KEY_ENV = "FIREWORKS_API_KEY"

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str = BASE_URL,
    ) -> None:
        from openai import OpenAI

        self._model = model
        self._openai = OpenAI(base_url=base_url, api_key=api_key)

    def complete(self, system: str, user: str, max_tokens: int = 4096) -> str:
        response = self._openai.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""

    @classmethod
    def from_env(cls, model: str, base_url: str = BASE_URL) -> "FireworksClient":
        """
        Construct a client from the FIREWORKS_API_KEY environment variable.

        Raises EnvironmentError if the variable is not set.
        """
        api_key = os.environ.get(cls.API_KEY_ENV)
        if not api_key:
            raise EnvironmentError(
                f"{cls.API_KEY_ENV} environment variable is not set. "
                "Export your Fireworks AI API key before running live induction:\n"
                f"  export {cls.API_KEY_ENV}=your-key-here"
            )
        return cls(model=model, api_key=api_key, base_url=base_url)


def is_rate_limit_error(exc: Exception) -> bool:
    """Return True if exc looks like a provider rate-limit (429) error."""
    try:
        import openai

        if isinstance(exc, openai.RateLimitError):
            return True
    except ImportError:
        pass
    text = str(exc).lower()
    return "429" in text or "rate limit" in text or "rate_limit" in text
