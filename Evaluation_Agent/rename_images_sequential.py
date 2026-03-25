import argparse
import uuid
from pathlib import Path
from typing import List

'''
# 真正执行改名
python3 rename_images_sequential.py \
  --input-dir "/Users/liyuanheng/Desktop/Battery Agent/Samples/3.9/初代生产智能体图片" \
  --no-dry-run
'''


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="将目录内图片重命名为 1~n（保留扩展名）。"
    )
    parser.add_argument("--input-dir", required=True, help="要处理的目录")
    parser.add_argument(
        "--recursive",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="是否递归处理子目录（默认 false）",
    )
    parser.add_argument("--start", type=int, default=1, help="起始序号（默认 1）")
    parser.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="仅预览改名结果，不实际执行（默认 true）",
    )
    return parser.parse_args()


def list_images(input_dir: Path, recursive: bool) -> List[Path]:
    candidates = input_dir.rglob("*") if recursive else input_dir.glob("*")
    images = [p for p in candidates if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
    return sorted(images, key=lambda p: str(p.relative_to(input_dir)).lower())


def build_rename_plan(files: List[Path], start: int) -> List[tuple[Path, Path]]:
    plan = []
    idx = start
    for src in files:
        dst = src.with_name(f"{idx}{src.suffix.lower()}")
        plan.append((src, dst))
        idx += 1
    return plan


def execute_rename(plan: List[tuple[Path, Path]], dry_run: bool) -> None:
    if dry_run:
        for src, dst in plan:
            print(f"[DRY-RUN] {src} -> {dst}")
        return

    # 两阶段重命名，避免目标文件名冲突
    temp_pairs: List[tuple[Path, Path]] = []
    for src, _ in plan:
        temp = src.with_name(f".tmp_rename_{uuid.uuid4().hex}{src.suffix.lower()}")
        src.rename(temp)
        temp_pairs.append((temp, src))

    for (temp, original_src), (_, final_dst) in zip(temp_pairs, plan):
        # zip 中第二项的 src 与 original_src 是同顺序对应的
        _ = original_src
        temp.rename(final_dst)
        print(f"{temp} -> {final_dst}")


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input_dir).expanduser().resolve()
    if not input_dir.exists() or not input_dir.is_dir():
        raise RuntimeError(f"输入目录不存在或不是目录: {input_dir}")
    if args.start < 1:
        raise RuntimeError("--start 必须 >= 1")

    files = list_images(input_dir, recursive=args.recursive)
    if not files:
        print("未找到可处理的图片文件。")
        return

    plan = build_rename_plan(files, start=args.start)
    print(f"共 {len(plan)} 张图片，dry_run={args.dry_run}。")
    execute_rename(plan, dry_run=args.dry_run)
    if not args.dry_run:
        print("重命名完成。")


if __name__ == "__main__":
    main()
