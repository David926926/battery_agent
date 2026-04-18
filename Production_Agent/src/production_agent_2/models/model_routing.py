from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

import requests


T = TypeVar("T")


MODEL_FAMILIES: dict[str, list[dict[str, str | int]]] = {
    "text_chat": [
        {"id": "qwen-max", "label": "Qwen Max", "rank": 1},
        {"id": "qwen-plus", "label": "Qwen Plus", "rank": 2},
        {"id": "qwen-turbo", "label": "Qwen Turbo", "rank": 3},
    ],
    "vision_chat": [
        {"id": "qwen3.5-omni-plus", "label": "Qwen3.5 Omni Plus", "rank": 1},
        {"id": "qwen3.5-omni-flash", "label": "Qwen3.5 Omni Flash", "rank": 2},
        {"id": "qwen3-omni-flash", "label": "Qwen3 Omni Flash", "rank": 3},
        {"id": "qwen-omni-turbo-latest", "label": "Qwen Omni Turbo", "rank": 4},
    ],
    "image_generation": [
        {"id": "qwen-image-max", "label": "Qwen Image Max", "rank": 1},
        {"id": "qwen-image-2.0-pro", "label": "Qwen Image 2.0 Pro", "rank": 2},
        {"id": "qwen-image-plus", "label": "Qwen Image Plus", "rank": 3},
        {"id": "qwen-image-2.0", "label": "Qwen Image 2.0", "rank": 4},
        {"id": "qwen-image", "label": "Qwen Image", "rank": 5},
    ],
    "image_edit": [
        {"id": "qwen-image-edit-max", "label": "Qwen Image Edit Max", "rank": 1},
        {"id": "qwen-image-edit-plus", "label": "Qwen Image Edit Plus", "rank": 2},
        {"id": "qwen-image-edit", "label": "Qwen Image Edit", "rank": 3},
    ],
}


DEFAULT_MODELS = {
    "text_chat": "qwen-plus",
    "vision_chat": "qwen3-omni-flash",
    "image_generation": "qwen-image-2.0-pro",
    "image_edit": "qwen-image-edit-max",
}


def get_family_models(family: str) -> list[dict[str, str | int]]:
    if family not in MODEL_FAMILIES:
        raise KeyError(f"Unknown model family: {family}")
    return list(MODEL_FAMILIES[family])


def get_model_ids(family: str) -> list[str]:
    return [str(item["id"]) for item in get_family_models(family)]


def order_models(family: str, preferred_model: str | None = None) -> list[str]:
    ranked = get_model_ids(family)
    if preferred_model and preferred_model in ranked:
        return [preferred_model] + [item for item in ranked if item != preferred_model]
    if preferred_model and preferred_model not in ranked:
        return [preferred_model] + ranked
    return ranked


def get_default_model(family: str) -> str:
    return DEFAULT_MODELS[family]


def is_retryable_model_error(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None)
    if status_code == 429:
        return True
    response = getattr(exc, "response", None)
    if response is not None and getattr(response, "status_code", None) == 429:
        return True
    if isinstance(exc, requests.HTTPError) and exc.response is not None and exc.response.status_code == 429:
        return True
    message = str(exc).lower()
    retry_markers = [
        "429",
        "too many requests",
        "rate limit",
        "quota",
        "throttl",
        "service unavailable",
        "engine overloaded",
        "request timed out",
        "timed out",
        "busy",
    ]
    return any(marker in message for marker in retry_markers)


def run_with_model_fallback(
    *,
    family: str,
    preferred_model: str | None,
    call: Callable[[str], T],
) -> tuple[T, str, list[dict[str, Any]]]:
    attempts: list[dict[str, Any]] = []
    last_error: Exception | None = None
    candidates = order_models(family, preferred_model)
    for index, model in enumerate(candidates):
        try:
            result = call(model)
            attempts.append({"model": model, "status": "success", "order": index + 1})
            return result, model, attempts
        except Exception as exc:  # pragma: no cover
            retryable = is_retryable_model_error(exc)
            attempts.append(
                {
                    "model": model,
                    "status": "failed",
                    "order": index + 1,
                    "retryable": retryable,
                    "error": str(exc),
                }
            )
            last_error = exc
            if not retryable or index == len(candidates) - 1:
                raise
    if last_error is not None:  # pragma: no cover
        raise last_error
    raise RuntimeError(f"No models configured for family {family}")
