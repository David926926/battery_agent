from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

from production_agent_2.schemas import MaterialAsset


CANVAS_SIZE = (1328, 1328)


def _trim(image: Image.Image, threshold: int = 10) -> Image.Image:
    working = image.convert("RGBA")
    alpha = working.getchannel("A").point(lambda value: 255 if value > threshold else 0)
    bbox = alpha.getbbox()
    if not bbox:
        return working
    return working.crop(bbox)


def _cover(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    working = image.convert("RGBA")
    scale = max(size[0] / working.width, size[1] / working.height)
    resized = working.resize((int(working.width * scale), int(working.height * scale)), Image.LANCZOS)
    left = max(0, (resized.width - size[0]) // 2)
    top = max(0, (resized.height - size[1]) // 2)
    return resized.crop((left, top, left + size[0], top + size[1]))


def _contain(image: Image.Image, width: int | None = None, height: int | None = None) -> Image.Image:
    working = _trim(image)
    if width is None and height is None:
        return working
    if width is not None and height is not None:
        ratio = min(width / working.width, height / working.height)
    elif width is not None:
        ratio = width / working.width
    else:
        ratio = height / working.height
    ratio = max(ratio, 0.01)
    return working.resize((int(working.width * ratio), int(working.height * ratio)), Image.LANCZOS)


def _alpha(image: Image.Image, opacity: int) -> Image.Image:
    working = image.convert("RGBA")
    alpha = working.getchannel("A").point(lambda value: value * opacity // 255)
    working.putalpha(alpha)
    return working


def _shadow(layer: Image.Image, blur: int = 30, strength: int = 105, y_scale: float = 1.0) -> Image.Image:
    width = max(1, int(layer.width))
    height = max(1, int(layer.height * y_scale))
    shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    alpha = layer.getchannel("A").resize((width, height), Image.LANCZOS).point(lambda value: strength if value else 0)
    shadow.putalpha(alpha)
    return shadow.filter(ImageFilter.GaussianBlur(blur))


def _radial_glow(size: tuple[int, int], color: tuple[int, int, int], strength: int = 160) -> Image.Image:
    width, height = size
    glow = Image.new("RGBA", size, (0, 0, 0, 0))
    cx = width / 2
    cy = height / 2
    max_dist = (cx**2 + cy**2) ** 0.5
    pixels: list[tuple[int, int, int, int]] = []
    for y in range(height):
        for x in range(width):
            dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            ratio = max(0.0, 1.0 - dist / max_dist)
            alpha = int((ratio**2.3) * strength)
            pixels.append((color[0], color[1], color[2], alpha))
    glow.putdata(pixels)
    return glow


def _screen(base: Image.Image, overlay: Image.Image) -> Image.Image:
    return ImageChops.screen(base.convert("RGB"), overlay.convert("RGB")).convert("RGBA")


def _linear_vertical_gradient(
    size: tuple[int, int],
    top: tuple[int, int, int],
    bottom: tuple[int, int, int],
) -> Image.Image:
    width, height = size
    image = Image.new("RGBA", size, (0, 0, 0, 255))
    draw = ImageDraw.Draw(image)
    for y in range(height):
        ratio = y / max(height - 1, 1)
        color = tuple(int(top[i] * (1 - ratio) + bottom[i] * ratio) for i in range(3))
        draw.line((0, y, width, y), fill=(*color, 255))
    return image


def _ellipse_glow(size: tuple[int, int], color: tuple[int, int, int], blur: int = 30, strength: int = 180) -> Image.Image:
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((0, 0, size[0] - 1, size[1] - 1), fill=(*color, strength))
    return image.filter(ImageFilter.GaussianBlur(blur))


def _rounded_panel(size: tuple[int, int], radius: int, fill: tuple[int, int, int, int], outline: tuple[int, int, int, int] | None = None) -> Image.Image:
    panel = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(panel)
    draw.rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=radius, fill=fill, outline=outline, width=2)
    return panel


def _find_first(assets: list[MaterialAsset], predicate) -> MaterialAsset | None:
    for asset in assets:
        if predicate(asset):
            return asset
    return None


def _classify_objects(assets: list[MaterialAsset]) -> dict[str, MaterialAsset | None]:
    stats = []
    for asset in assets:
        with Image.open(asset.path) as image:
            trimmed = _trim(image)
        aspect = trimmed.height / max(trimmed.width, 1)
        wide_ratio = trimmed.width / max(trimmed.height, 1)
        stats.append((asset, aspect, wide_ratio, trimmed.width * trimmed.height))
    hero = next((asset for asset, aspect, _, _ in sorted(stats, key=lambda item: item[1], reverse=True) if aspect > 2.0), None)
    package = next(
        (
            asset
            for asset, _, wide_ratio, _ in sorted(stats, key=lambda item: item[2], reverse=True)
            if wide_ratio > 1.35 and asset is not hero
        ),
        None,
    )
    excluded_ids = {item.asset_id for item in (hero, package) if item is not None}
    portrait = next((asset for asset, _, _, _ in stats if asset.asset_id not in excluded_ids), None)
    return {"hero": hero, "package": package, "portrait": portrait}


def _classify_texts(assets: list[MaterialAsset]) -> dict[str, list[MaterialAsset]]:
    sorted_by_area = sorted(assets, key=lambda item: item.width * item.height, reverse=True)
    headline = sorted_by_area[:1]
    secondary = sorted_by_area[1:2]
    badges = sorted_by_area[2:]
    return {"headline": headline, "secondary": secondary, "badges": badges}


def _paste_with_shadow(canvas: Image.Image, layer: Image.Image, position: tuple[int, int], *, shadow_blur: int = 28) -> None:
    shadow = _shadow(layer, blur=shadow_blur)
    canvas.alpha_composite(shadow, (position[0] + 20, position[1] + 26))
    canvas.alpha_composite(layer, position)


def compose_material_draft(grouped_assets: dict[str, list[MaterialAsset]], output_path: Path) -> dict[str, object]:
    canvas = _linear_vertical_gradient(CANVAS_SIZE, (8, 10, 16), (6, 7, 12))
    placements: list[dict[str, object]] = []
    width, height = CANVAS_SIZE

    layout_assets = grouped_assets.get("layout", [])
    background_assets = grouped_assets.get("background", [])

    if layout_assets:
        with Image.open(layout_assets[0].path) as image:
            base_layout = _cover(image, CANVAS_SIZE)
        top_band = base_layout.crop((0, 0, width, 170)).filter(ImageFilter.GaussianBlur(2))
        canvas.alpha_composite(_alpha(top_band, 170), (0, 0))
        placements.append({"asset_id": layout_assets[0].asset_id, "role": "layout_top_band", "x": 0, "y": 0})

    if background_assets:
        with Image.open(background_assets[0].path) as image:
            bg = _cover(image, (820, 820))
        bg = _alpha(bg.filter(ImageFilter.GaussianBlur(6)), 135)
        hero_mask = _ellipse_glow((820, 820), (60, 200, 255), blur=40, strength=255).getchannel("A")
        bg.putalpha(hero_mask)
        canvas = _screen(canvas, bg)
        placements.append({"asset_id": background_assets[0].asset_id, "role": "background_fx", "x": 520, "y": 180})

    left_panel = _rounded_panel((470, 1030), 42, (4, 8, 18, 168), outline=(199, 156, 45, 72))
    canvas.alpha_composite(left_panel, (34, 62))
    canvas.alpha_composite(_ellipse_glow((540, 420), (216, 165, 38), blur=56, strength=58), (-40, 780))
    canvas.alpha_composite(_ellipse_glow((840, 840), (30, 140, 255), blur=42, strength=88), (450, 150))

    object_roles = _classify_objects(grouped_assets.get("object", []))
    hero_asset = object_roles["hero"]
    package_asset = object_roles["package"]
    portrait_asset = object_roles["portrait"]

    if hero_asset:
        with Image.open(hero_asset.path) as image:
            hero = _contain(image, height=820)
        hero_x = 748
        hero_y = 134
        _paste_with_shadow(canvas, hero, (hero_x, hero_y), shadow_blur=36)
        placements.append(
            {
                "asset_id": hero_asset.asset_id,
                "role": "hero_object",
                "x": hero_x,
                "y": hero_y,
                "width": hero.width,
                "height": hero.height,
            }
        )

    if package_asset:
        with Image.open(package_asset.path) as image:
            pack = _contain(image, width=330)
        pack_x = 884
        pack_y = 968
        package_panel = _rounded_panel((380, 210), 28, (8, 10, 16, 126), outline=(223, 178, 58, 62))
        canvas.alpha_composite(package_panel, (850, 930))
        _paste_with_shadow(canvas, pack, (pack_x, pack_y), shadow_blur=24)
        placements.append(
            {
                "asset_id": package_asset.asset_id,
                "role": "package_object",
                "x": pack_x,
                "y": pack_y,
                "width": pack.width,
                "height": pack.height,
            }
        )

    if portrait_asset:
        with Image.open(portrait_asset.path) as image:
            portrait = _contain(image, height=236)
        frame = _rounded_panel((portrait.width + 44, portrait.height + 44), 28, (10, 10, 12, 170), outline=(214, 169, 52, 82))
        frame.alpha_composite(_ellipse_glow(frame.size, (238, 180, 60), blur=24, strength=58), (0, 0))
        frame.alpha_composite(portrait, (22, 22))
        portrait_x = 72
        portrait_y = 972
        _paste_with_shadow(canvas, frame, (portrait_x, portrait_y), shadow_blur=22)
        placements.append(
            {
                "asset_id": portrait_asset.asset_id,
                "role": "portrait_object",
                "x": portrait_x,
                "y": portrait_y,
                "width": frame.width,
                "height": frame.height,
            }
        )

    text_roles = _classify_texts(grouped_assets.get("text", []))
    headline_asset = text_roles["headline"][0] if text_roles["headline"] else None
    secondary_asset = text_roles["secondary"][0] if text_roles["secondary"] else None
    badge_assets = text_roles["badges"]

    left_col_x = 68
    top_y = 86

    if headline_asset:
        with Image.open(headline_asset.path) as image:
            headline = _contain(image, width=440)
        canvas.alpha_composite(headline, (left_col_x, top_y))
        placements.append(
            {
                "asset_id": headline_asset.asset_id,
                "role": "headline_text",
                "x": left_col_x,
                "y": top_y,
                "width": headline.width,
                "height": headline.height,
            }
        )
        top_y += headline.height + 44

    if secondary_asset:
        with Image.open(secondary_asset.path) as image:
            secondary = _contain(image, width=360)
        canvas.alpha_composite(secondary, (left_col_x, top_y))
        placements.append(
            {
                "asset_id": secondary_asset.asset_id,
                "role": "secondary_text",
                "x": left_col_x,
                "y": top_y,
                "width": secondary.width,
                "height": secondary.height,
            }
        )
        top_y += secondary.height + 40

    badge_cursor_x = 70
    badge_cursor_y = min(top_y + 14, 770)
    for asset in badge_assets[:3]:
        with Image.open(asset.path) as image:
            badge = _contain(image, width=220)
        if badge_cursor_x + badge.width > 440:
            badge_cursor_x = 70
            badge_cursor_y += badge.height + 16
        badge_panel = _rounded_panel((badge.width + 28, badge.height + 18), 22, (10, 12, 20, 182), outline=(209, 168, 64, 78))
        badge_panel.alpha_composite(badge, (14, 9))
        canvas.alpha_composite(badge_panel, (badge_cursor_x, badge_cursor_y))
        placements.append(
            {
                "asset_id": asset.asset_id,
                "role": "badge_text",
                "x": badge_cursor_x,
                "y": badge_cursor_y,
                "width": badge_panel.width,
                "height": badge_panel.height,
            }
        )
        badge_cursor_x += badge_panel.width + 14

    if hero_asset:
        floor_glow = _ellipse_glow((540, 160), (50, 180, 255), blur=18, strength=110)
        canvas.alpha_composite(floor_glow, (710, 930))

    vignette = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    vignette_draw = ImageDraw.Draw(vignette)
    vignette_draw.rectangle((0, 0, width, height), fill=(0, 0, 0, 26))
    vignette = vignette.filter(ImageFilter.GaussianBlur(26))
    canvas.alpha_composite(vignette, (0, 0))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output_path, format="PNG")
    return {"path": str(output_path), "placements": placements, "size": list(CANVAS_SIZE)}


def compose_final_poster(
    grouped_assets: dict[str, list[MaterialAsset]],
    background_path: str,
    output_path: Path,
) -> dict[str, object]:
    with Image.open(background_path) as image:
        canvas = _cover(image, CANVAS_SIZE).convert("RGBA")

    placements: list[dict[str, object]] = []
    width, height = CANVAS_SIZE

    layout_assets = grouped_assets.get("layout", [])
    if layout_assets:
        with Image.open(layout_assets[0].path) as image:
            layout_overlay = _cover(image, CANVAS_SIZE)
        canvas.alpha_composite(_alpha(layout_overlay, 36), (0, 0))
        placements.append({"asset_id": layout_assets[0].asset_id, "role": "layout_hint", "x": 0, "y": 0})

    object_roles = _classify_objects(grouped_assets.get("object", []))
    hero_asset = object_roles["hero"]
    package_asset = object_roles["package"]
    portrait_asset = object_roles["portrait"]

    if hero_asset:
        with Image.open(hero_asset.path) as image:
            hero = _contain(image, height=760)
        hero_x = 760
        hero_y = 160
        _paste_with_shadow(canvas, hero, (hero_x, hero_y), shadow_blur=28)
        placements.append({"asset_id": hero_asset.asset_id, "role": "hero_object", "x": hero_x, "y": hero_y, "width": hero.width, "height": hero.height})

    if package_asset:
        with Image.open(package_asset.path) as image:
            pack = _contain(image, width=280)
        pack_x = 932
        pack_y = 976
        _paste_with_shadow(canvas, pack, (pack_x, pack_y), shadow_blur=18)
        placements.append({"asset_id": package_asset.asset_id, "role": "package_object", "x": pack_x, "y": pack_y, "width": pack.width, "height": pack.height})

    if portrait_asset:
        with Image.open(portrait_asset.path) as image:
            portrait = _contain(image, height=250)
        portrait_x = 94
        portrait_y = 955
        _paste_with_shadow(canvas, portrait, (portrait_x, portrait_y), shadow_blur=16)
        placements.append({"asset_id": portrait_asset.asset_id, "role": "portrait_object", "x": portrait_x, "y": portrait_y, "width": portrait.width, "height": portrait.height})

    text_roles = _classify_texts(grouped_assets.get("text", []))
    headline_asset = text_roles["headline"][0] if text_roles["headline"] else None
    secondary_asset = text_roles["secondary"][0] if text_roles["secondary"] else None
    badge_assets = text_roles["badges"]

    left_col_x = 66
    top_y = 92

    if headline_asset:
        with Image.open(headline_asset.path) as image:
            headline = _contain(image, width=470)
        canvas.alpha_composite(headline, (left_col_x, top_y))
        placements.append({"asset_id": headline_asset.asset_id, "role": "headline_text", "x": left_col_x, "y": top_y, "width": headline.width, "height": headline.height})
        top_y += headline.height + 38

    if secondary_asset:
        with Image.open(secondary_asset.path) as image:
            secondary = _contain(image, width=320)
        canvas.alpha_composite(secondary, (left_col_x, top_y))
        placements.append({"asset_id": secondary_asset.asset_id, "role": "secondary_text", "x": left_col_x, "y": top_y, "width": secondary.width, "height": secondary.height})
        top_y += secondary.height + 34

    badge_cursor_x = left_col_x
    badge_cursor_y = min(top_y + 18, 760)
    for asset in badge_assets[:3]:
        with Image.open(asset.path) as image:
            badge = _contain(image, width=210)
        canvas.alpha_composite(badge, (badge_cursor_x, badge_cursor_y))
        placements.append({"asset_id": asset.asset_id, "role": "badge_text", "x": badge_cursor_x, "y": badge_cursor_y, "width": badge.width, "height": badge.height})
        badge_cursor_y += badge.height + 22

    floor_glow = _ellipse_glow((520, 150), (45, 170, 255), blur=24, strength=95)
    canvas.alpha_composite(floor_glow, (720, 930))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output_path, format="PNG")
    return {"path": str(output_path), "placements": placements, "size": list(CANVAS_SIZE), "background_path": background_path}


def export_layer_bundle(
    grouped_assets: dict[str, list[MaterialAsset]],
    output_dir: Path,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    width, height = CANVAS_SIZE
    placements: list[dict[str, object]] = []

    background_layer = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    layout_hint_layer = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    object_layer = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    text_layer = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))

    background_assets = grouped_assets.get("background", [])
    if background_assets:
        with Image.open(background_assets[0].path) as image:
            bg = _cover(image, CANVAS_SIZE)
        background_layer.alpha_composite(bg, (0, 0))
        placements.append({"asset_id": background_assets[0].asset_id, "role": "background_base", "x": 0, "y": 0})

    layout_assets = grouped_assets.get("layout", [])
    if layout_assets:
        with Image.open(layout_assets[0].path) as image:
            layout = _cover(image, CANVAS_SIZE)
        layout_hint_layer.alpha_composite(_alpha(layout, 56), (0, 0))
        placements.append({"asset_id": layout_assets[0].asset_id, "role": "layout_hint", "x": 0, "y": 0})

    object_roles = _classify_objects(grouped_assets.get("object", []))
    hero_asset = object_roles["hero"]
    package_asset = object_roles["package"]
    portrait_asset = object_roles["portrait"]

    if hero_asset:
        with Image.open(hero_asset.path) as image:
            hero = _contain(image, height=760)
        hero_x = 760
        hero_y = 160
        _paste_with_shadow(object_layer, hero, (hero_x, hero_y), shadow_blur=28)
        placements.append({"asset_id": hero_asset.asset_id, "role": "hero_object", "x": hero_x, "y": hero_y, "width": hero.width, "height": hero.height})

    if package_asset:
        with Image.open(package_asset.path) as image:
            pack = _contain(image, width=280)
        pack_x = 932
        pack_y = 976
        _paste_with_shadow(object_layer, pack, (pack_x, pack_y), shadow_blur=18)
        placements.append({"asset_id": package_asset.asset_id, "role": "package_object", "x": pack_x, "y": pack_y, "width": pack.width, "height": pack.height})

    if portrait_asset:
        with Image.open(portrait_asset.path) as image:
            portrait = _contain(image, height=250)
        portrait_x = 94
        portrait_y = 955
        _paste_with_shadow(object_layer, portrait, (portrait_x, portrait_y), shadow_blur=16)
        placements.append({"asset_id": portrait_asset.asset_id, "role": "portrait_object", "x": portrait_x, "y": portrait_y, "width": portrait.width, "height": portrait.height})

    text_roles = _classify_texts(grouped_assets.get("text", []))
    headline_asset = text_roles["headline"][0] if text_roles["headline"] else None
    secondary_asset = text_roles["secondary"][0] if text_roles["secondary"] else None
    badge_assets = text_roles["badges"]

    left_col_x = 66
    top_y = 92

    if headline_asset:
        with Image.open(headline_asset.path) as image:
            headline = _contain(image, width=470)
        text_layer.alpha_composite(headline, (left_col_x, top_y))
        placements.append({"asset_id": headline_asset.asset_id, "role": "headline_text", "x": left_col_x, "y": top_y, "width": headline.width, "height": headline.height})
        top_y += headline.height + 38

    if secondary_asset:
        with Image.open(secondary_asset.path) as image:
            secondary = _contain(image, width=320)
        text_layer.alpha_composite(secondary, (left_col_x, top_y))
        placements.append({"asset_id": secondary_asset.asset_id, "role": "secondary_text", "x": left_col_x, "y": top_y, "width": secondary.width, "height": secondary.height})
        top_y += secondary.height + 34

    badge_cursor_x = left_col_x
    badge_cursor_y = min(top_y + 18, 760)
    for asset in badge_assets[:3]:
        with Image.open(asset.path) as image:
            badge = _contain(image, width=210)
        text_layer.alpha_composite(badge, (badge_cursor_x, badge_cursor_y))
        placements.append({"asset_id": asset.asset_id, "role": "badge_text", "x": badge_cursor_x, "y": badge_cursor_y, "width": badge.width, "height": badge.height})
        badge_cursor_y += badge.height + 22

    final_preview = background_layer.copy()
    final_preview.alpha_composite(layout_hint_layer, (0, 0))
    final_preview.alpha_composite(object_layer, (0, 0))
    final_preview.alpha_composite(text_layer, (0, 0))

    background_path = output_dir / "background_base.png"
    layout_path = output_dir / "layout_hint.png"
    object_path = output_dir / "object_cluster.png"
    text_path = output_dir / "text_cluster.png"
    preview_path = output_dir / "final_preview.png"

    background_layer.convert("RGBA").save(background_path, format="PNG")
    layout_hint_layer.convert("RGBA").save(layout_path, format="PNG")
    object_layer.convert("RGBA").save(object_path, format="PNG")
    text_layer.convert("RGBA").save(text_path, format="PNG")
    final_preview.convert("RGB").save(preview_path, format="PNG")

    return {
        "background_base": str(background_path),
        "layout_hint": str(layout_path),
        "object_cluster": str(object_path),
        "text_cluster": str(text_path),
        "final_preview": str(preview_path),
        "layout_plan": placements,
        "size": list(CANVAS_SIZE),
    }
