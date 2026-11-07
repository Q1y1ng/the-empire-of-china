# -*- coding: utf-8 -*-
"""百科扩写进度统计：按类别统计已改写（含「参考资料」节）与未改写词条。

用法：py -3 tools/baike_status.py [--todo]
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "baike" / "src"


def main() -> int:
    todo = "--todo" in sys.argv
    done = {"机构": [], "人物": [], "概念": []}
    left = {"机构": [], "人物": [], "概念": []}
    for f in sorted(SRC.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        cat = ""
        for line in text.split("\n")[:10]:
            if line.startswith("category:"):
                cat = line.split(":", 1)[1].strip()
                break
        if cat not in done:
            continue
        ready = "## 参考资料" in text and "## 参考资料来源" not in text
        (done if ready else left)[cat].append(f.stem)
    total = sum(len(v) for v in done.values()) + sum(len(v) for v in left.values())
    print(f"合计 {total} 条：已改写 {sum(len(v) for v in done.values())}，未改写 {sum(len(v) for v in left.values())}")
    for cat in ("机构", "人物", "概念"):
        print(f"  {cat}: 已 {len(done[cat])} / 待 {len(left[cat])}")
    if todo:
        for cat in ("机构", "人物", "概念"):
            if left[cat]:
                print(f"\n[待改·{cat}] {' '.join(left[cat])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
