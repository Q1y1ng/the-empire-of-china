# -*- coding: utf-8 -*-
"""校正百科词条中「革鼎」年号与公元年份的换算。

换算基准（《中华帝国编年史1700—2026》附三·四「年号一览」）：
  革鼎元年＝1930 年，且 **公元 = 1930 + 革鼎年数**（四十八年＝1978）。
  承宪元年＝1981 年，公元 = 1981 + 承宪年数（九年＝1990）。
  继文十一年＝2026，公元 = 2015 + 继文年数（元年＝2016）。
本脚本只改动两类位置：
  1. 前置信息 `出生:` / `生年:` 行内的括注；
  2. 正文中「NNNN 年（革鼎××年）」这类同句对照。
其余提及一律只报告，交人工判断。

用法：py -3 tools/fix_baike_era.py [--write]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "baike" / "src"

DIGITS = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
          "六": 6, "七": 7, "八": 8, "九": 9}
ERAS = {"革鼎": 1930, "承宪": 1981, "继文": 2015}
CN_NUM = re.compile(r"[零一二两三四五六七八九十]+")


def cn2int(s: str) -> int:
    if s == "十":
        return 10
    if "十" in s:
        head, _, tail = s.partition("十")
        tens = DIGITS.get(head, 1) if head else 1
        ones = DIGITS.get(tail, 0) if tail else 0
        return tens * 10 + ones
    total = 0
    for ch in s:
        total = total * 10 + DIGITS.get(ch, 0)
    return total


def int2cn(n: int) -> str:
    if n <= 10:
        return "十" if n == 10 else "一 二 三 四 五 六 七 八 九".split()[n - 1]
    tens, ones = divmod(n, 10)
    head = "" if tens == 1 else "一 二 三 四 五 六 七 八 九".split()[tens - 1]
    tail = "" if ones == 0 else "一 二 三 四 五 六 七 八 九".split()[ones - 1]
    return f"{head}十{tail}"


def main() -> int:
    write = "--write" in sys.argv
    fixed = reported = 0
    for f in sorted(SRC.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        lines = text.split("\n")
        out = []
        changed = False
        for ln in lines:
            is_front = re.match(r"^\s*(出生|生年):", ln)
            m = re.search(r"(\d{4})\s*年（(革鼎|承宪|继文)([零一二两三四五六七八九十]+)年）", ln)
            if m:
                year = int(m.group(1))
                era, num = m.group(2), cn2int(m.group(3))
                want = year - ERAS[era]
                if want != num:
                    ln = ln[: m.start()] + f"{year} 年（{era}{int2cn(want)}年）" + ln[m.end():]
                    changed = True
                    fixed += 1
                    print(f"[改] {f.stem}: {m.group(0)} → {year} 年（{era}{int2cn(want)}年）")
            elif is_front and re.search(r"(革鼎|承宪|继文)", ln):
                reported += 1
                print(f"[待看] {f.stem}: {ln.strip()}")
            out.append(ln)
        if changed and write:
            f.write_text("\n".join(out), encoding="utf-8")
    print(f"\n{'已写回' if write else '待改'} {fixed} 处；需人工看 {reported} 处")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
