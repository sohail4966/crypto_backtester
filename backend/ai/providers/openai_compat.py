"""
OpenAI-compatible HTTP chat completions provider (D-112).
"""

from __future__ import annotations

from typing import Any

import httpx


class OpenAICompatProvider:
    """
    Call an OpenAI-compatible ``/chat/completions`` endpoint.

    Requires ``AI_LLM_API_KEY`` (passed at construction). Never log the key.
    """

    name = "openai_compat"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        timeout_sec: float = 60.0,
    ) -> None:
        if not api_key:
            raise ValueError("OpenAI-compatible provider requires a non-empty API key")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_sec = timeout_sec

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """
        POST chat completions and return the assistant message content.

        Args:
            system_prompt: System instructions.
            user_prompt: User NL text.

        Returns:
            Assistant content string.

        Raises:
            ProviderHTTPError: On non-2xx or empty content.
        """
        url = f"{self._base_url}/chat/completions"
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self._timeout_sec) as client:
                response = client.post(url, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise ProviderHTTPError(f"LLM HTTP request failed: {exc}") from exc

        if response.status_code >= 400:
            raise ProviderHTTPError(
                f"LLM provider returned HTTP {response.status_code}: {response.text[:200]}"
            )

        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderHTTPError("LLM provider returned unexpected payload") from exc

        if not isinstance(content, str) or not content.strip():
            raise ProviderHTTPError("LLM provider returned empty content")
        return content


class ProviderHTTPError(RuntimeError):
    """Upstream LLM HTTP or payload failure."""
