from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


load_dotenv()

DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com"


class DashScopeClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
        self.base_url = os.getenv("DASHSCOPE_BASE_URL", DEFAULT_BASE_URL).rstrip("/")

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def post_multimodal_generation(self, payload: dict[str, Any], timeout: int = 300) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("DASHSCOPE_API_KEY is not configured")
        response = requests.post(
            f"{self.base_url}/api/v1/services/aigc/multimodal-generation/generation",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()


def encode_image_as_data_url(path: str | Path) -> str:
    image_path = Path(path)
    mime_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }.get(image_path.suffix.lower(), "image/png")
    payload = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return f"data:{mime_type};base64,{payload}"


def extract_image_urls(response_json: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for choice in response_json.get("output", {}).get("choices", []):
        for item in choice.get("message", {}).get("content", []):
            if item.get("image"):
                urls.append(item["image"])
    return urls


def download_binary(url: str, timeout: int = 300) -> bytes:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.content
