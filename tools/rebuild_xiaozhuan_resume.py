# -*- coding: utf-8 -*-
"""用百科人物词条的「履历表」重写《帝国高层人物小传》各人的「履历：」句。

目的：让小传履历年份与虚构生年一致（改齐），且两卷时间线同源。
做法：
  · 解析小传 **N. 姓名**｜生年｜籍贯 块后的段落；
  · 取该人百科词条「## 履历表」中带四位年份的行，跳过出生与学历段；
  · 生成「YYYY年职务，YYYY年职务……」串，替换原「履历：……。」整段；
  · 「2026年任……」及其后的风格／标签原样保留。

用法：
  py -3 tools/rebuild_xiaozhuan_resume.py            # 试运行，打印对照
  py -3 tools/rebuild_xiaozhuan_resume.py --write
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIO = ROOT / "设定" / "帝国高层人物小传(2026).md"
BAIKE = ROOT / "docs" / "baike" / "src"

HEAD = re.compile(r"^\*\*(\d+)\.\s*([^*｜]+?)(?:※)?\*\*｜生年\s*(\d{4})｜")
ROW = re.compile(r"^\|\s*(\d{4})(?:\s*[—–-]\s*[\d.]*)?\s*\|\s*([^|]*)\|\s*([^|]*)\|")
SKIP_POST = ("生于", "出生", "卒", "小学", "中学", "毕业", "学员", "学生", "学徒", "技校", "大学", "学业", "插队", "入伍", "技工学校", "学堂", "专业", "学校")


def slug_of(name: str) -> Path | None:
    for f in BAIKE.glob("*.md"):
        t = f.read_text(encoding="utf-8")
        if re.search(rf"^title:\s*{re.escape(name)}\s*$", t, re.M):
            return f
    return None


def rows_of(path: Path) -> list[tuple[int, str]]:
    text = path.read_text(encoding="utf-8")
    if "## 履历表" not in text:
        return []
    seg = text.split("## 履历表", 1)[1].split("\n## ", 1)[0]
    out = []
    for line in seg.split("\n"):
        r = ROW.match(line.strip())
        if not r:
            continue
        year, post, rank = int(r.group(1)), r.group(2).strip(), r.group(3).strip()
        if not post or post in ("—", "职务"):
            continue
        if any(s in post for s in SKIP_POST):
            continue
        if rank in ("学员", "学生", "举子", "学徒", "吏"):
            continue
        if year >= 2026:
            continue
        clean = re.sub(r"\s+", "", post).replace("（兼）", "")
        if out and out[-1][1] == clean:
            continue
        out.append((year, clean))
    return out


def main() -> int:
    write = "--write" in sys.argv
    lines = BIO.read_text(encoding="utf-8").split("\n")
    out = list(lines)
    changed = 0
    for i, line in enumerate(lines):
        m = HEAD.match(line.strip())
        if not m:
            continue
        name, birth = m.group(2).strip(), int(m.group(3))
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        if j >= len(lines):
            continue
        para = lines[j]
        k = para.find("履历：")
        if k < 0:
            continue
        seg_end = para.find("。", k)
        if seg_end < 0:
            continue
        old_seg = para[k + 3: seg_end]

        bk = slug_of(name)
        if not bk:
            print(f"[无词条] {name}")
            continue
        rows = rows_of(bk)
        if not rows:
            print(f"[无履历表] {name}（{bk.name}）")
            continue
        frag = "，".join(f"{y}年{p}" for y, p in rows)
        new_seg = frag
        if new_seg == old_seg:
            continue
        out[j] = para[: k + 3] + new_seg + para[seg_end:]
        changed += 1
        print(f"--- {name}（生年 {birth}）")
        print(f"    旧：{old_seg[:96]}")
        print(f"    新：{new_seg[:96]}")

    print(f"\n改写 {changed} 人")
    if write:
        BIO.write_text("\n".join(out), encoding="utf-8")
        print(f"已写回 {BIO.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
