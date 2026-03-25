#!/usr/bin/env python3
"""
读取 output/prompt_job.json，将 component 图片 + 文案 prompt 直接发送给 wan2.6-image 模型，
由模型自主完成构图、光影、背景融合、文案排版，生成完整海报。
最后用 Pillow 叠加南孚 logo。

用法:
  python scripts/call_image_api.py
  python scripts/call_image_api.py --job output/prompt_job.json --out output/主图商详/poster.png
"""
import argparse
import base64
import io
import json
import os
import sys
import time
from pathlib import Path

from PIL import Image

Image.MAX_IMAGE_PIXELS = None

ROOT = Path(__file__).resolve().parent.parent
POSTER_SIZE = (800, 800)

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / "config" / ".env")
except ImportError:
    pass


# --------------- 图片预处理 ---------------

def prepare_image_b64(path: Path, max_pixels: int = 1280 * 1280) -> str:
    """加载图片 → 去透明通道 → 限制尺寸 → 转 JPEG base64 data URI。

    wan2.6-image 不支持 PNG 透明通道，统一转 JPEG。
    """
    img = Image.open(path)

    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    w, h = img.size
    if w * h > max_pixels:
        scale = (max_pixels / (w * h)) ** 0.5
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    b64 = base64.b64encode(buf.getvalue()).decode()
    size_mb = len(b64) / (1024 * 1024)
    print(f"  {path.name}: {img.size[0]}x{img.size[1]}, {size_mb:.1f} MB", file=sys.stderr)
    return f"data:image/jpeg;base64,{b64}"


# --------------- wan2.6-image API ---------------

def generate_poster(image_paths: list[Path], prompt: str,
                    negative_prompt: str = "", n: int = 4) -> list[bytes]:
    """调用 wan2.6-image，传入 component 图片 + prompt，模型自主生成完整海报。"""
    key = os.environ.get("DASHSCOPE_API_KEY", "").strip()
    if not key:
        raise ValueError("DASHSCOPE_API_KEY 未设置，请在 config/.env 中配置")

    import requests

    content = [{"text": prompt}]
    for p in image_paths[:4]:
        content.append({"image": prepare_image_b64(p)})

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }
    body = {
        "model": "wan2.6-image",
        "input": {
            "messages": [{"role": "user", "content": content}]
        },
        "parameters": {
            "prompt_extend": True,
            "watermark": False,
            "n": min(n, 4),
            "enable_interleave": False,
            "size": "1280*1280",
        },
    }
    if negative_prompt:
        body["parameters"]["negative_prompt"] = negative_prompt

    print("  提交异步任务...", file=sys.stderr)
    resp = requests.post(
        "https://dashscope.aliyuncs.com/api/v1/services/aigc/image-generation/generation",
        headers=headers,
        json=body,
        timeout=60,
    )
    if resp.status_code != 200:
        print(f"API 错误 ({resp.status_code}): {resp.text}", file=sys.stderr)
        resp.raise_for_status()
    data = resp.json()

    if "output" in data and "task_id" in data["output"]:
        task_id = data["output"]["task_id"]
        print(f"  任务已创建: {task_id}", file=sys.stderr)
        return _poll_task(key, task_id)

    if "output" in data and "choices" in data["output"]:
        return _extract_images(data["output"]["choices"])

    raise RuntimeError(f"API 返回异常: {data}")


def _poll_task(api_key: str, task_id: str, max_wait: int = 300) -> list[bytes]:
    """轮询异步任务直到完成（wan2.6 生成通常需要 1-3 分钟）。"""
    import requests

    url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
    headers = {"Authorization": f"Bearer {api_key}"}

    waited = 0
    interval = 5
    while waited < max_wait:
        time.sleep(interval)
        waited += interval

        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        status = data.get("output", {}).get("task_status", "")
        print(f"  任务状态: {status} ({waited}s)", file=sys.stderr)

        if status == "SUCCEEDED":
            choices = data.get("output", {}).get("choices", [])
            return _extract_images(choices)
        elif status in ("FAILED", "CANCELED", "UNKNOWN"):
            msg = data.get("message", "") or str(data.get("output", {}))
            raise RuntimeError(f"任务失败: {msg}")

        if interval < 15:
            interval += 2

    raise RuntimeError(f"任务超时 ({max_wait}s)")


