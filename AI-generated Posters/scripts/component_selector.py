"""
从 Input Component 中选取组件（图片路径）。
支持三种模式：
  1. use_panda=True：仅出海熊猫+出海电池体
  2. use_panda=False：从除熊猫外的所有组选
  3. groups=["电池体","电商彩盒","马龙"]：自定义指定组合

用法：
  from component_selector import pick_components, pick_from_groups
  paths = pick_components(use_panda=True)
  paths = pick_from_groups(["电池体", "电商彩盒", "马龙"])
"""
import random
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
INPUT_COMPONENT = ROOT / "Input Component"

ALL_GROUPS = ["电商彩盒", "出海电池体", "出海熊猫", "电池体", "挂卡", "马龙"]


def _list_images(dir_path: Path) -> list[Path]:
    if not dir_path.is_dir():
        return []
    out = []
    for ext in ("*.png", "*.jpg", "*.jpeg"):
        out.extend(dir_path.glob(ext))
    return sorted(out)


def _pick_one_from_group(group_name: str) -> Path | None:
    """从指定组中随机取一张图。电池体会遍历 5号/7号 子目录。"""
    folder = INPUT_COMPONENT / group_name
    if not folder.is_dir():
        return None
    if group_name == "电池体":
        for sub in sorted(folder.iterdir()):
            if sub.is_dir():
                imgs = _list_images(sub)
                if imgs:
                    return random.choice(imgs)
        return None
    imgs = _list_images(folder)
    return random.choice(imgs) if imgs else None


def pick_from_groups(groups: list[str]) -> list[Path]:
    """
    从指定的组列表中各选 1 张图。
    仍然遵守出海熊猫规则：如果选了出海熊猫，自动加入出海电池体；
    不允许出海熊猫与电商彩盒/挂卡/电池体同时出现。
    """
    has_panda = "出海熊猫" in groups
    if has_panda:
        forbidden_with_panda = {"电商彩盒", "挂卡", "电池体"}
        conflict = set(groups) & forbidden_with_panda
        if conflict:
            print(f"Warning: 出海熊猫不能与 {conflict} 同时使用，已自动移除冲突组。")
            groups = [g for g in groups if g not in forbidden_with_panda]
        if "出海电池体" not in groups:
            groups.append("出海电池体")

    result = []
    for g in groups:
        path = _pick_one_from_group(g)
        if path:
            result.append(path)
        else:
            print(f"Warning: 组 '{g}' 中未找到图片，跳过。")
    return result


def pick_components(use_panda: bool = False) -> list[Path]:
    """兼容旧接口。use_panda=True 选熊猫+出海电池体，False 选其他所有。"""
    if use_panda:
        return pick_from_groups(["出海熊猫", "出海电池体"])
    return pick_from_groups(["电商彩盒", "出海电池体", "电池体", "挂卡", "马龙"])
