from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _default_regions_norm() -> dict[str, dict[str, object]]:
    # 归一化坐标（相对 1:1 画布），用于 1328*1328 / 1024*1024 的通用摆放建议。
    # 这些框仅用于“后期添加”占位建议，生成阶段不实际渲染任何文字/电池/人物。
    return {
        "logo_badge": {
            "type": "logo_badge",
            "box_norm": [0.04, 0.03, 0.32, 0.11],
            "what_to_add": "品牌 Logo/角标（由素材提供）",
            "notes": "建议保持留白边距，避免压到上方信息区。",
        },
        "top_copy_safe_zone": {
            "type": "copy_safe_zone",
            "box_norm": [0.05, 0.14, 0.62, 0.30],
            "what_to_add": "上方文案安全区（如后期需要）",
            "notes": "保持干净留白，方便后期自由添加标题或说明信息。",
        },
        "middle_copy_safe_zone": {
            "type": "copy_safe_zone",
            "box_norm": [0.05, 0.31, 0.62, 0.40],
            "what_to_add": "中部辅助信息区（如后期需要）",
            "notes": "适合补充说明、短标签或留空，不要求实际放文字。",
        },
        "battery_hero": {
            "type": "battery_hero",
            "box_norm": [0.56, 0.20, 0.97, 0.86],
            "what_to_add": "电池体/包装/主体（由 Object 素材后期添加）",
            "notes": "建议主体占比高，并与背景光影匹配（阴影/发光边缘后期可加）。",
        },
        "human_optional": {
            "type": "human_optional",
            "box_norm": [0.45, 0.22, 0.80, 0.80],
            "what_to_add": "可选人物（if applicable，由后期素材决定是否启用）",
            "notes": "若没有人物素材可忽略；若启用需保证不遮挡标题与主体。",
        },
        "promo_bar": {
            "type": "promo_bar",
            "box_norm": [0.02, 0.76, 0.98, 0.97],
            "what_to_add": "底部信息或装饰区（可选）",
            "notes": "可留作装饰、组件承载区，若不需要也可以完全留空。",
        },
    }


def build_placement_plan(
    background_path: str | Path,
    output_dir: str | Path,
    *,
    component_library: dict[str, object] | None = None,
) -> dict[str, str]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    background_path = Path(background_path)
    with Image.open(background_path) as img:
        width, height = img.size
        base = img.convert("RGB")

    regions_norm = _default_regions_norm()
    # 预览图：在背景上画半透明框与文字标签，仅用于可视化对齐建议
    preview = base.convert("RGBA")
    overlay = Image.new("RGBA", preview.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    try:
        font = ImageFont.truetype(str(Path(__file__).parent / "dummy.ttf"), 16)  # type: ignore[arg-type]
    except Exception:
        font = ImageFont.load_default()

    def _norm_to_px(box_norm: list[float]) -> list[int]:
        x1n, y1n, x2n, y2n = box_norm
        return [int(x1n * width), int(y1n * height), int(x2n * width), int(y2n * height)]

    for region_key, region in regions_norm.items():
        box_norm = region["box_norm"]  # type: ignore[assignment]
        box_px = _norm_to_px(box_norm)  # type: ignore[arg-type]
        # outline + fill
        draw.rectangle(box_px, outline=(255, 255, 255, 210), width=3)
        draw.rectangle(box_px, fill=(0, 0, 0, 35))
        label = f"{region_key}"
        draw.text((box_px[0] + 6, box_px[1] + 6), label, fill=(255, 255, 255, 230), font=font)

    preview = Image.alpha_composite(preview, overlay).convert("RGB")

    plan_path = output_dir / "placement_plan.json"
    preview_path = output_dir / "placement_preview.png"
    preview.save(preview_path, format="PNG")

    regions: dict[str, dict[str, object]] = {}
    for region_key, region in regions_norm.items():
        box_norm = region["box_norm"]  # type: ignore[assignment]
        box_px = _norm_to_px(box_norm)  # type: ignore[arg-type]
        regions[region_key] = {
            "type": region["type"],
            "box_norm": box_norm,
            "box_px": box_px,
            "what_to_add": region["what_to_add"],
            "notes": region["notes"],
        }

    payload = {
        "background": {"path": str(background_path), "width": width, "height": height},
        "component_library": component_library or {},
        "regions": regions,
        "z_order_suggestion": [
            "background (底图)",
            "logo_badge / top_copy_safe_zone / middle_copy_safe_zone / promo_bar",
            "battery_hero / human_optional（是否添加由后期需求决定）",
        ],
        "instruction": (
            "生成的背景底图必须保持无文字/无主体。请按 regions 的框在后期自由叠加组件或保持留白；"
            "component_library 列出仓库内可用的组件素材路径，供设计对照选用。"
        ),
    }

    plan_path.write_text(
        __import__("json").dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {"placement_plan": str(plan_path), "placement_preview": str(preview_path)}
