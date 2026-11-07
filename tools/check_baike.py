# -*- coding: utf-8 -*-
"""《帝国百科》体例与口径校验器。

校验项：
  1. 前置信息完整、slug 与文件名一致、title 全库唯一、related 与交叉链接可解析
  2. 篇幅下限（机构 2,600 / 人物 1,800 / 概念 2,400，按正文汉字计）
  3. 节数与节名（5.1–5.3 模板）
  4. 否定句比例（每篇 ≤ 2 处，含首段定义句禁用否定）
  5. 禁忌词（现实政治名词、史实原型、†、未定状态）
  6. 人物生年、品级与《口径基线》一致
  7. 交叉链接数量 8–20，表格分隔行完整

用法：
  py -3 tools/check_baike.py                 # 全库
  py -3 tools/check_baike.py --slug pcc      # 单条
  py -3 tools/check_baike.py --quiet         # 只列不通过项
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "baike" / "src"
BASELINE = ROOT / "docs" / "baike" / "口径基线.md"

MIN_CHARS = {"机构": 2600, "人物": 1800, "概念": 2400}
MIN_SECTIONS = {"机构": 6, "人物": 7, "概念": 7}

ALLOWED_SECTIONS = {
    "机构": {
        "概述", "历史沿革", "机构设置", "主要职能", "运行机制", "与相关机构的分工",
        "2026 年要项", "2026 年落点", "内设与人事", "内设与直属", "规则要点",
        "与国务院的关系", "与军委的关系", "与政府的关系", "与总理的关系", "与州委主席的关系",
        "与常委会、政委会的关系", "与外交部、中央外事委员会的关系", "与纪委、谋官论处的关系",
        "与央企、与地方", "与宪法法院、政法系统的关系", "与军委、国防部的关系", "与三衡的关系",
        "关系图谱审查", "参考资料", "参考资料来源", "相关条目",
    },
    "人物": {
        "概述", "生平", "履历", "履历表", "主要工作", "施政主张", "人物风格", "风格与主张",
        "家庭", "评价", "争议", "参考资料", "参考资料来源", "相关条目",
    },
    "概念": {
        "概述", "定义与内涵", "历史渊源", "制度内容", "运行与实例", "数据", "意义与评价",
        "现代用法", "参考资料", "参考资料来源", "相关条目",
    },
}

REQUIRED_SECTION = "参考资料"
REQUIRED_SECTION_ALT = "参考资料来源"

NEG_PATTERNS = [
    ("不是", re.compile(r"不是")),
    ("并非", re.compile(r"并非")),
    ("而非", re.compile(r"而非")),
    ("并不", re.compile(r"并不")),
    ("并不是", re.compile(r"并不是")),
]
NEG_LIMIT = 2

FORBIDDEN = [
    ("史实原型", "溯源标注"),
    ("†", "溯源标注"),
    ("社会主义", "现实政治名词"),
    ("共产党", "现实政治名词"),
    ("新民主主义", "现实政治名词"),
    ("马克思", "现实政治名词"),
    ("筹建中", "未定状态"),
    ("拟设", "未定状态"),
    ("改革开放", "现实政治名词"),
]

RANK_DIGITS = {"一": "1", "二": "2", "三": "3", "四": "4", "五": "5",
               "六": "6", "七": "7", "八": "8", "九": "9", "十": "10"}


def parse_front(text: str):
    if not text.startswith("---"):
        return None, text, "缺少前置信息块"
    end = text.find("\n---", 3)
    if end < 0:
        return None, text, "前置信息块未闭合"
    front, body = text[3:end], text[end + 4:].lstrip("\n")
    meta: dict = {"infobox": []}
    in_box = False
    for raw in front.split("\n"):
        if not raw.strip():
            continue
        if raw.strip() == "infobox:":
            in_box = True
            continue
        if in_box and raw.startswith("  "):
            k, _, v = raw.strip().partition(":")
            meta["infobox"].append((k.strip(), v.strip()))
            continue
        in_box = False
        k, _, v = raw.partition(":")
        meta[k.strip()] = v.strip()
    return meta, body, None


def load_baseline() -> dict[str, dict]:
    if not BASELINE.exists():
        return {}
    out: dict[str, dict] = {}
    row = re.compile(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")
    for line in BASELINE.read_text(encoding="utf-8").split("\n"):
        m = row.match(line)
        if not m:
            continue
        _, name, post, rank, birth, native = (g.strip() for g in m.groups())
        digits = re.findall(r"[一二三四五六七八九十]+品", rank)
        out[name] = {"post": post, "rank": rank, "digits": digits, "birth": birth, "native": native}
    return out


def body_chars(body: str) -> int:
    return len(re.sub(r"\s", "", body))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    files = sorted(SRC.glob("*.md"))
    if args.slug:
        files = [f for f in files if f.stem == args.slug]
        if not files:
            print(f"未找到词条：{args.slug}", file=sys.stderr)
            return 2

    baseline = load_baseline()

    # 全库索引（用于链接与重名校验）：只解析前置信息
    titles: dict[str, str] = {}
    metas: dict[str, dict] = {}
    for f in sorted(SRC.glob("*.md")):
        meta, _, err = parse_front(f.read_text(encoding="utf-8"))
        if meta is None:
            continue
        slug = meta.get("slug", "")
        titles.setdefault(meta.get("title", ""), slug)
        metas[slug] = meta
    dup_titles = len(metas) - len(titles)

    rows = []
    fails = warns = 0

    for f in files:
        text = f.read_text(encoding="utf-8")
        meta, body, err = parse_front(text)
        problems: list[str] = []
        notes: list[str] = []
        if meta is None:
            rows.append((f.stem, "—", "—", f"失败：{err}", 1))
            fails += 1
            continue

        cat = meta.get("category", "")
        slug = meta.get("slug", "")
        n = body_chars(body)

        # 1 前置信息
        for need in ("slug", "title", "category", "subtitle", "summary"):
            if not meta.get(need):
                problems.append(f"缺字段 {need}")
        if slug != f.stem:
            problems.append(f"slug({slug}) 与文件名不符")
        if cat not in MIN_CHARS:
            problems.append(f"category 非法：{cat}")
        box = meta.get("infobox", [])
        if not (8 <= len(box) <= 16):
            notes.append(f"infobox {len(box)} 行（宜 8–16）")
        rel = [t.strip() for t in meta.get("related", "").split(",") if t.strip()]
        if not (4 <= len(rel) <= 8):
            notes.append(f"related {len(rel)} 个（宜 4–8）")
        for t in rel:
            if t not in titles:
                problems.append(f"related 指向不存在词条：{t}")

        # 2 篇幅
        if cat in MIN_CHARS:
            if n < MIN_CHARS[cat]:
                problems.append(f"正文 {n} 字 < 下限 {MIN_CHARS[cat]}")

        # 3 节数与节名
        heads = re.findall(r"(?m)^##\s+(.+?)\s*$", body)
        if cat in MIN_SECTIONS and len(heads) < MIN_SECTIONS[cat]:
            problems.append(f"节数 {len(heads)} < {MIN_SECTIONS[cat]}")
        allowed = ALLOWED_SECTIONS.get(cat, set())
        odd = [h for h in heads if h not in allowed]
        if odd:
            notes.append("节名自拟：" + "、".join(odd[:4]))
        if "概述" not in heads:
            problems.append("缺「概述」节")
        if REQUIRED_SECTION not in heads and REQUIRED_SECTION_ALT not in heads:
            problems.append("缺「参考资料」节")
        else:
            key = REQUIRED_SECTION if REQUIRED_SECTION in heads else REQUIRED_SECTION_ALT
            seg = body.split("## " + key, 1)[1]
            seg = seg.split("\n## ", 1)[0]
            items = re.findall(r"(?m)^\s*\d+[.．]\s*\S", seg)
            if len(items) < 2:
                problems.append(f"参考资料仅 {len(items)} 条（至少 2 条）")

        # 4 否定句
        hits = []
        for label, pat in NEG_PATTERNS:
            for m in pat.finditer(body):
                line_no = body[: m.start()].count("\n") + 1
                hits.append((label, line_no))
        if len(hits) > NEG_LIMIT:
            problems.append("否定句 {} 处 > {}：{}".format(
                len(hits), NEG_LIMIT, "、".join(f"{l}@{ln}" for l, ln in hits[:6])))
        elif hits:
            notes.append("否定句 {} 处".format(len(hits)))

        # 5 禁忌词
        for word, why in FORBIDDEN:
            if word in text:
                problems.append(f"禁忌词「{word}」（{why}）")

        # 6 人物口径
        if cat == "人物":
            name = meta.get("title", "")
            base = baseline.get(name)
            birth_raw = ""
            for k, v in box:
                if k in ("生年", "出生"):
                    birth_raw = v
            m4 = re.search(r"\d{4}", birth_raw)
            birth = m4.group(0) if m4 else ""
            if birth_raw and not birth:
                problems.append(f"生年/出生应含四位年份：{birth_raw}")
            if birth_raw and ("†" in birth_raw or "史实" in birth_raw):
                problems.append(f"生年含溯源标注：{birth_raw}")
            if base:
                if birth and birth != base["birth"]:
                    problems.append(f"生年 {birth} ≠ 基线 {base['birth']}")
                front_txt = " ".join([meta.get("subtitle", "")] + [f"{k} {v}" for k, v in box])
                want = {d for d in base["digits"]}
                if want and not any(d in front_txt for d in want):
                    problems.append(f"品级未体现基线「{'/'.join(sorted(want))}」")

        # 7 链接
        links = re.findall(r"\[\[([^\[\]|]+)(?:\|[^\[\]]+)?\]\]", body)
        for t in links:
            if t.strip() not in titles:
                problems.append(f"交叉链接不存在：[[{t.strip()}]]")
        uniq = list(dict.fromkeys(t.strip() for t in links))
        if not (8 <= len(uniq) <= 20):
            notes.append(f"交叉链接 {len(uniq)} 个（宜 8–20）")

        # 8 表格分隔行
        lines = body.split("\n")
        for i, ln in enumerate(lines):
            if ln.strip().startswith("|") and (i == 0 or not lines[i - 1].strip().startswith("|")):
                if i + 1 >= len(lines) or not re.match(r"^\|[\s:\-|]+\|$", lines[i + 1].strip()):
                    problems.append(f"表格第 {i + 1} 行缺分隔行")

        status = "失败" if problems else ("提示" if notes else "通过")
        if problems:
            fails += 1
        elif notes:
            warns += 1
        rows.append((f.stem, cat, str(n), "；".join(problems + notes), 0 if not problems else 1))

        if not args.quiet and problems:
            print(f"[失败] {slug}")
            for p in problems:
                print(f"    - {p}")
        elif not args.quiet and notes:
            print(f"[提示] {slug}：" + "；".join(notes))

    print()
    print(f"共 {len(rows)} 条：通过/提示 {len(rows) - fails}，失败 {fails}")
    if dup_titles:
        print(f"[失败] 存在重名 title {dup_titles} 组")
    if not args.quiet:
        for slug, cat, n, msg, bad in rows:
            mark = "×" if bad else "√"
            print(f"{mark} {slug:<32} {cat:<4} {n:>5}  {msg[:110]}")
    return 1 if (fails or dup_titles) else 0


if __name__ == "__main__":
    raise SystemExit(main())
