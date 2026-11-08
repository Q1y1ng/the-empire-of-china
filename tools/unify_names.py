# -*- coding: utf-8 -*-
"""全库归一：把「同岗异名」的作废姓名在百科所有词条中改为采用名。

裁定规则（作者 2026-11-08）：以**人物词条**所载为准；无人物条时按机构条，再按批号在先。
与 `resolve_name_conflicts.py` 的区别：本脚本在**全部词条**中做替换（不止作废方那一条），
用于清理前一轮「机构优先」改写后残留在其他词条里的旧名。

用法：py -3 tools/unify_names.py [--write]
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REG = ROOT / "docs" / "baike" / "命名登记"
SRC = ROOT / "docs" / "baike" / "src"
ROW = re.compile(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")


def info() -> dict[str, tuple[str, str]]:
    out = {}
    for f in SRC.glob("*.md"):
        t = f.read_text(encoding="utf-8")
        mt = re.search(r"(?m)^title:\s*(.+)$", t)
        mc = re.search(r"(?m)^category:\s*(.+)$", t)
        if mt and mc:
            out[f.stem] = (mt.group(1).strip(), mc.group(1).strip())
    return out


def main() -> int:
    write = "--write" in sys.argv
    meta = info()
    rows = []
    for f in sorted(REG.glob("B*.md")):
        for line in f.read_text(encoding="utf-8").split("\n"):
            m = ROW.match(line.strip())
            if not m or m.group(2).strip() == "姓名":
                continue
            rows.append({"batch": f.stem, "name": m.group(2).strip(),
                         "org": m.group(3).strip(), "post": m.group(4).strip(),
                         "entry": m.group(7).strip()})
    groups = defaultdict(list)
    for r in rows:
        groups[(r["org"], r["post"])].append(r)

    mapping: dict[str, str] = {}
    for (org, post), rs in groups.items():
        if len({r["name"] for r in rs}) < 2:
            continue

        def score(r):
            mm = re.search(r"[（(]([a-z0-9-]+)[）)]", r["entry"])
            slug = mm.group(1) if mm else r["entry"]
            title, cat = meta.get(slug, ("", ""))
            rank = 0 if cat == "人物" else (1 if cat == "机构" else 2)
            return (rank, -len(title), r["batch"])

        rs_sorted = sorted(rs, key=score)
        win = rs_sorted[0]["name"]
        for r in rs_sorted[1:]:
            if r["name"] != win:
                mapping[r["name"]] = win

    print(f"待归一姓名 {len(mapping)} 个：")
    for k, v in mapping.items():
        print(f"  {k} → {v}")

    total = 0
    for f in sorted(SRC.glob("*.md")):
        t = f.read_text(encoding="utf-8")
        orig = t
        for old, new in mapping.items():
            if old in t:
                t = t.replace(old, new)
        if t != orig:
            n = sum(orig.count(k) for k in mapping)
            total += n
            if write:
                f.write_text(t, encoding="utf-8")
            print(f"[{'改' if write else '待改'}] {f.stem}: {n} 处")
    print(f"\n合计 {total} 处" + ("（已写回）" if write else "（试运行）"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
