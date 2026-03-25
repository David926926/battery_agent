import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Iterable, List

from openai import OpenAI

from qwen3_vlm_api import (
    BASE_URL,
    MODEL_NAME,
    SYSTEM_PROMPT,
    build_prompt,
    extract_first_json,
    file_to_media_block,
)


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def parse_args() -> argparse.Namespace:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    default_out = f"batch_evaluation_{ts}"

    parser = argparse.ArgumentParser(
        description="批量遍历文件夹图片，并调用 qwen VLM 逐张评估。"
    )
    parser.add_argument("--input-dir", required=True, help="待遍历的图片目录")
    parser.add_argument("--output-dir", default=default_out, help="输出目录（默认带时间戳）")
    parser.add_argument(
        "--checklist-type",
        default="main_detail",
        choices=["main_detail", "media_ad"],
        help="评估规则类型",
    )
    parser.add_argument("--content-text", default="", help="素材背景补充文本，可选")
    parser.add_argument(
        "--recursive",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="是否递归遍历子目录（默认 true）",
    )
    parser.add_argument("--max-files", type=int, default=0, help="最多处理文件数，0 表示不限制")
    parser.add_argument("--base-url", default=BASE_URL, help="DashScope compatible base URL")
    parser.add_argument(
        "--model-name",
        default=MODEL_NAME,
        help=f"模型名（默认 {MODEL_NAME}）",
    )
    parser.add_argument("--temperature", type=float, default=0.1, help="采样温度")
    parser.add_argument("--top-p", type=float, default=0.1, help="Top-p 采样参数")
    return parser.parse_args()


def list_images(input_dir: Path, recursive: bool) -> List[Path]:
    candidates = input_dir.rglob("*") if recursive else input_dir.glob("*")
    images = [p for p in candidates if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
    return sorted(images)


def iter_limited(items: List[Path], max_files: int) -> Iterable[Path]:
    if max_files <= 0:
        return items
    return items[:max_files]


def run_once(
    client: OpenAI,
    image_path: Path,
    checklist_type: str,
    content_text: str,
    model_name: str,
    temperature: float,
    top_p: float,
) -> dict:
    prompt = build_prompt(
        f"{content_text}\n素材文件名: {image_path.name}".strip(),
        checklist_type=checklist_type,
    )
    media_block = file_to_media_block(str(image_path))
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                media_block,
            ],
        },
    ]

    text_buf = ""
    completion = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=temperature,
        top_p=top_p,
        stream=True,
        stream_options={"include_usage": True},
    )
    for chunk in completion:
        if chunk.choices:
            delta = chunk.choices[0].delta
            if getattr(delta, "content", None):
                text_buf += delta.content

    return extract_first_json(text_buf)


def save_result(output_dir: Path, input_dir: Path, image_path: Path, result: dict) -> Path:
    rel_path = image_path.relative_to(input_dir)
    out_path = (output_dir / rel_path).with_suffix(".json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def main() -> None:
    args = parse_args()

    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("未检测到环境变量 DASHSCOPE_API_KEY，请先 export 后再运行。")

    input_dir = Path(args.input_dir).expanduser().resolve()
    if not input_dir.exists() or not input_dir.is_dir():
        raise RuntimeError(f"输入目录不存在或不是目录: {input_dir}")

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    images = list_images(input_dir, recursive=args.recursive)
    if not images:
        raise RuntimeError(f"目录下未找到图片文件（支持: {sorted(IMAGE_EXTS)}）: {input_dir}")

    selected = list(iter_limited(images, args.max_files))
    print(f"共找到 {len(images)} 张图片，本次处理 {len(selected)} 张。")

    client = OpenAI(api_key=api_key, base_url=args.base_url)

    summary_path = output_dir / "summary.jsonl"
    ok_count = 0
    fail_count = 0
    with summary_path.open("w", encoding="utf-8") as f:
        for idx, image_path in enumerate(selected, start=1):
            print(f"[{idx}/{len(selected)}] 处理: {image_path}")
            try:
                result = run_once(
                    client=client,
                    image_path=image_path,
                    checklist_type=args.checklist_type,
                    content_text=args.content_text,
                    model_name=args.model_name,
                    temperature=args.temperature,
                    top_p=args.top_p,
                )
                out_file = save_result(output_dir, input_dir, image_path, result)
                record = {
                    "file": str(image_path),
                    "output_json": str(out_file),
                    "model_used": args.model_name,
                    "overall_grade": result.get("overall_grade"),
                    "overall_score": result.get("overall_score"),
                    "status": "ok",
                }
                ok_count += 1
            except Exception as e:
                record = {
                    "file": str(image_path),
                    "status": "error",
                    "error": str(e),
                }
                fail_count += 1

            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()

    print(f"完成。成功 {ok_count}，失败 {fail_count}。")
    print(f"结果目录: {output_dir}")
    print(f"汇总文件: {summary_path}")


if __name__ == "__main__":
    main()
