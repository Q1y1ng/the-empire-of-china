# -*- coding: utf-8 -*-
"""合并百科「命名登记」各批表格，做重名与同岗异名检查，并生成《名录·总索引》附录。

用法：
  py -3 tools/merge_name_registry.py            # 只检查、打印报告
  py -3 tools/merge_name_registry.py --write    # 写出 docs/baike/命名登记/汇总.md
"""
from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REG = ROOT / "docs" / "baike" / "命名登记"
OUT = REG / "汇总.md"
ROW = re.compile(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")


def main() -> int:
    write = "--write" in sys.argv
    rows = []
    for f in sorted(REG.glob("B*.md")):
        for line in f.read_text(encoding="utf-8").split("\n"):
            m = ROW.match(line.strip())
            if not m:
                continue
            if m.group(2).strip() in ("姓名",):
                continue
            rows.append({
                "batch": f.stem,
                "no": m.group(1).strip(),
                "name": m.group(2).strip(),
                "org": m.group(3).strip(),
                "post": m.group(4).strip(),
                "rank": m.group(5).strip(),
                "vol": m.group(6).strip(),
                "entry": m.group(7).strip(),
            })
    print(f"登记行合计 {len(rows)}")

    # 同岗异名去重：按「机构词条＞批号」保留唯一一行
    info = {}
    for f in (ROOT / "docs" / "baike" / "src").glob("*.md"):
        tx = f.read_text(encoding="utf-8")
        mt = re.search(r"(?m)^title:\s*(.+)$", tx)
        mc = re.search(r"(?m)^category:\s*(.+)$", tx)
        if mt and mc:
            info[f.stem] = (mt.group(1).strip(), mc.group(1).strip())
    groups = defaultdict(list)
    for r in rows:
        groups[(r["org"], r["post"])].append(r)
    dedup = []
    for (org, post), rs in groups.items():
        def score(x):
            mm = re.search(r"[（(]([a-z0-9-]+)[）)]", x["entry"])
            slug = mm.group(1) if mm else x["entry"]
            title, cat = info.get(slug, ("", ""))
            rank = 0 if cat == "人物" else (1 if cat == "机构" else 2)
            return (rank, -len(title), int(x["batch"][1:]))
        dedup.append(sorted(rs, key=score)[0])
    dedup.sort(key=lambda r: (r["batch"], int(r["no"])))
    rows = dedup

    by_name = Counter(r["name"] for r in rows)
    dup_names = [n for n, c in by_name.items() if c > 1]
    print(f"重名 {len(dup_names)} 个：{'、'.join(dup_names[:12])}")

    by_post = defaultdict(set)
    for r in rows:
        by_post[(r["org"], r["post"])].add(r["name"])
    conflicts = {k: v for k, v in by_post.items() if len(v) > 1}
    print(f"同岗异名 {len(conflicts)} 处：")
    for (org, post), names in list(conflicts.items())[:12]:
        print(f"  {org}｜{post}：{'、'.join(sorted(names))}")

    by_vol = Counter(r["vol"] for r in rows)
    print("按卷分布：" + "；".join(f"{k} {v}" for k, v in by_vol.most_common()))

    if write:
        lines = ["# 百科命名登记·汇总（2026）", "",
                 f"> 由 `tools/merge_name_registry.py` 合并 B01—B12 各批登记表生成；共 {len(rows)} 人。",
                 "> 本表为《全国官员名录》附「内设与副职具名表」的底稿。", "",
                 "| 序 | 姓名 | 机关 | 职务 | 品级 | 应入名录卷 | 所在词条 |",
                 "| --- | --- | --- | --- | --- | --- | --- |"]
        for i, r in enumerate(rows, 1):
            lines.append(f"| {i} | {r['name']} | {r['org']} | {r['post']} | {r['rank']} | {r['vol']} | {r['entry']} |")
        if dup_names:
            lines += ["", "## 待处理：重名", ""] + [f"- {n}（{by_name[n]} 处）" for n in dup_names]
        if conflicts:
            lines += ["", "## 待处理：同岗异名", ""]
            for (org, post), names in conflicts.items():
                lines.append(f"- {org}｜{post}：{'、'.join(sorted(names))}")
        OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"已写 {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
