# -*- coding: utf-8 -*-
"""把百科词条正文中的 ASCII 双引号成对改为「」，统一中文引号体例。

- 只处理正文（前置信息块之后），不碰 frontmatter 的 YAML 值。
- 逐行成对替换；行内引号个数为奇数者跳过并列出，交人工处理。
- `--write` 才落盘，默认只报告。

用法：
  py -3 tools/fix_baike_quotes.py            # 试运行，列出待改条目
  py -3 tools/fix_baike_quotes.py --write    # 落盘
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "baike" / "src"

PAIR = re.compile(r'"([^"\n]{1,200})"')


def split_front(text: str) -> tuple[str, str]:
    if not text.startswith("---"):
        return "", text
    end = text.find("\n---", 3)
    if end < 0:
        return "", text
    return text[: end + 4], text[end + 4 :]


def main() -> int:
    write = "--write" in sys.argv
    changed = odd = 0
    for f in sorted(SRC.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        front, body = split_front(text)
        if not body:
            continue
        lines = body.split("\n")
        out = []
        local_odd = 0
        for ln in lines:
            if ln.count('"') % 2 == 1:
                local_odd += 1
                out.append(ln)
                continue
            out.append(PAIR.sub(r"「\1」", ln))
        new_body = "\n".join(out)
        if new_body == body:
            if local_odd:
                print(f"[奇数引号] {f.stem}: {local_odd} 行")
                odd += local_odd
            continue
        changed += 1
        n = sum(1 for a, b in zip(body.split("\n"), new_body.split("\n")) if a != b)
        print(f"[改] {f.stem}: {n} 行")
        if local_odd:
            print(f"      另 {local_odd} 行奇数引号，未动")
            odd += local_odd
        if write:
            f.write_text(front + new_body, encoding="utf-8")
    print(f"\n{'已写回' if write else '待改'} {changed} 条；奇数引号 {odd} 行")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
