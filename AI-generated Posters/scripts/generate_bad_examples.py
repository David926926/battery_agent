#!/usr/bin/env python3
"""
根据 main_detail_issue_tags.json，为每个质检问题标签自动生成“不良示例”海报。

用法示例：
  python scripts/generate_bad_examples.py
  python scripts/generate_bad_examples.py --dims Background,Object --n-per-issue 2

输出目录：
  output/bad_examples/<Dimension>/<IssueTag>/bad_1.png, bad_2.png
"""
import argparse
import json
import sys
import io
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from call_image_api import generate_poster  # type: ignore
from component_selector import pick_from_groups  # type: ignore


ISSUE_PROMPT_SUFFIX = {
    "Background": {
        "场景无关": (
            "在保证主体仍然是南孚电池产品的前提下，请故意让背景与产品使用场景明显无关，"
            "例如把电池放在与日常使用完全不匹配的环境中，让人一眼觉得场景不相关。"
        ),
        "背景杂乱或噪点过多": (
            "请在背景中加入大量杂乱的纹理、噪点或过多无关装饰元素，让背景显得非常拥挤和嘈杂。"
        ),
        "明显的“AI生成”痕迹": (
            "请故意让背景中出现较为明显的 AI 生成痕迹，例如不自然的纹理、重复的图案或违和的细节。"
        ),
        "人物或物体部位缺失/断裂": (
            "如果画面中出现人物或物体，请故意让其有部分肢体或边缘缺失、断裂，看起来不完整。"
        ),
        "明显拼贴或合成痕迹": (
            "请让背景与前景之间的融合不自然，产生明显的拼贴或抠图合成感，让人一眼看出是拼出来的。"
        ),
    },
    "Object": {
        "产品包装文字模糊或不可读": (
            "请故意让产品包装上的文字变得模糊、难以辨认，看不清楚具体内容。"
        ),
        "物体轮廓不完整（缺失或被裁切）": (
            "请故意把产品主体的边缘裁切掉一部分，让产品轮廓不完整，看起来被截断。"
        ),
        "多余或重复部件（轮廓异常延展）": (
            "请在产品周围或表面故意生成多余或重复的部件，让轮廓出现异常延展或重复。"
        ),
        "物体摆放或姿态不符合物理逻辑": (
            "请让产品的摆放方式明显违背物理常识，例如悬空、倾斜得不自然等。"
        ),
        "光影或透视与场景不一致": (
            "请让产品的光影方向或透视关系与背景场景不一致，产生明显违和感。"
        ),
        "比例或尺度不合理": (
            "请故意把产品的大小比例设置得非常不合理，例如比周围常见物体大得离谱或小得离谱。"
        ),
        "未展示产品实物细节（增强确定性）": (
            "请让画面中几乎看不到产品的实物细节，只能模糊感知有产品存在，缺乏明确的细节展示。"
        ),
    },
    "Text": {
        "行距或断行不合理": (
            "请在文字排版上故意做出不合理的断行和行距，例如在句子中间随意换行，"
            "或把行距拉得忽宽忽窄，让文案显得很别扭。"
        ),
        "风格与品牌或海报调性不符": (
            "请故意选择一种与南孚品牌调性和整体画面风格严重不符的字体或文字风格，"
            "例如过于花哨、太童趣或与高端感相反的风格。"
        ),
        "笔画渲染错误": (
            "请故意让中文字的笔画出现渲染错误，例如缺笔少画、连接错乱等，让文字看起来不正常。"
        ),
        "拼写错误或错别字": (
            "请在文案中故意加入明显的错别字或拼写错误，让阅读时一眼能发现问题。"
        ),
        "缺少应出现的覆盖文字": (
            "请在画面中不要正确完整地展示核心卖点文案，让人感觉缺少应有的关键信息提示。"
        ),
        "字体过小": (
            "请把主要卖点文案的字体做得很小，小到不容易看清内容。"
        ),
        "文字相互重叠（或与主体重叠）": (
            "请故意让文字之间相互重叠，或者文字与产品主体发生明显的遮挡和重叠，影响阅读和观看。"
        ),
    },
    "Layout": {
        "画面过于拥挤或杂乱": (
            "请在画面中加入过多的元素，让整体显得非常拥挤、非常杂乱，缺乏清晰的视觉重点。"
        ),
        "留白过多": (
            "请在画面中留下大量空白区域，让主体显得很小、信息非常稀疏，看起来内容不足。"
        ),
        "构图视觉不平衡": (
            "请故意在构图上做得非常不平衡，例如所有主体都挤在画面一侧，另一侧几乎空无一物。"
        ),
        "重要元素被遮挡或互相遮挡": (
            "请让关键的产品主体或关键信息被其他元素部分遮挡，让人看不清楚。"
        ),
        "信息层级不清晰": (
            "请让画面中的文字和元素缺乏主次层级，所有内容大小、颜色都很接近，让人一眼看上去分不清重点。"
        ),
    },
}


def load_base_prompt() -> str:
    """
    使用正式生成海报时的主 Prompt 作为基础 Prompt。

    这里直接读取 prompts/nanfu_ecommerce_main_prompt.txt，
    并将其中的 {copy_line} 占位符替换为一条通用示例文案，
    以保证结构和语气与正式生产环境一致。
    """
    prompt_path = ROOT / "prompts" / "nanfu_ecommerce_main_prompt.txt"
    text = prompt_path.read_text(encoding="utf-8").strip()
    example_copy = "真正耐用，南孚电池"
    return text.replace("{copy_line}", example_copy)


