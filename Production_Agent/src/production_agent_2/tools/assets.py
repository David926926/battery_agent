from __future__ import annotations

from PIL import Image

from production_agent_2.paths import CATEGORY_DIRS, MATERIALS_ROOT
from production_agent_2.schemas import MaterialAsset


VALID_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def load_assets() -> list[MaterialAsset]:
    assets: list[MaterialAsset] = []
    for category, folder in CATEGORY_DIRS.items():
        if not folder.exists():
            continue
        for path in sorted(folder.rglob("*")):
            if path.is_dir():
                continue
            if path.name.startswith(".") or path.suffix.lower() not in VALID_SUFFIXES:
                continue
            relative_path = path.relative_to(MATERIALS_ROOT)
            with Image.open(path) as image:
                assets.append(
                    MaterialAsset(
                        asset_id=f"{category}:{relative_path.as_posix()}",
                        category=category,  # type: ignore[arg-type]
                        path=str(path),
                        filename=relative_path.as_posix(),
                        width=image.width,
                        height=image.height,
                        mode=image.mode,
                    )
                )
    return assets


def assets_by_category(assets: list[MaterialAsset]) -> dict[str, list[MaterialAsset]]:
    grouped: dict[str, list[MaterialAsset]] = {}
    for asset in assets:
        grouped.setdefault(asset.category, []).append(asset)
    return grouped
