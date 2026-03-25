import argparse
import base64
import json
import mimetypes
import os
from pathlib import Path

from openai import OpenAI

DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen3-omni-flash"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Call Qwen Omni to check if an image contains typos."
    )
    parser.add_argument(
        "--image",
        required=True,
        help="Local image path or HTTP(S) URL that the model should inspect.",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("DASHSCOPE_API_KEY"),
        help="DashScope API key. Defaults to the DASHSCOPE_API_KEY env variable.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Model name to call (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"API base URL (default: {DEFAULT_BASE_URL}).",
    )
    return parser.parse_args()


def to_media_block(image_source: str) -> dict:
    if image_source.startswith("http://") or image_source.startswith("https://"):
        return {"type": "image_url", "image_url": {"url": image_source}}

    path = Path(image_source).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")

    mime, _ = mimetypes.guess_type(path.name)
    mime = (mime or "image/png").lower()
    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    data_url = f"data:{mime};base64,{encoded}"
    return {"type": "image_url", "image_url": {"url": data_url}}


def build_prompt() -> str:
    return (
        "You are an assistant that ONLY checks whether the text in an image contains"
        " typos or misspelled words."
        "\n- Ignore layout, colors, marketing claims, and every other issue."
        "\n- If text is unreadable or missing, say so explicitly."
        "\n- Reply with exactly one JSON object using the format"
        " {\"has_typo\": true/false/null, \"details\": [\"evidence or reason\"] }."
        "\n- Use null for has_typo when you cannot make a judgement."
    )


def extract_first_json(raw_text: str) -> dict:
    raw_text = (raw_text or "").strip()
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("Cannot find a JSON object in the model output:\n" + raw_text)
    return json.loads(raw_text[start : end + 1])


def run_check(args: argparse.Namespace) -> dict:
    if not args.api_key:
        raise RuntimeError(
            "DASHSCOPE_API_KEY is not set. Provide --api-key or export the env variable."
        )

    media_block = to_media_block(args.image)
    client = OpenAI(api_key=args.api_key, base_url=args.base_url)

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": build_prompt()},
                media_block,
            ],
        }
    ]

    text_response = []
    completion = client.chat.completions.create(
        model=args.model,
        messages=messages,
        stream=True,
        stream_options={"include_usage": True},
    )

    for chunk in completion:
        if chunk.choices and chunk.choices[0].delta:
            piece = chunk.choices[0].delta.content or ""
            if piece:
                text_response.append(piece)

    parsed = extract_first_json("".join(text_response))
    return parsed


def main():
    args = parse_args()
    result = run_check(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
