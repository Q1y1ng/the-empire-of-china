# -*- coding: utf-8 -*-
"""为「政代会衔接」补写生成清单：按现职判定每人应补哪一类程序表述。

输出：slug｜姓名｜现职｜类别（文职／州委主席／州长／军区司令／军委副主席／军职四席／议会专委主任）
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "baike" / "src"


def classify(post: str, title: str) -> str:
    if any(k in post for k in ("军区司令",)):
        return "军区司令"
    if any(k in post for k in ("军种负责人", "总政治部主任")):
        return "军职四席"
    if "军委副主席" in post or "副主席（常务主持）" in post:
        return "军委副主席"
    if "州委主席" in post:
        return "州委主席"
    if "州长" in post:
        return "州长"
    if post.endswith("州长") or "州长" == post.strip():
        return "州长"
    if "专门委员会主任" in post or "委员会主任" in post and "议" in post:
        return "议会专委主任"
    return "文职"


def main() -> int:
    rows = []
    for f in sorted(SRC.glob("*.md")):
        t = f.read_text(encoding="utf-8")
        if "category: 人物" not in t[:400]:
            continue
        if not re.search(r"中央政治委员会|政治委员会委员", t):
            continue
        if re.search(r"政代会|州代会|政治代表会议", t):
            continue
        title = re.search(r"(?m)^title:\s*(.+)$", t).group(1).strip()
        m = re.search(r"(?m)^\s*现职:\s*(.+)$", t)
        post = m.group(1).strip() if m else ""
        rows.append((f.stem, title, post, classify(post, title)))
    rows.sort(key=lambda r: (r[3], r[0]))
    print(f"共 {len(rows)} 条待补：")
    for slug, title, post, cls in rows:
        print(f"{slug:22} {title:5} {cls:8} {post[:46]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
