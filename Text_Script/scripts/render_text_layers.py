#!/usr/bin/env python3
"""
Text 字体模块（独立可运行）

功能：
1) 支持手动输入文案（仅 headline）
2) 支持在命令行输入文字样式参数（字体、字号、颜色、描边、阴影、对齐等）
3) 使用 Text/字体库 下的 TTF/OTF 渲染透明文字图层
4) 输出图层 PNG + 元数据 JSON + 预览图

示例：
python "Text/scripts/render_text_layers.py" \
  --headline "南孚聚能环5代" \
  --template clean_red \
  --font-file "SourceHanSansSC-Heavy.otf" \
  --font-size 92 \
  --fill "#FFFFFF" \
  --stroke-fill "#8A0000" \
  --stroke-width 3 \
  --shadow \
  --shadow-color "#2A0000" \
  --shadow-offset-x 2 \
  --shadow-offset-y 2 \
  --align center \
  --max-width 680
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageColor, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
FONT_DIR = ROOT / "Text" / "字体库"
OUT_DIR = ROOT / "Text" / "output"
POSTER_SIZE = (800, 800)


TEMPLATES: dict[str, dict[str, Any]] = {
    "clean_red": {
        "font_file": "Alibaba-PuHuiTi-Heavy.otf",
        "font_size": 86,
        "fill": "#FFFFFF",
        "stroke_fill": "#B40000",
        "stroke_width": 3,
        "shadow": True,
        "shadow_color": "#500000",
        "shadow_offset": [2, 2],
        "line_spacing": 12,
        "align": "center",
    },
    "brand_black_gold": {
        "font_file": "SourceHanSansSC-Heavy.otf",
        "font_size": 82,
        "fill": "#F8E9A1",
        "stroke_fill": "#2D2D2D",
        "stroke_width": 2,
        "shadow": True,
        "shadow_color": "#1A1A1A",
        "shadow_offset": [2, 2],
        "line_spacing": 10,
        "align": "center",
    },
    "stylized": {
        "font_file": "字语咏宏体.TTF",
        "font_size": 88,
        "fill": "#FFFFFF",
        "stroke_fill": "#8A0000",
        "stroke_width": 3,
        "shadow": True,
        "shadow_color": "#3A0000",
        "shadow_offset": [2, 2],
        "line_spacing": 12,
        "align": "center",
    },
}


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    if not text:
        return []
    lines: list[str] = []
    current = ""
    for ch in text:
        candidate = current + ch
        left, _, right, _ = draw.textbbox((0, 0), candidate, font=font)
        if right - left <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = ch
    if current:
        lines.append(current)
    return lines


def render_block(
    text: str,
    font_path: Path,
    font_size: int,
    max_width: int,
    fill: str,
    stroke_fill: str,
    stroke_width: int,
    shadow: bool,
    shadow_color: str,
    shadow_offset: tuple[int, int],
    line_spacing: int,
    align: str,
    space_as_newline: bool,
) -> tuple[Image.Image | None, dict[str, Any]]:
    if not text:
        return None, {"enabled": False}

    font = ImageFont.truetype(str(font_path), font_size)
    tmp = Image.new("RGBA", (max_width + 100, 2000), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tmp)

    normalized_text = text.replace(" ", "\n") if space_as_newline else text
    if "\n" in normalized_text:
        lines = [ln for ln in normalized_text.split("\n") if ln]
    else:
        lines = wrap_text(draw, normalized_text, font, max_width=max_width)
    if not lines:
        return None, {"enabled": False}

    max_line_w = 0
    line_h = 0
    for ln in lines:
        l, t, r, b = draw.textbbox((0, 0), ln, font=font, stroke_width=stroke_width)
        max_line_w = max(max_line_w, r - l)
        line_h = max(line_h, b - t)
    total_h = len(lines) * line_h + max(0, len(lines) - 1) * line_spacing

    pad = 12 + stroke_width + (max(abs(shadow_offset[0]), abs(shadow_offset[1])) if shadow else 0)
    canvas_w = max_line_w + pad * 2
    canvas_h = total_h + pad * 2
    out = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    od = ImageDraw.Draw(out)

    y = pad
    for ln in lines:
        l, t, r, b = od.textbbox((0, 0), ln, font=font, stroke_width=stroke_width)
        line_w = r - l
        if align == "left":
            x = pad
        elif align == "right":
            x = canvas_w - line_w - pad
        else:
            x = (canvas_w - line_w) // 2
        if shadow:
            od.text(
                (x + shadow_offset[0], y + shadow_offset[1]),
                ln,
                font=font,
                fill=shadow_color,
                stroke_width=stroke_width,
                stroke_fill=shadow_color,
            )
        od.text(
            (x, y),
            ln,
            font=font,
            fill=fill,
            stroke_width=stroke_width,
            stroke_fill=stroke_fill,
        )
        y += line_h + line_spacing

    meta = {
        "enabled": True,
        "text": text,
        "lines": lines,
        "font_path": str(font_path),
        "font_size": font_size,
        "width": out.width,
        "height": out.height,
        "stroke_width": stroke_width,
        "align": align,
    }
    return out, meta


def ensure_font_exists(font_name: str) -> Path:
    p = FONT_DIR / font_name
    if not p.exists():
        raise FileNotFoundError(f"字体不存在: {p}")
    return p


def main() -> None:
    parser = argparse.ArgumentParser(description="渲染文字图层（PNG + JSON）")
    parser.add_argument("--headline", type=str, required=True, help="主标题文案")
    parser.add_argument("--template", type=str, default="clean_red", choices=sorted(TEMPLATES.keys()), help="字体模板（可被下面参数覆盖）")
    parser.add_argument("--font-file", type=str, default="", help="字体文件名（位于 Text/字体库）")
    parser.add_argument("--font-size", type=int, default=0, help="字体大小（0=使用模板默认值）")
    parser.add_argument("--fill", type=str, default="", help="文字颜色，例如 #FFFFFF")
    parser.add_argument("--stroke-fill", type=str, default="", help="描边颜色，例如 #B40000")
    parser.add_argument("--stroke-width", type=int, default=-1, help="描边宽度（-1=使用模板默认值）")
    parser.add_argument("--shadow", action="store_true", help="启用阴影（覆盖模板）")
    parser.add_argument("--no-shadow", action="store_true", help="禁用阴影（覆盖模板）")
    parser.add_argument("--shadow-color", type=str, default="", help="阴影颜色，例如 #2A0000")
    parser.add_argument("--shadow-offset-x", type=int, default=99999, help="阴影X偏移（留空则沿用模板）")
    parser.add_argument("--shadow-offset-y", type=int, default=99999, help="阴影Y偏移（留空则沿用模板）")
    parser.add_argument("--line-spacing", type=int, default=-1, help="行间距（-1=使用模板默认值）")
    parser.add_argument("--align", type=str, default="", choices=["", "left", "center", "right"], help="文字对齐方式")
    parser.add_argument("--space-as-newline", action="store_true", help="将 headline 文案中的空格当作换行符")
    parser.add_argument("--max-width", type=int, default=680, help="单行最大宽度（像素）")
    parser.add_argument("--out-dir", type=str, default="", help="可选，输出目录")
    args = parser.parse_args()

    tpl = dict(TEMPLATES[args.template])
    # 动态覆盖模板：支持用户在输入时自定义格式
    if args.font_file:
        tpl["font_file"] = args.font_file
    if args.font_size > 0:
        tpl["font_size"] = args.font_size
    if args.fill:
        tpl["fill"] = args.fill
    if args.stroke_fill:
        tpl["stroke_fill"] = args.stroke_fill
    if args.stroke_width >= 0:
        tpl["stroke_width"] = args.stroke_width
    if args.shadow:
        tpl["shadow"] = True
    if args.no_shadow:
        tpl["shadow"] = False
    if args.shadow_color:
        tpl["shadow_color"] = args.shadow_color
    if args.shadow_offset_x != 99999:
        tpl["shadow_offset"][0] = args.shadow_offset_x
    if args.shadow_offset_y != 99999:
        tpl["shadow_offset"][1] = args.shadow_offset_y
    if args.line_spacing >= 0:
        tpl["line_spacing"] = args.line_spacing
    if args.align:
        tpl["align"] = args.align

    out_dir = Path(args.out_dir) if args.out_dir else (OUT_DIR / datetime.now().strftime("%Y%m%d_%H%M%S"))
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    fill = ImageColor.getrgb(tpl["fill"])
    stroke_fill = ImageColor.getrgb(tpl["stroke_fill"])
    shadow_color = ImageColor.getrgb(tpl["shadow_color"])
    shadow_offset = (int(tpl["shadow_offset"][0]), int(tpl["shadow_offset"][1]))

    head_img, head_meta = render_block(
        args.headline,
        ensure_font_exists(tpl["font_file"]),
        int(tpl["font_size"]),
        args.max_width,
        fill=fill,
        stroke_fill=stroke_fill,
        stroke_width=int(tpl["stroke_width"]),
        shadow=bool(tpl["shadow"]),
        shadow_color=shadow_color,
        shadow_offset=shadow_offset,
        line_spacing=int(tpl["line_spacing"]),
        align=str(tpl["align"]),
        space_as_newline=bool(args.space_as_newline),
    )

    if head_img:
        head_img.save(out_dir / "headline.png", "PNG")

    # 预览图：将 headline 图层居中放到预览画布
    preview = Image.new("RGBA", (POSTER_SIZE[0], POSTER_SIZE[1]), (30, 30, 30, 255))
    if head_img is not None:
        x = (preview.width - head_img.width) // 2
        y = (preview.height - head_img.height) // 2
        preview.alpha_composite(head_img, (x, y))
    preview.save(out_dir / "preview.png", "PNG")

    meta = {
        "template": args.template,
        "input": {"headline": args.headline},
        "style": {
            "font_file": tpl["font_file"],
            "font_size": int(tpl["font_size"]),
            "fill": tpl["fill"],
            "stroke_fill": tpl["stroke_fill"],
            "stroke_width": int(tpl["stroke_width"]),
            "shadow": bool(tpl["shadow"]),
            "shadow_color": tpl["shadow_color"],
            "shadow_offset": tpl["shadow_offset"],
            "line_spacing": int(tpl["line_spacing"]),
            "align": tpl["align"],
            "space_as_newline": bool(args.space_as_newline),
        },
        "assets": {"headline": head_meta},
        "files": {
            "headline": "headline.png" if head_img else "",
            "preview": "preview.png",
        },
    }
    (out_dir / "text_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"文字图层已生成: {out_dir}")
    print("输出文件: preview.png, text_meta.json, headline.png")


if __name__ == "__main__":
    main()

