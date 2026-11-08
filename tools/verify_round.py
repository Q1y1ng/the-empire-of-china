# -*- coding: utf-8 -*-
"""收尾验收：三项指令是否全部达成（只读，不改文件）。"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIO = ROOT / "设定" / "帝国高层人物小传(2026).md"
SRC = ROOT / "docs" / "baike" / "src"
INDEX = ROOT / "设定" / "全国官员名录·总索引(2026).md"
CHANGELOG = ROOT / "CHANGELOG.md"

HEAD = re.compile(r"^\*\*(\d+)\.\s*([^*｜]+?)(?:※)?\*\*｜生年\s*(\d{4})｜")
YEAR_ITEM = re.compile(r"(\d{4})\s*年")


def check_bio() -> None:
    lines = BIO.read_text(encoding="utf-8").split("\n")
    bad = []
    people = 0
    birth_by_line: dict[int, tuple[str, int]] = {}
    last = None
    for i, line in enumerate(lines):
        m = HEAD.match(line.strip())
        if m:
            last = (m.group(2).strip(), int(m.group(3)))
        if last:
            birth_by_line[i] = last
    for i, line in enumerate(lines):
        if "履历：" not in line or i not in birth_by_line:
            continue
        people += 1
        name, birth = birth_by_line[i]
        seg = line[line.find("履历："):].split("。", 1)[0]
        for ym in YEAR_ITEM.finditer(seg):
            y = int(ym.group(1))
            if y - birth < 18:
                bad.append((name, birth, y, seg[max(0, ym.start() - 12): ym.start() + 16]))
    print(f"[①] 小传 {people}/57 人的履历句已校验；年份早于生年+18 的条目 {len(bad)} 处")
    for b in bad[:6]:
        print("    ", b)


def check_baike() -> None:
    neg = 0
    files = list(SRC.glob("*.md"))
    for f in files:
        t = f.read_text(encoding="utf-8")
        neg += sum(t.count(w) for w in ("不是", "并非", "而非", "并不"))
    print(f"[②] 百科 {len(files)} 条；否定式命中 {neg} 处")


def check_names() -> None:
    text = INDEX.read_text(encoding="utf-8")
    seg = text.split("## 五、内设与副职具名表（2026）", 1)
    if len(seg) < 2:
        print("[③] 未找到具名表章节")
        return
    body = seg[1].split("\n## ", 1)[0]
    rows = re.findall(r"(?m)^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|", body)
    names = [r[1].strip() for r in rows]
    print(f"[③] 具名表 {len(rows)} 行，去重姓名 {len(set(names))} 个")

    # 抽样：每个姓名在百科里应至少出现一次
    corpus = "\n".join(f.read_text(encoding="utf-8") for f in SRC.glob("*.md"))
    missing = [n for n in names if n not in corpus]
    print(f"     姓名未在百科出现：{len(missing)} 个" + ("（" + "、".join(missing[:5]) + "）" if missing else ""))


def check_repo() -> None:
    log = subprocess.run(["git", "log", "--oneline", "-3"], cwd=ROOT, capture_output=True)
    st = subprocess.run(["git", "status", "--short"], cwd=ROOT, capture_output=True)
    print("[④] 最近提交：\n" + log.stdout.decode("utf-8", "ignore").strip())
    print("     工作区改动：", len(st.stdout.decode("utf-8", "ignore").strip().splitlines()))
    cl = CHANGELOG.read_text(encoding="utf-8")
    hit = "百科三项补正" in cl
    print("[⑤] CHANGELOG 含本轮记录：", "是" if hit else "否")


if __name__ == "__main__":
    check_bio()
    check_baike()
    check_names()
    check_repo()
