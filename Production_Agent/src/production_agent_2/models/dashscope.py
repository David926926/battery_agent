from __future__ import annotations

import base64
import io
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from PIL import Image


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
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            response_text = ""
            try:
                response_text = response.text.strip()
            except Exception:
                response_text = ""
            detail = f"{exc}"
            if response_text:
                detail = f"{detail}\nDashScope response body: {response_text}"
            raise requests.HTTPError(detail, response=response) from exc
        return response.json()


def encode_image_as_data_url(path: str | Path) -> str:
    image_path = Path(path)

    def _raw_data_url() -> str:
        mime_type = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
        }.get(image_path.suffix.lower(), "image/png")
        payload = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        return f"data:{mime_type};base64,{payload}"

    max_bytes = 9_500_000
    try:
        original_bytes = image_path.read_bytes()
    except Exception:
        return _raw_data_url()

    if len(original_bytes) <= max_bytes:
        mime_type = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
        }.get(image_path.suffix.lower(), "image/png")
        payload = base64.b64encode(original_bytes).decode("utf-8")
        return f"data:{mime_type};base64,{payload}"

    # DashScope multimodal generation rejects files above ~10MB.
    # Compress large images in-memory before converting to data URL.
    with Image.open(image_path) as image:
        image.load()
        base = image.convert("RGBA") if image.mode in {"RGBA", "LA", "P"} else image.convert("RGB")

    width, height = base.size
    longest_side = max(width, height)
    max_side_candidates = [min(longest_side, 2048), 1792, 1600, 1440, 1280, 1024]
    quality_candidates = [88, 82, 76, 70, 64, 58]
    best_bytes: bytes | None = None
    best_mime = "image/webp"

    for max_side in max_side_candidates:
        if longest_side > max_side:
            scale = max_side / longest_side
            resized = base.resize(
                (max(1, int(width * scale)), max(1, int(height * scale))),
                Image.LANCZOS,
            )
        else:
            resized = base.copy()
        for quality in quality_candidates:
            buffer = io.BytesIO()
            if resized.mode == "RGBA":
                resized.save(buffer, format="WEBP", quality=quality, method=6)
                mime_type = "image/webp"
            else:
                rgb_image = resized.convert("RGB")
                rgb_image.save(buffer, format="JPEG", quality=quality, optimize=True)
                mime_type = "image/jpeg"
            candidate = buffer.getvalue()
            best_bytes = candidate
            best_mime = mime_type
            if len(candidate) <= max_bytes:
                payload = base64.b64encode(candidate).decode("utf-8")
                return f"data:{mime_type};base64,{payload}"

    if best_bytes is None:
        return _raw_data_url()

    payload = base64.b64encode(best_bytes).decode("utf-8")
    return f"data:{best_mime};base64,{payload}"


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