def sanitize_folder_name(name: str) -> str:
    """将中文问题描述转成适合做文件夹名的形式（主要是去掉空格、引号等特殊符号）。"""
    bad_chars = ['"', "'", "“", "”", " ", "：", ":", "/", "\\", "|"]
    result = name
    for ch in bad_chars:
        result = result.replace(ch, "_")
    return result.strip("_")


def get_fixed_components() -> list[Path]:
    """选定一组相对稳定的组件组合：电池体 + 电商彩盒。"""
    paths = pick_from_groups(["马龙","电商彩盒","挂卡"])
    if not paths:
        print("Warning: 未能选出组件图片，请检查 Input Component 目录。", file=sys.stderr)
    return paths


def build_bad_prompt(dimension: str, issue_tag: str) -> str:
    suffix = ISSUE_PROMPT_SUFFIX.get(dimension, {}).get(issue_tag)
    base_prompt = load_base_prompt()

    # 全局文字规范要求：简体中文 + 不能有错别字，品牌名必须写作“南孚”
    text_rules = """
补充的文字规范要求（非常重要）：
1. 所有文案必须使用简体中文，禁止出现任何繁体字。
2. 文案内容必须与提供的句子完全一致，不能改写、不能增删、不能替换任何一个字。
3. 品牌名称必须严格写作「南孚」，不能出现任何错别字、谐音字或相似变体（例如“南扶”“南符”等全部不允许）。
4. 整个画面中禁止出现任何错别字或拼写错误。
"""

    if not suffix:
        # 如果没有针对性的描述，就退化为：正式主 Prompt + 文字规范
        print(f"Warning: 未找到 {dimension}/{issue_tag} 的专用描述，使用基础 Prompt。", file=sys.stderr)
        return base_prompt + "\n\n" + text_rules

    extra = (
        "现在请刻意在以下方面做出不符合规范的效果，用于生成“带问题”的反例海报（仅在这一点上做坏）：\n"
        f"{suffix}\n\n"
        "除上述特定问题外，其他方面可以正常表现，不需要故意制造额外的问题。"
    )

    # 基础正式 prompt + 全局文字规范 + 针对当前 issue 的“做坏”说明
    return base_prompt + "\n\n" + text_rules + "\n\n" + extra


def main() -> None:
    parser = argparse.ArgumentParser(description="为每个质检问题标签生成“不良示例”海报")
    parser.add_argument(
        "--dims",
        type=str,
        default="Background,Object,Text,Layout",
        help="要处理的维度，逗号分隔，例如 Background,Object",
    )
    parser.add_argument(
        "--n-per-issue",
        type=int,
        default=2,
        help="每个 issue tag 生成的图片数量",
    )
    args = parser.parse_args()

    dims_to_run = {d.strip() for d in args.dims.split(",") if d.strip()}

    tags_path = ROOT / "main_detail_issue_tags.json"
    if not tags_path.exists():
        print(f"Error: 未找到 {tags_path}，请确认文件存在。", file=sys.stderr)
        sys.exit(1)

    with open(tags_path, "r", encoding="utf-8") as f:
        all_tags: dict[str, list[str]] = json.load(f)

    image_paths = get_fixed_components()
    if not image_paths:
        sys.exit(1)

    out_root = ROOT / "output" / "bad_examples"
    out_root.mkdir(parents=True, exist_ok=True)

    for dim, tags in all_tags.items():
        if dim not in dims_to_run:
            continue
        for issue in tags:
            bad_prompt = build_bad_prompt(dim, issue)
            print(f"\n=== 生成 {dim} / {issue} 的不良示例 ===", file=sys.stderr)
            try:
                imgs_bytes = generate_poster(
                    image_paths,
                    bad_prompt,
                    negative_prompt="",  # 这里不加负向提示，以便更容易出现“问题”
                    n=args.n_per_issue,
                )
            except Exception as e:
                print(f"  调用模型失败: {e}", file=sys.stderr)
                continue

            dim_dir = out_root / dim
            issue_dir = dim_dir / sanitize_folder_name(issue)
            issue_dir.mkdir(parents=True, exist_ok=True)

            # 方案 2：在同一目录下追加编号，而不是覆盖
            # 先扫描已有的 bad_*.png，找到当前最大编号
            existing = list(issue_dir.glob("bad_*.png"))
            max_idx = 0
            for p in existing:
                name = p.stem  # e.g. "bad_3"
                try:
                    num = int(name.split("_")[-1])
                    if num > max_idx:
                        max_idx = num
                except ValueError:
                    continue

            for i, raw in enumerate(imgs_bytes[: args.n_per_issue], start=1):
                try:
                    img = Image.open(io.BytesIO(raw)).convert("RGB")  # type: ignore[name-defined]
                except Exception as e:
                    print(f"  解码图片失败: {e}", file=sys.stderr)
                    continue

                new_idx = max_idx + i
                out_path = issue_dir / f"bad_{new_idx}.png"
                img.save(out_path, "PNG")
                print(f"  已保存: {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()

