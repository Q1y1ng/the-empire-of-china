# -*- coding: utf-8 -*-
"""把百科命名登记（B01—B12）落成《全国官员名录·总索引》的正式附录。

产物：
  1. `设定/全国官员名录·总索引(2026).md` 新增一节「五、内设与副职具名表（2026）」，
     原「五、使用指南」顺延为「六」；
  2. 控制台报告：行数、按卷分布、被跳过的冲突行。

用法：py -3 tools/apply_name_registry.py [--write]
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REG = ROOT / "docs" / "baike" / "命名登记"
INDEX = ROOT / "设定" / "全国官员名录·总索引(2026).md"
ROW = re.compile(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")

# 同岗异名时以机构词条所属批为准（见 docs/baike/命名登记/冲突处理.md）
SUPERSEDED = {
    ("B06", "2"), ("B06", "4"), ("B06", "15"), ("B06", "16"), ("B06", "18"), ("B06", "19"),
}

TITLE = "## 五、内设与副职具名表（2026）"
HEAD = [
    TITLE,
    "",
    "> **口径**：本表为 2026 年中央机关内设司局、直属机构副职、议会专委副职与州级机关主官的具名登记，"
    "与《帝国百科》各词条所载姓名一一对应；品级栏照岗位本身，不照兼任者高配。",
    "> **效力**：姓名一经本表登记，即为此岗位现任者的正式设定；各卷「—」为版面省略，以本表为准。",
    "",
    "| 序 | 姓名 | 机关 | 职务 | 品级 | 所属卷 |",
    "| --- | --- | --- | --- | --- | --- |",
]


SUMMARY = REG / "汇总.md"


def rows() -> list[dict]:
    if SUMMARY.exists():
        out = []
        for line in SUMMARY.read_text(encoding="utf-8").split("\n"):
            m = ROW.match(line.strip())
            if not m or m.group(2).strip() == "姓名":
                continue
            out.append({"name": m.group(2).strip(), "org": m.group(3).strip(),
                        "post": m.group(4).strip(), "rank": m.group(5).strip(),
                        "vol": m.group(6).strip(), "entry": m.group(7).strip()})
        return out
    return rows_raw()


def rows_raw() -> list[dict]:
    out = []
    for f in sorted(REG.glob("B*.md")):
        for line in f.read_text(encoding="utf-8").split("\n"):
            m = ROW.match(line.strip())
            if not m or m.group(2).strip() == "姓名":
                continue
            if (f.stem, m.group(1).strip()) in SUPERSEDED:
                continue
            out.append({
                "name": m.group(2).strip(), "org": m.group(3).strip(),
                "post": m.group(4).strip(), "rank": m.group(5).strip(),
                "vol": m.group(6).strip(), "entry": m.group(7).strip(),
                "batch": f.stem,
            })
    return out


def main() -> int:
    write = "--write" in sys.argv
    rs = rows()
    print(f"有效登记 {len(rs)} 人（已跳过冲突行 {len(SUPERSEDED)} 条）")
    print("按卷分布：" + "；".join(f"{k} {v}" for k, v in Counter(r["vol"] for r in rs).most_common()))
    if not write:
        print("（试运行，未写入）")
        return 0

    table = [f"| {i} | {r['name']} | {r['org']} | {r['post']} | {r['rank']} | {r['vol']} |"
             for i, r in enumerate(rs, 1)]
    block = "\n".join(HEAD + table) + "\n\n"

    text = INDEX.read_text(encoding="utf-8")
    if TITLE in text:
        print("总索引已含该节，先删除旧节再写")
        pre, rest = text.split(TITLE, 1)
        nxt = rest.find("\n## ", 1)
        text = pre + rest[nxt + 1:] if nxt > 0 else pre
    anchor = "## 六、使用指南" if "## 六、使用指南" in text else "## 五、使用指南"
    if anchor not in text:
        print("未找到「## 五、使用指南」，放弃写入")
        return 1
    text = text.replace(anchor, block + "## 六、使用指南", 1)
    INDEX.write_text(text, encoding="utf-8")
    print(f"已写入 {INDEX.relative_to(ROOT)}：新增 {len(rs)} 行")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
