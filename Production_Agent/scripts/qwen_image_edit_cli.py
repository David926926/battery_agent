from __future__ import annotations

import argparse
import base64
import os
from pathlib import Path

import requests


DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com"
DEFAULT_MODEL = "qwen-image-2.0-pro"


def encode_image_as_data_url(path: Path) -> str:
    mime_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }.get(path.suffix.lower(), "image/png")
    payload = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime_type};base64,{payload}"


def extract_image_urls(response_json: dict) -> list[str]:
    urls: list[str] = []
    for choice in response_json.get("output", {}).get("choices", []):
        content = choice.get("message", {}).get("content", [])
        for item in content:
            if item.get("image"):
                urls.append(item["image"])
    return urls


def download_binary(url: str, timeout: int = 300) -> bytes:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.content


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Edit an image with Qwen image editing API")
    parser.add_argument("--image", required=True, help="Input image path")
    parser.add_argument("--prompt", required=True, help="Editing instruction")
    parser.add_argument("--out", required=True, help="Output image path")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Qwen editing model")
    parser.add_argument("--size", default=None, help='Optional output size, e.g. "1328*1328"')
    parser.add_argument("--seed", type=int, default=None, help="Optional seed")
    parser.add_argument("--negative-prompt", default="", help="Optional negative prompt")
    parser.add_argument("--no-prompt-extend", action="store_true", help="Disable prompt rewriting")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("DASHSCOPE_API_KEY is not set")

    image_path = Path(args.image).expanduser().resolve()
    output_path = Path(args.out).expanduser().resolve()
    if not image_path.exists():
        raise SystemExit(f"Input image not found: {image_path}")

    payload = {
        "model": args.model,
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"image": encode_image_as_data_url(image_path)},
                        {"text": args.prompt},
                    ],
                }
            ]
        },
        "parameters": {
            "n": 1,
            "watermark": False,
            "prompt_extend": not args.no_prompt_extend,
        },
    }
    if args.size:
        payload["parameters"]["size"] = args.size
    if args.seed is not None:
        payload["parameters"]["seed"] = args.seed
    if args.negative_prompt:
        payload["parameters"]["negative_prompt"] = args.negative_prompt

    response = requests.post(
        f"{DEFAULT_BASE_URL}/api/v1/services/aigc/multimodal-generation/generation",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=300,
    )
    response.raise_for_status()
    response_json = response.json()

    image_urls = extract_image_urls(response_json)
    if not image_urls:
        raise SystemExit(f"No image returned: {response_json}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(download_binary(image_urls[0]))
    print(f"Saved: {output_path}")
    print(f"Model: {args.model}")
    print(f"Source URL: {image_urls[0]}")


if __name__ == "__main__":
    main()
