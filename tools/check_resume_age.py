# -*- coding: utf-8 -*-
"""检查百科人物词条「履历表」中与生年不相容的年份（年份 − 生年 < 18）。

用法：py -3 tools/check_resume_age.py [--min 18]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "baike" / "src"
ROW = re.compile(r"^\|\s*(\d{4})(?:\s*[—–-]\s*(\d{4})?)?\s*\|\s*([^|]*)\|")

SKIP = ("生于", "出生", "卒", "小学", "中学", "毕业", "学员", "学生", "学徒", "技校", "大学")


def main() -> int:
    mins = 18
    if "--min" in sys.argv:
        mins = int(sys.argv[sys.argv.index("--min") + 1])
    bad = 0
    for f in sorted(SRC.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        if "category: 人物" not in text[:400]:
            continue
        m = re.search(r"(?m)^\s*出生:\s*(\d{4})", text)
        if not m:
            continue
        birth = int(m.group(1))
        title = re.search(r"(?m)^title:\s*(.+)$", text).group(1).strip()
        seg = text.split("## 履历表", 1)
        if len(seg) < 2:
            continue
        seg = seg[1].split("\n## ", 1)[0]
        for line in seg.split("\n"):
            r = ROW.match(line.strip())
            if not r:
                continue
            year, post = int(r.group(1)), r.group(3)
            if any(s in post for s in SKIP):
                continue
            if year - birth < mins:
                print(f"{f.stem:20} {title:5} 生年{birth}  {year} 年 {post.strip()[:34]}（{year - birth} 岁）")
                bad += 1
    print(f"\n共 {bad} 处")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