def _extract_images(choices: list) -> list[bytes]:
    """从 wan2.6-image 的 choices 响应中下载所有图片。"""
    import urllib.request

    images = []
    for choice in choices:
        for item in choice.get("message", {}).get("content", []):
            if item.get("type") == "image" and item.get("image"):
                with urllib.request.urlopen(item["image"]) as r:
                    images.append(r.read())

    if not images:
        raise RuntimeError(f"API 未返回图片: {choices}")
    return images


# --------------- Logo 叠加 ---------------

LOGO_PATH = ROOT / "Input Component" / "logo.jpg"


def _remove_white_bg(img: Image.Image, threshold: int = 240) -> Image.Image:
    """将接近白色的像素变为透明，用于处理白底 logo。"""
    img = img.convert("RGBA")
    pixels = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if r > threshold and g > threshold and b > threshold:
                pixels[x, y] = (r, g, b, 0)
    return img


def overlay_logo(img: Image.Image, position: str = "top-left") -> Image.Image:
    """在海报上叠加南孚 logo。

    logo 自动去白底，缩放到海报宽度的 25%，放在指定角落。
    """
    if not LOGO_PATH.exists():
        print(f"  警告: logo 文件不存在 ({LOGO_PATH})，跳过", file=sys.stderr)
        return img

    logo = Image.open(LOGO_PATH)
    logo = _remove_white_bg(logo)

    w, h = img.size
    logo_w = int(w * 0.25)
    ratio = logo_w / logo.width
    logo_h = int(logo.height * ratio)
    logo = logo.resize((logo_w, logo_h), Image.LANCZOS)

    padding = int(w * 0.03)
    if position == "top-left":
        x, y = padding, padding
    elif position == "top-right":
        x, y = w - logo_w - padding, padding
    elif position == "bottom-left":
        x, y = padding, h - logo_h - padding
    else:
        x, y = w - logo_w - padding, h - logo_h - padding

    canvas = img.convert("RGBA")
    canvas.paste(logo, (x, y), logo)
    return canvas.convert("RGB")


# --------------- 主流程 ---------------

def main():
    parser = argparse.ArgumentParser(description="调用 wan2.6-image 生成完整海报")
    parser.add_argument("--job", type=Path, default=None, help="prompt_job.json 路径")
    parser.add_argument("--out", type=Path, default=None, help="输出目录")
    args = parser.parse_args()

    job_path = args.job or (ROOT / "output" / "prompt_job.json")
    if not job_path.exists():
        print(f"Error: 未找到 {job_path}", file=sys.stderr)
        print("请先执行: python scripts/generate_poster.py --dry-run", file=sys.stderr)
        sys.exit(1)

    with open(job_path, "r", encoding="utf-8") as f:
        job = json.load(f)

    poster_type = job.get("poster_type", "主图商详")
    comp_paths = [Path(p) for p in job.get("component_paths", [])]
    prompt = job.get("prompt", "")

    valid_paths = [p for p in comp_paths if p.exists()]
    if not valid_paths:
        print("Error: 无有效 component 图片", file=sys.stderr)
        sys.exit(1)

    print(f"发送 {len(valid_paths)} 张 component 图片给 wan2.6-image:", file=sys.stderr)
    for p in valid_paths:
        print(f"  - {p.name}", file=sys.stderr)

    negative = "低分辨率，低画质，白色背景，透明背景，文字模糊扭曲，构图混乱，卡通风格，插画风格，AI感，蜡像感，过度光滑，肢体畸形"

    all_bytes = generate_poster(valid_paths, prompt, negative_prompt=negative, n=3)
    print(f"API 返回 {len(all_bytes)} 张候选图", file=sys.stderr)

    if args.out:
        out_dir = args.out
    else:
        out_dir = ROOT / "output" / poster_type
    out_dir.mkdir(parents=True, exist_ok=True)

    for idx, raw_bytes in enumerate(all_bytes, start=1):
        img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
        img = img.resize(POSTER_SIZE, Image.LANCZOS)
        img = overlay_logo(img, position="top-left")

        out_path = out_dir / f"poster_{idx}.png"
        img.save(out_path, "PNG")
        print(f"海报已保存: {out_path}")

    print(f"\n共生成 {len(all_bytes)} 张海报，请挑选最满意的。")


if __name__ == "__main__":
    main()
