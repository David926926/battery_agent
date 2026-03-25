#!/usr/bin/env python3
"""
主流程：从 Input Component 选组件、从 lines.txt 随机选一条文案，读取 Prompt，
保存到 output/prompt_job.json 供 call_image_api.py 使用。

用法:
  python scripts/generate_poster.py --groups 电池体,电商彩盒,马龙 --dry-run
  python scripts/generate_poster.py --groups 出海熊猫,出海电池体 --dry-run
  python scripts/generate_poster.py --use-panda 1 --dry-run
  python scripts/generate_poster.py --dry-run
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from component_selector import pick_components, pick_from_groups, ALL_GROUPS
from copy_selector import load_lines, pick_one


def load_prompt() -> str:
    path = ROOT / "prompts" / "nanfu_ecommerce_main_prompt.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def main():
    parser = argparse.ArgumentParser(description="选组件 + 选文案，生成 prompt_job.json")
    parser.add_argument("--type", choices=["主图商详", "投放素材"], default="主图商详", help="海报类型")
    parser.add_argument("--groups", type=str, default=None,
                        help=f"自定义组合，逗号分隔，可选: {','.join(ALL_GROUPS)}")
    parser.add_argument("--use-panda", type=int, default=None, choices=[0, 1],
                        help="（旧参数）1=出海熊猫+出海电池体, 0=其他组。推荐用 --groups 替代")
    parser.add_argument("--dry-run", action="store_true", help="仅保存 prompt_job.json")
    args = parser.parse_args()

    if args.groups:
        groups = [g.strip() for g in args.groups.split(",") if g.strip()]
        invalid = [g for g in groups if g not in ALL_GROUPS]
        if invalid:
            print(f"Error: 不认识的组名 {invalid}", file=sys.stderr)
            print(f"可选: {ALL_GROUPS}", file=sys.stderr)
            sys.exit(1)
        component_paths = pick_from_groups(groups)
    elif args.use_panda is not None:
        component_paths = pick_components(use_panda=bool(args.use_panda))
    else:
        component_paths = pick_components(use_panda=False)

    if not component_paths:
        print("Warning: 未找到组件图片，请检查 Input Component 文件夹。", file=sys.stderr)

    lines = load_lines()
    copy_line = pick_one(lines)

    prompt_text = load_prompt()
    prompt_text = prompt_text.replace("{copy_line}", copy_line)

    out_dir = ROOT / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    job = {
        "prompt": prompt_text,
        "component_paths": [str(p) for p in component_paths],
        "copy_line": copy_line,
        "poster_type": args.type,
    }
    job_path = out_dir / "prompt_job.json"
    with open(job_path, "w", encoding="utf-8") as f:
        json.dump(job, f, ensure_ascii=False, indent=2)

    print(f"prompt_job.json 已保存到 {job_path}")
    print(f"组件图片: {[str(p) for p in component_paths]}")
    print(f"选中文案: {copy_line}")


if __name__ == "__main__":
    main()
