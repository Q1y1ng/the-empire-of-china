# -*- coding: utf-8 -*-
"""列出名词卷表格中的「姓名式」单元格，便于人工核对是否混入真实历史人名。"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = [
    "设定/全国官员名录·卷三十三·中央政治委员会全名单(2026).md",
    "设定/全国官员名录·卷一·中央与京畿直隶州(2026).md",
    "设定/全国官员名录·卷三十五·三大舰队与八大军区纵深(2026).md",
    "设定/全国官员名录·卷四十·皇室成员与皇室机构(2026).md",
    "设定/帝国高层人物小传(2026).md",
]
STOP = set("一二三四五六七八九十品级职务姓名备注推演常委委员会政治局中央国务院主席主任秘书长书记部长局长厅长处长院长省长州长司令军区舰队大校中将上将少将")
CELL = re.compile(r"^\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|")


def main() -> int:
    seen: dict[str, str] = {}
    for rel in FILES:
        p = ROOT / rel
        for line in p.read_text(encoding="utf-8").split("\n"):
            m = CELL.match(line.strip())
            if not m:
                continue
            cell = m.group(2)
            if not cell or cell in ("—", "姓名"):
                continue
            for tok in re.split(r"[、，,／/；;（）()\s]+", cell):
                if not (2 <= len(tok) <= 3) or not re.fullmatch(r"[\u4e00-\u9fa5]+", tok):
                    continue
                if any(c in STOP for c in tok):
                    continue
                if tok.endswith(("长", "员", "席", "任", "级", "人", "处", "局", "厅", "院", "部", "校", "军", "州", "省")):
                    continue
                seen.setdefault(tok, p.name)
    print(f"候选姓名 {len(seen)} 个：")
    items = list(seen)
    for i in range(0, len(items), 10):
        print("  " + "、".join(items[i:i + 10]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
