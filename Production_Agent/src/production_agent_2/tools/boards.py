from __future__ import annotations

from math import ceil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from production_agent_2.schemas import MaterialAsset, ReferenceBoard


def _fit_image(image: Image.Image, box_size: tuple[int, int]) -> Image.Image:
    working = image.convert("RGBA")
    working.thumbnail(box_size, Image.LANCZOS)
    canvas = Image.new("RGBA", box_size, (245, 245, 245, 255))
    x = (box_size[0] - working.width) // 2
    y = (box_size[1] - working.height) // 2
    canvas.alpha_composite(working, (x, y))
    return canvas


def create_reference_board(
    board_id: str,
    category: str,
    assets: list[MaterialAsset],
    output_path: Path,
    note: str,
) -> ReferenceBoard:
    tile_w = 720
    tile_h = 720
    caption_h = 44
    cols = 2 if len(assets) > 1 else 1
    rows = ceil(len(assets) / cols) or 1
    board = Image.new("RGB", (cols * tile_w, rows * (tile_h + caption_h)), (255, 255, 255))
    draw = ImageDraw.Draw(board)
    font = ImageFont.load_default()

    for idx, asset in enumerate(assets):
        col = idx % cols
        row = idx // cols
        x = col * tile_w
        y = row * (tile_h + caption_h)
        with Image.open(asset.path) as image:
            tile = _fit_image(image, (tile_w, tile_h))
        board.paste(tile.convert("RGB"), (x, y))
        draw.rectangle((x, y + tile_h, x + tile_w, y + tile_h + caption_h), fill=(248, 214, 66))
        draw.text((x + 12, y + tile_h + 14), asset.filename, fill=(20, 20, 20), font=font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    board.save(output_path, format="PNG")
    return ReferenceBoard(
        board_id=board_id,
        category=category,
        source_asset_ids=[asset.asset_id for asset in assets],
        path=str(output_path),
        note=note,
    )
