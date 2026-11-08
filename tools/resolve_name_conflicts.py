# -*- coding: utf-8 -*-
"""裁定「同岗异名」：机构词条所载姓名为准，人物词条随之改写。

规则（按优先级）：
  1. 若某行的「所在词条」是**机构类词条**，且该词条标题与该行「机关」相互包含 → 该行胜出；
  2. 否则取批号最小者（B01 优先于 B06…）；
  3. 败方姓名在其词条文件内整体替换为胜方姓名，并报告替换次数。

用法：py -3 tools/resolve_name_conflicts.py [--write]
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


def titles() -> dict[str, tuple[str, str]]:
    out = {}
    for f in SRC.glob("*.md"):
        t = f.read_text(encoding="utf-8")
        m = re.search(r"(?m)^title:\s*(.+)$", t)
        c = re.search(r"(?m)^category:\s*(.+)$", t)
        if m and c:
            out[f.stem] = (m.group(1).strip(), c.group(1).strip())
    return out


def main() -> int:
    write = "--write" in sys.argv
    info = titles()
    rows = []
    for f in sorted(REG.glob("B*.md")):
        for line in f.read_text(encoding="utf-8").split("\n"):
            m = ROW.match(line.strip())
            if not m or m.group(2).strip() == "姓名":
                continue
            rows.append({"batch": int(f.stem[1:]), "name": m.group(2).strip(),
                         "org": m.group(3).strip(), "post": m.group(4).strip(),
                         "entry": m.group(7).strip()})
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        groups[(r["org"], r["post"])].append(r)

    fixes = []
    for (org, post), rs in groups.items():
        names = {r["name"] for r in rs}
        if len(names) < 2:
            continue

        def score(r: dict) -> tuple[int, int, int]:
            mm = re.search(r"[（(]([a-z0-9-]+)[）)]", r["entry"])
            slug = mm.group(1) if mm else r["entry"]
            title, cat = info.get(slug, ("", ""))
            if cat != "机构" or not title:
                home = 0
            elif title == org:
                home = 2
            elif title in org or org in title:
                home = 1
            else:
                home = 0
            return (-home, -len(title), r["batch"])

        rs_sorted = sorted(rs, key=score)
        win = rs_sorted[0]
        for lose in rs_sorted[1:]:
            fixes.append((win, lose, org, post))

    for win, lose, org, post in fixes:
        slug = re.search(r"[（(]([a-z0-9-]+)[）)]", lose["entry"])
        slug = slug.group(1) if slug else lose["entry"]
        p = SRC / f"{slug}.md"
        if not p.exists():
            print(f"[缺文件] {lose['entry']}")
            continue
        t = p.read_text(encoding="utf-8")
        n = t.count(lose["name"])
        print(f"{org}｜{post}：{lose['name']}（{lose['entry']}）→ {win['name']}（{win['entry']}）　替换 {n} 处")
        if write and n:
            p.write_text(t.replace(lose["name"], win["name"]), encoding="utf-8")
    print(f"\n共 {len(fixes)} 处待改")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
