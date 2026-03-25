#!/usr/bin/env python3
"""
解析 品牌广告渠道-文案.pdf，提取每条文案，输出到 Input Component/lines.txt（一行一句）。
用法:
  python scripts/parse_pdf_to_copy_library.py
"""
import re
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

ROOT = Path(__file__).resolve().parent.parent
INPUT_PDF = ROOT / "Input Component" / "品牌广告渠道-文案.pdf"
OUTPUT_TXT = ROOT / "Input Component" / "lines.txt"


def _clean(s: str) -> str:
    """去掉控制字符和首尾空白。"""
    return "".join(c for c in s.strip() if ord(c) >= 32 or c in "\n\t").strip()


def _should_skip(s: str) -> bool:
    """跳过页码、年份标题等非文案行。"""
    if len(s) < 2:
        return True
    if re.match(r"^--\s*\d+\s+of\s+\d+\s*--$", s):
        return True
    if re.match(r"^\d{4}$", s):
        return True
    if re.match(r"^品牌.*文案$", s):
        return True
    return False


def extract_lines(pdf_path: Path) -> list[str]:
    """从 PDF 提取所有文案行，去重。"""
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if not pdfplumber:
        raise RuntimeError("pip install pdfplumber required")

    seen = set()
    lines = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            for raw in text.splitlines():
                raw = raw.strip()
                if not raw:
                    continue
                for part in re.split(r"[。；\|]", raw):
                    part = _clean(part)
                    if not part or _should_skip(part) or part in seen:
                        continue
                    seen.add(part)
                    lines.append(part)
    return lines


def main():
    lines = extract_lines(INPUT_PDF)
    OUTPUT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"提取了 {len(lines)} 条文案 → {OUTPUT_TXT}")


if __name__ == "__main__":
    main()
