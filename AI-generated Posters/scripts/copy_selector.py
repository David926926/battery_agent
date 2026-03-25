"""
从 Input Component/lines.txt 中随机选取文案。
用法：
  from copy_selector import load_lines, pick_one
  lines = load_lines()
  line = pick_one(lines)
"""
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINES_TXT = ROOT / "Input Component" / "lines.txt"


def load_lines(path: Path | None = None) -> list[str]:
    """加载 lines.txt，返回非空行列表。"""
    p = path or LINES_TXT
    if not p.exists():
        raise FileNotFoundError(f"文案文件不存在: {p}，请先运行 parse_pdf_to_copy_library.py")
    return [l.strip() for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def pick_one(lines: list[str] | None = None) -> str:
    """从文案列表中随机选 1 条。"""
    lines = lines or load_lines()
    if not lines:
        return "南孚聚能环5代 超大容量更耐用"
    return random.choice(lines)
