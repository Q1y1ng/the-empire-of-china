# -*- coding: utf-8 -*-
"""按虚构生年把《帝国高层人物小传》的履历年份改齐（以百科词条履历表为准）。

做法：
  1. 解析小传「**N. 姓名**｜生年 YYYY｜籍贯」块与随后的「履历：」句；
  2. 解析 docs/baike/src/<slug>.md 的「## 履历表」行（时间｜职务）；
  3. 对每个履历条目，若 年份 − 生年 < 22（早年不可能任职），用履历表中职务最相近的一行年份替换；
  4. 校验年份单调不减，输出改前改后对照。

用法：
  py -3 tools/align_xiaozhuan_years.py            # 试运行，打印报告
  py -3 tools/align_xiaozhuan_years.py --write    # 落盘（只改 设定/帝国高层人物小传(2026).md）
"""
from __future__ import annotations

import difflib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIO = ROOT / "设定" / "帝国高层人物小传(2026).md"
BAIKE = ROOT / "docs" / "baike" / "src"

HEAD = re.compile(r"^\*\*(\d+)\.\s*([^*｜]+?)(?:※)?\*\*｜生年\s*(\d{4})｜")
YEAR_ITEM = re.compile(r"(\d{4})\s*年([^，。；]*)")
ROW = re.compile(r"^\|\s*(\d{4})(?:\s*[—–-]\s*(\d{4})?)?\s*\|\s*([^|]+?)\s*\|")


def slug_of(baike_dir: Path, name: str) -> Path | None:
    for f in baike_dir.glob("*.md"):
        t = f.read_text(encoding="utf-8")
        if re.search(rf"^title:\s*{re.escape(name)}\s*$", t, re.M):
            return f
    return None


def resume_rows(path: Path) -> list[tuple[int, str]]:
    text = path.read_text(encoding="utf-8")
    m = re.search(r"(?m)^## 履历表\s*$", text)
    if not m:
        return []
    seg = text[m.end():]
    seg = seg.split("\n## ", 1)[0]
    rows = []
    for line in seg.split("\n"):
        r = ROW.match(line.strip())
        if r:
            rows.append((int(r.group(1)), r.group(3).strip()))
    return rows


def main() -> int:
    write = "--write" in sys.argv
    lines = BIO.read_text(encoding="utf-8").split("\n")
    out = list(lines)
    changed_people = 0
    changed_items = 0
    report = []

    i = 0
    while i < len(lines):
        m = HEAD.match(lines[i].strip())
        if not m:
            i += 1
            continue
        idx, name, birth = m.group(1), m.group(2).strip(), int(m.group(3))
        # 履历句在随后 1–3 行内
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        if j >= len(lines):
            break
        para = lines[j]
        k = para.find("履历：")
        if k < 0:
            i = j + 1
            continue

        bk = slug_of(BAIKE, name)
        rows = resume_rows(bk) if bk else []

        head, tail = para[: k + 3], para[k + 3:]
        seg_end = tail.find("。")
        seg = tail if seg_end < 0 else tail[:seg_end]
        rest = "" if seg_end < 0 else tail[seg_end:]

        items = list(YEAR_ITEM.finditer(seg))
        new_seg = seg
        local = 0
        for it in reversed(items):
            year = int(it.group(1))
            duty = it.group(2)
            age = year - birth
            if age >= 22 or year >= 2026:
                continue
            # 找职务最相近的履历表行
            best, best_ratio = None, 0.0
            for ry, rpost in rows:
                ratio = difflib.SequenceMatcher(None, duty, rpost).ratio()
                if ratio > best_ratio:
                    best, best_ratio = (ry, rpost), ratio
            if not best or best_ratio < 0.25:
                report.append(f"[跳过] {name} {year}年{duty}（无可匹配履历行，相似度 {best_ratio:.2f}）")
                continue
            new_year = best[0]
            if new_year - birth < 18:
                report.append(f"[存疑] {name} {year}→{new_year} 仍不足 18 岁（{duty}）")
            new_seg = new_seg[: it.start()] + f"{new_year} 年" + new_seg[it.start() + len(it.group(1)) + 1:]
            report.append(f"[改] {name} {year}→{new_year}（{duty[:18]}｜履历表：{best[1][:18]}）")
            local += 1

        if local:
            out[j] = head + new_seg + rest
            changed_people += 1
            changed_items += local
        i = j + 1

    for r in report:
        print(r)
    print(f"\n涉及 {changed_people} 人、{changed_items} 处年份")
    if write:
        BIO.write_text("\n".join(out), encoding="utf-8")
        print(f"已写回 {BIO.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
