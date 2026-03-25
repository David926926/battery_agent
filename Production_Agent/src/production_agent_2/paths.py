from __future__ import annotations

from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = PACKAGE_ROOT.parent.parent
RUNS_ROOT = SOURCE_ROOT / "runs"

CATEGORY_NAMES = {
    "background": "Background",
    "layout": "Layout",
    "object": "Object",
    "text": "Text",
}


def _pick_material_root() -> Path:
    for folder_name in ("resources", "sources"):
        candidate = SOURCE_ROOT / folder_name
        if candidate.exists():
            return candidate
    return SOURCE_ROOT / "sources"


MATERIALS_ROOT = _pick_material_root()

CATEGORY_DIRS = {
    category: MATERIALS_ROOT / folder_name for category, folder_name in CATEGORY_NAMES.items()
}
