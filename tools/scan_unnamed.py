# -*- coding: utf-8 -*-
"""扫描百科词条中「未具名」的干部岗位，输出需补名的词条与规模。

判据（任一命中即计入）：
  · 正文出现「名录未列姓名」「名录只列职务」「按同名套填」「未具名」「名录未具名」
    「—（略）」「填『—』」等占位说明；
  · 机构设置／组成类表格中，含「主任」「司长」「局长」「厅长」「处长」「副部长」
    「副主任」「副署长」「秘书长」等职务字样而同一行无人名。
用法：py -3 tools/scan_unnamed.py
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "baike" / "src"

MARKERS = ("名录未列姓名", "名录只列职务", "按同名套填", "未具名", "名录未具名",
           "—（略）", "名录记为「—」", "名录为「—」", "只列职务", "不列姓名")
POSTS = ("主任", "司长", "局长", "厅长", "处长", "部长", "副部长", "副主任", "副署长",
         "秘书长", "副秘书长", "庭长", "院长", "检察长", "司令员", "参谋长", "政委",
         "参事", "专员", "总编", "社长", "校长", "院长", "主席", "委员")


def main() -> int:
    total = 0
    rows = []
    for f in sorted(SRC.glob("*.md")):
        t = f.read_text(encoding="utf-8")
        hits = sum(t.count(m) for m in MARKERS)
        # 表格行里职务无名的粗估：行内含职务词、行内中文长度小于 40、且含「—」
        tbl = 0
        for line in t.split("\n"):
            s = line.strip()
            if not s.startswith("|"):
                continue
            if any(p in s for p in POSTS) and ("—" in s or len(re.sub(r"[^\u4e00-\u9fa5]", "", s)) < 26):
                tbl += 1
        if hits or tbl >= 3:
            rows.append((f.stem, hits, tbl, t.split("category:")[1][:4].strip() if "category:" in t else ""))
            total += 1
    rows.sort(key=lambda r: -(r[1] * 2 + r[2]))
    for slug, hits, tbl, cat in rows:
        print(f"{slug:26} {cat:4} 占位说明 {hits:2}  疑无名表行 {tbl:2}")
    print(f"\n涉及 {total} 条词条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
