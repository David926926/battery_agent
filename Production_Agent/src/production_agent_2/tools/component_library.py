from __future__ import annotations

from pathlib import Path

from production_agent_2.paths import SOURCE_ROOT

VALID_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
# 与 load_assets 的四类目录名一致；其余子目录视为「组件素材库」
LEGACY_CATEGORY_FOLDERS = frozenset({"Background", "Layout", "Object", "Text"})


def scan_component_library(max_files_per_group: int = 80) -> dict[str, object]:
    """
    扫描 Production_Agent/sources 下除四类 legacy 目录外的子目录，
    汇总可作为后期合成的组件素材路径（相对仓库 Production_Agent/sources）。
    """
    root = SOURCE_ROOT / "sources"
    if not root.exists():
        return {"root": None, "groups": {}, "root_level_files": []}

    groups: dict[str, list[str]] = {}
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith(".") or child.name in LEGACY_CATEGORY_FOLDERS:
            continue
        paths: list[str] = []
        for path in sorted(child.rglob("*")):
            if path.is_dir():
                continue
            if path.name.startswith(".") or path.suffix.lower() not in VALID_SUFFIXES:
                continue
            paths.append(str(path))
            if len(paths) >= max_files_per_group:
                break
        if paths:
            groups[child.name] = paths

    root_files: list[str] = []
    for path in sorted(root.iterdir()):
        if path.is_file() and path.suffix.lower() in VALID_SUFFIXES and not path.name.startswith("."):
            root_files.append(str(path))

    return {
        "root": str(root),
        "groups": groups,
        "root_level_files": root_files,
    }
