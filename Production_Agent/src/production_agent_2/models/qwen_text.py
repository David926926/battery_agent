from __future__ import annotations

import json
from typing import Any

import requests

from production_agent_2.models.dashscope import DEFAULT_BASE_URL, DashScopeClient
from production_agent_2.models.model_routing import get_default_model, run_with_model_fallback


class QwenTextClient:
    model_name = get_default_model("text_chat")

    def __init__(self) -> None:
        self._client = DashScopeClient()

    def is_enabled(self) -> bool:
        return self._client.enabled

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        timeout: int = 180,
        preferred_model: str | None = None,
    ) -> tuple[dict[str, Any], str, list[dict[str, Any]]]:
        if not self._client.enabled:
            raise RuntimeError("DASHSCOPE_API_KEY is not configured")

        base_url = self._client.base_url or DEFAULT_BASE_URL
        if base_url.endswith("/compatible-mode/v1"):
            endpoint = f"{base_url}/chat/completions"
        else:
            endpoint = f"{base_url}/compatible-mode/v1/chat/completions"
        def _call(model_name: str) -> dict[str, Any]:
            response = requests.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {self._client.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model_name,
                    "temperature": 0.2,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()

        payload, resolved_model, attempts = run_with_model_fallback(
            family="text_chat",
            preferred_model=preferred_model or self.model_name,
            call=_call,
        )
        raw_text = payload["choices"][0]["message"]["content"]
        if isinstance(raw_text, list):
            raw_text = "".join(item.get("text", "") for item in raw_text if isinstance(item, dict))
        return json.loads(raw_text), resolved_model, attempts
