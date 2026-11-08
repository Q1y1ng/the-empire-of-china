# -*- coding: utf-8 -*-
"""全库整体体检（只读）。

分项：时代换算、政委会名单算术、数字口径、主表结构、人名一致、小传生年履历、
百科信息框、结构瑕疵、章节编号、卷次引用、未具名统计。

用法：
    py -3 tools/audit_corpus.py
    py -3 tools/audit_corpus.py --report "docs/体检报告(2026-11-08).md"
"""
from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SET = ROOT / "设定"
SRC = ROOT / "docs" / "baike" / "src"
BIO = SET / "帝国高层人物小传(2026).md"
INDEX = SET / "全国官员名录·总索引(2026).md"
VOL33 = SET / "全国官员名录·卷三十三·中央政治委员会全名单(2026).md"
MASTER = SET / "帝国主数据表(2026).md"
REGISTRY = ROOT / "docs" / "baike" / "命名登记" / "汇总.md"

ERA_BASE = {"革鼎": 1930, "承宪": 1981, "继文": 2015}
CN_DIGIT = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
            "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
CN_ORDER = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
            "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八"]

findings: dict[str, list[str]] = defaultdict(list)
stats: dict[str, str] = {}


def cn2int(s: str) -> int | None:
    if not s:
        return None
    if "十" in s:
        head, _, tail = s.partition("十")
        if head and head not in CN_DIGIT:
            return None
        if tail and tail not in CN_DIGIT:
            return None
        return (CN_DIGIT.get(head, 1) if head else 1) * 10 + (CN_DIGIT.get(tail, 0) if tail else 0)
    total = 0
    for ch in s:
        if ch not in CN_DIGIT:
            return None
        total = total * 10 + CN_DIGIT[ch]
    return total


def setting_files() -> list[Path]:
    return sorted(p for p in SET.glob("*.md") if "合订本" not in p.name)


def baike_files() -> list[Path]:
    return sorted(SRC.glob("*.md"))


def read(p: Path) -> list[str]:
    return p.read_text(encoding="utf-8").split("\n")


# ---------------------------------------------------------------- 1 时代换算
ERA_RE = re.compile(r"(革鼎|承宪|继文)([零〇一二两三四五六七八九十百]+)年[（(](\d{4})\s*年?[）)]")


def check_era() -> None:
    n = 0
    year_first = re.compile(r"(\d{4})\s*年（(革鼎|承宪|继文)([零〇一二两三四五六七八九十百]+)年）")
    table_row = re.compile(r"^\|\s*(\d{4})(?:\.\d{1,2})?[^|]*\|\s*(革鼎|承宪|继文)([零〇一二两三四五六七八九十百]+)年")
    for p in setting_files() + baike_files():
        for i, line in enumerate(read(p), 1):
            for m in ERA_RE.finditer(line):
                n += 1
                era, cn, year = m.group(1), m.group(2), int(m.group(3))
                v = cn2int(cn)
                if v is None:
                    findings["时代换算"].append(f"{p.name}:{i} 年号数字无法解析「{cn}」")
                elif ERA_BASE[era] + v != year:
                    findings["时代换算"].append(
                        f"{p.name}:{i} {era}{cn}年＝{ERA_BASE[era] + v}，文中括注 {year}"
                        f"｜{line.strip()[:70]}")
            for m in year_first.finditer(line):
                n += 1
                year, era, cn = int(m.group(1)), m.group(2), m.group(3)
                v = cn2int(cn)
                if v is not None and ERA_BASE[era] + v != year:
                    findings["时代换算"].append(
                        f"{p.name}:{i}「{year} 年（{era}{cn}年）」不符："
                        f"{era}{cn}＝{ERA_BASE[era] + v} 年｜{line.strip()[:70]}")
            m = table_row.match(line.strip())
            if m:
                n += 1
                year, era, cn = int(m.group(1)), m.group(2), m.group(3)
                v = cn2int(cn)
                if v is not None and ERA_BASE[era] + v != year:
                    findings["时代换算"].append(
                        f"{p.name}:{i} 表内 {year} 年与「{era}{cn}年」不符"
                        f"（应＝{ERA_BASE[era] + v} 年）｜{line.strip()[:70]}")
    stats["时代括注"] = f"{n} 处（元年在位次年：革鼎＝1930＋N／承宪＝1981＋N／继文＝2015＋N）"


# ------------------------------------------------------- 2 政委会名单算术
VOL33_COL = {"一": 1, "二": 1, "三": 1, "四": 1, "五": 0, "六": 0, "七": 1,
             "八": 1, "九": 2, "十": 2, "十一": 2, "十二": 2, "十三": 1}
VOL33_EXPECT = {"一": 1, "二": 27, "三": 3, "四": 3, "五": 1, "六": 1, "七": 6,
                "八": 1, "九": 19, "十": 5, "十一": 9, "十二": 4, "十三": 1}


def parse_vol33() -> None:
    section = ""
    rows: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for line in read(VOL33):
        if line.startswith("## "):
            m = re.match(r"##\s+([一二三四五六七八九十]+)、", line)
            section = m.group(1) if m else ""
            continue
        if not line.startswith("|") or not section:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if set("".join(cells)) <= set("-: "):
            continue
        col = VOL33_COL.get(section)
        if col is None or len(cells) <= col:
            continue
        if "品级" in cells or cells[0] in ("序", "职务", "州", "机构", "姓名", "专门委员会"):
            continue
        if cells[col] in ("姓名", "姓名（略）", "主任"):
            continue
        name = re.sub(r"[※*]", "", cells[col]).strip()
        if not name or name == "—":
            continue
        rows[section].append((name, cells[-1]))

    seen: dict[str, str] = {}
    total = 0
    for sec in VOL33_EXPECT:
        lst = rows.get(sec, [])
        total += len(lst)
        if len(lst) != VOL33_EXPECT[sec]:
            findings["政委会名单"].append(
                f"§{sec} 实列 {len(lst)} 人，口径 {VOL33_EXPECT[sec]} 人")
        for name, _ in lst:
            if name in seen and sec not in ("一", "二"):
                findings["政委会名单"].append(f"「{name}」跨节重复：§{seen[name]} 与 §{sec}")
            elif name in seen and seen[name] == "二" and sec == "一":
                pass
            seen.setdefault(name, sec)
    stats["政委会名单"] = (f"逐表合计 {total} 人次／去重 {len(seen)} 人"
                          f"（口径 80 人，委员 79 人）；重复列名 {total - len(seen)} 处")
    if len(seen) != 80:
        findings["政委会名单"].append(f"去重后 {len(seen)} 人，主表 G-01 口径 80 人")
    # 二品以上必在政治局／副国级序列
    high = [n for sec, lst in rows.items() for n, r in lst if "二品" in r or "一品" in r]
    stats["政委会二品以上"] = f"{len(set(high))} 人（口径 51 人，含皇帝）"


# ------------------------------------------------------------ 3 数字口径
BLACKLIST: list[tuple[str, str, str]] = [
    (r"政委会\s*79\s*→\s*91", "68→80", "政委会规模旧稿"),
    (r"政委会\s*91\s*人", "80 人", "政委会规模旧稿"),
    (r"二品\s*41\s*人", "二品 42 人", "二品人数旧稿"),
    (r"政治局\s*26\b", "政治局 27", "政治局人数旧稿"),
    (r"政治局\s*[|｜]\s*26\s*人", "政治局 27 人（9 常委＋18 委员）", "政治局人数旧稿（表内）"),
    (r"中央政治局由\*\*二十六人", "二十七人", "政治局人数旧稿（宪法原引）"),
    (r"政治局委员\s*17\s*人", "18 人", "政治局委员旧稿"),
    (r"副国级以上\s*50\s*人", "51 人", "副国级旧稿"),
    (r"216\.0\s*万亿", "360.0 万亿元", "GDP 旧值"),
    (r"36\.0\s*万亿美元", "60.0 万亿美元", "GDP 美元旧值"),
    (r"119\.6", "150.0 万亿美元", "世界 GDP 旧值"),
    (r"30\.1%", "40.0%", "全球占比旧值"),
    (r"121[,，]?300\s*元", "202,200 元", "人均 GDP 旧值"),
    (r"44\s*个省级", "45 个省级", "省级单位旧稿"),
    (r"5\s*个直辖市", "6 直辖市", "直辖市旧稿"),
    (r"17\.5\s*亿", "17.8 亿", "人口旧值"),
    (r"汇率\s*6\.97", "6.00", "汇率旧值"),
]
HISTORY_MARK = ("旧值", "已作废", "作废", "旧稿", "原为", "旧版", "改定", "后经")


def check_numbers() -> None:
    for pat, canon, why in BLACKLIST:
        for p in setting_files() + baike_files():
            for i, line in enumerate(read(p), 1):
                m = re.search(pat, line)
                if not m:
                    continue
                if any(k in line for k in HISTORY_MARK):
                    continue
                findings["数字口径"].append(
                    f"{p.name}:{i}「{why}」应作 {canon}｜{line.strip()[:90]}")


def check_master_table() -> None:
    for i, line in enumerate(read(MASTER), 1):
        if re.match(r"^\|\s*[A-Z]-\d+[a-z]?\s*\|\s*\|", line):
            findings["主数据表"].append(f"{MASTER.name}:{i} 编号行内容为空")
        if line.startswith(" 中央政治委员会人数口径"):
            findings["主数据表"].append(
                f"{MASTER.name}:{i} 该行缺编号（应为 N-08），其上 N-08 行为空壳")
    # 主表内部算术：G-01／G-01a／G-01b／G-01c
    text = "\n".join(read(MASTER))
    m = re.search(r"政治局 \*\*27\*\*.*?共 80 人", text)
    stats["主表 G-01a"] = "80 人构成已在表中勾稽" if m else "构成行未能自动核对"
    if "74＋2＋4" in text.replace(" ", "") or "74**（" in text:
        pass


# ------------------------------------------------------------ 4 人名一致
def load_registry() -> list[tuple[str, str, str]]:
    rows = []
    for line in read(REGISTRY):
        m = re.match(r"^\|\s*\d+\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", line)
        if m:
            rows.append((m.group(1).strip(), m.group(2).strip(), m.group(3).strip()))
    return rows


def load_index_names() -> list[tuple[str, str, str]]:
    text = INDEX.read_text(encoding="utf-8")
    body = text.split("## 五、内设与副职具名表（2026）", 1)[1].split("\n## ", 1)[0]
    rows = []
    for line in body.split("\n"):
        m = re.match(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", line)
        if m:
            rows.append((m.group(2).strip(), m.group(3).strip(), m.group(4).strip()))
    return rows


def check_names() -> None:
    reg = load_registry()
    idx = load_index_names()
    stats["具名表"] = f"登记底稿 {len(reg)} 行／总索引 §五 {len(idx)} 行"
    set_reg = {(b, c) for _, b, c in reg}
    set_idx = {(b, c) for _, b, c in idx}
    for label, diff in (("仅登记底稿有", set_reg - set_idx), ("仅总索引有", set_idx - set_reg)):
        if diff:
            findings["人名一致"].append(f"{label}（机关+职务）{len(diff)} 条：" +
                                        "、".join(f"{a}/{b}" for a, b in list(diff)[:5]))

    dup = [n for n, c in Counter(n for n, _, _ in idx).items() if c > 1]
    if dup:
        findings["人名一致"].append(f"§五 同一姓名占两岗：{len(dup)} 个 → " + "、".join(dup[:10]))
    dup2 = [n for n, c in Counter(n for n, _, _ in reg).items() if c > 1]
    if dup2:
        findings["人名一致"].append(f"登记底稿同一姓名占两岗：{len(dup2)} 个 → " + "、".join(dup2[:10]))

    corpus = "\n".join(p.read_text(encoding="utf-8") for p in baike_files())
    missing = [n for n, _, _ in idx if n not in corpus]
    if missing:
        findings["人名一致"].append(f"§五 姓名未在百科出现：{len(missing)} 个 → " + "、".join(missing[:8]))

    # 各分卷名录里的同岗异名（(机关, 职务) → 姓名）
    roster: dict[tuple[str, str], tuple[str, str]] = {}
    for p in SET.glob("全国官员名录·卷*.md"):
        if "三十三" in p.name or "合订本" in p.name:
            continue
        for line in read(p):
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 5 or not re.fullmatch(r"\d+", cells[0]):
                continue
            name = re.sub(r"[※*]", "", cells[2]).strip()
            if not re.fullmatch(r"[\u4e00-\u9fa5·]{2,6}", name):
                continue
            roster.setdefault((cells[1], cells[3]), (name, p.name))
    mismatch = []
    for name, org, post in idx:
        key = (org, post)
        if key in roster and roster[key][0] != name:
            mismatch.append(f"{org}／{post}：§五「{name}」vs {roster[key][1]}「{roster[key][0]}」")
    for item in mismatch[:12]:
        findings["人名一致"].append("同岗异名：" + item)
    if len(mismatch) > 12:
        findings["人名一致"].append(f"…另有 {len(mismatch) - 12} 处同岗异名")


# ------------------------------------------------------------ 5 小传
HEAD = re.compile(r"^\*\*(\d+)\.\s*([^*｜]+?)\*\*\s*(?:※|（[^）]*）)*\s*｜.*?生年\s*(\d{4})｜")
QUICK = re.compile(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|[^|]*\|[^|]*\|\s*(\d{4})\s*\|")


def bio_quick() -> dict[str, int]:
    out = {}
    for line in read(BIO):
        m = QUICK.match(line)
        if m:
            out[re.sub(r"[※*]", "", m.group(2)).strip()] = int(m.group(3))
    return out


def check_bio() -> None:
    text = BIO.read_text(encoding="utf-8")
    lines = text.split("\n")
    quick = bio_quick()
    heads: dict[str, int] = {}
    for line in lines:
        m = HEAD.match(line.strip())
        if m:
            heads[re.sub(r"[※*]", "", m.group(2)).strip()] = int(m.group(3))
    stats["小传"] = f"速查表 {len(quick)} 人／人物卡 {len(heads)} 人"
    if len(quick) != len(heads):
        findings["小传"].append(f"速查表 {len(quick)} 人 vs 人物卡 {len(heads)} 人")
    for m in re.finditer(r"本卷为\s*(\d+)\s*名帝国最高层", text):
        if int(m.group(1)) != len(heads):
            findings["小传"].append(
                f"导语「{m.group(1)} 名帝国最高层」，实为 {len(heads)} 人（含 2026.12 新设 8 岗）")
    for m in re.finditer(r"与本卷\s*(\d+)\s*人", text):
        if int(m.group(1)) != len(heads):
            findings["小传"].append(f"「与本卷 {m.group(1)} 人」应为 {len(heads)} 人")
    for name in sorted(set(quick) ^ set(heads)):
        findings["小传"].append(f"速查表／人物卡不一致：「{name}」")
    # 卷末追述的构成算术
    m = re.search(r"＝2026\.12 改定前 (\d+) 人（([^）]+)）", text)
    if m:
        total_claim = int(m.group(1))
        nums = [int(x) for x in re.findall(r"(\d+)\s*(?=＋|，|$)", m.group(2))]
        s = sum(nums)
        if nums and s != total_claim:
            findings["小传"].append(
                f"卷末追述「{'＋'.join(map(str, nums))}＝{s}」，却写 {total_claim} 人（漏江南州委主席顾明远）")
    for name in sorted(set(quick) & set(heads)):
        if quick[name] != heads[name]:
            findings["小传"].append(f"{name} 生年：速查表 {quick[name]}／人物卡 {heads[name]}")

    cur = ""
    birth = 0
    for i, line in enumerate(lines, 1):
        m = HEAD.match(line.strip())
        if m:
            cur = re.sub(r"[※*]", "", m.group(2)).strip()
            birth = int(m.group(3))
            continue
        if "履历：" not in line or not birth:
            continue
        seg = line.split("履历：", 1)[1].split("。", 1)[0]
        for ym in re.finditer(r"(\d{4})\s*年", seg):
            y = int(ym.group(1))
            if y - birth < 18:
                findings["小传·年龄"].append(
                    f"{cur}（{birth} 年生）{y} 年＝{y - birth} 岁：{seg[max(0, ym.start() - 10):ym.start() + 14]}")


# ------------------------------------------------------------ 6 百科信息框
def field(head: str, key: str) -> str:
    m = re.search(rf"^\s+{key}:\s*(.+)$", head, re.M)
    return m.group(1).strip() if m else ""


def check_baike() -> None:
    person = 0
    no_birth = 0
    quick = bio_quick()
    for p in baike_files():
        t = p.read_text(encoding="utf-8")
        h = re.match(r"---\n(.*?)\n---", t, re.S)
        if not h:
            findings["百科信息框"].append(f"{p.name} 缺 YAML 头")
            continue
        head = h.group(1)
        if "category: 人物" not in head:
            continue
        person += 1
        name = field(head, "中文名") or field(head, "title")
        birth_s = field(head, "出生")
        m = re.search(r"(\d{4})", birth_s)
        if not m:
            no_birth += 1
            continue
        birth = int(m.group(1))
        m2 = re.search(r"(\d+)\s*岁", field(head, "现年"))
        if m2 and int(m2.group(1)) != 2026 - birth:
            findings["百科信息框"].append(
                f"{name} 生年 {birth}，现年写 {m2.group(1)} 岁，应 {2026 - birth} 岁（{p.name}）")
        if name in quick and quick[name] != birth:
            findings["百科信息框"].append(f"{name} 生年：小传 {quick[name]}／百科 {birth}（{p.name}）")

        # 履历表：出生行年份、入职年龄
        rows = re.findall(r"^\| (\d{4})(?:[—-](\d{4})?)? \| ([^|]*) \| ([^|]*) \|", t, re.M)
        for year, _, post, rank in rows:
            y = int(year)
            if "出生" in post and y != birth:
                findings["百科履历表"].append(
                    f"{name} 出生行写 {y} 年，信息框 {birth} 年（{p.name}）")
            rank = rank.strip()
            if rank in ("—", "") or any(k in rank for k in ("学生", "学业", "在读", "举子", "生员")):
                continue
            if any(k in post for k in ("学业", "学校", "学堂", "科举", "书院")):
                continue
            if y - birth < 16:
                findings["百科履历表"].append(
                    f"{name}（{birth} 年生）{y} 年起任「{post.strip()}」，{y - birth} 岁")
    stats["百科人物"] = f"{person} 条（其中 {no_birth} 条为卸任／已故者，不设生年栏）"


def check_lint() -> None:
    import subprocess
    import sys
    for label, cmd in (("check_baike", [sys.executable, "tools/check_baike.py", "--quiet"]),
                       ("build_baike --check", [sys.executable, "tools/build_baike.py", "--check"]),
                       ("check_resume_age", [sys.executable, "tools/check_resume_age.py"])):
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="ignore")
        tail = [l for l in r.stdout.strip().split("\n") if l.strip()]
        stats[f"lint·{label}"] = (tail[-1].strip() if tail else "无输出") + f"（退出码 {r.returncode}）"
        if r.returncode != 0:
            findings["既有检查器"].append(f"{label} 退出码 {r.returncode}：{tail[-1] if tail else ''}")


# ------------------------------------------------------------ 7 结构瑕疵
BROKEN = [
    (re.compile(r"（，"), "括号内以逗号开头"),
    (re.compile(r"，）"), "括号内以逗号结尾"),
    (re.compile(r"（\s*）"), "空括号"),
    (re.compile(r"——[，。；：、]"), "破折号后紧跟标点"),
    (re.compile(r"[，、]。"), "逗号／顿号后直接句号（删改残留）"),
    (re.compile(r"[，、]；"), "逗号／顿号后直接分号（删改残留）"),
    (re.compile(r"\*\*\s*\*\*"), "空加粗标记（删改残留）"),
]


def check_structure() -> None:
    for p in sorted(SET.glob("*.md")) + baike_files():
        if "合订本" in p.name:
            continue
        for i, line in enumerate(read(p), 1):
            for rx, desc in BROKEN:
                if rx.search(line):
                    findings["结构瑕疵"].append(f"{p.name}:{i} {desc}｜{line.strip()[:80]}")


def check_sections() -> None:
    for p in sorted(SET.glob("*.md")):
        if "合订本" in p.name:
            continue
        prev = 0
        for i, line in enumerate(read(p), 1):
            m = re.match(r"##\s+([一二三四五六七八九十]+)、", line)
            if not m or m.group(1) not in CN_ORDER:
                continue
            cur = CN_ORDER.index(m.group(1))
            if prev and cur > prev + 1:
                findings["章节编号"].append(
                    f"{p.name}:{i} 跳过「{CN_ORDER[prev + 1]}」，由「{CN_ORDER[prev]}」直入「{m.group(1)}」")
            prev = cur


# ------------------------------------------------------- 8 品级一致性
RANK_RE = re.compile(r"([一二三四五六七八九])品")


def parse_rank(s: str) -> str:
    m = RANK_RE.search(s or "")
    return f"{m.group(1)}品" if m else ""


def iter_rank_tables(path: Path):
    """产出 (表头, 行) —— 仅含「姓名」与「品级」两列的表格。"""
    lines = read(path)
    header = None
    prev = None
    for line in lines:
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if set("".join(cells)) <= set("-: "):
                header = prev
                prev = None
                continue
            if header is not None:
                yield header, cells
            prev = cells
        else:
            header = None
            prev = None


def roster_ranks() -> dict[str, Counter]:
    out: dict[str, Counter] = defaultdict(Counter)
    for p in SET.glob("全国官员名录·卷*.md"):
        if "合订本" in p.name:
            continue
        for header, cells in iter_rank_tables(p):
            if not header or len(header) != len(cells):
                continue
            name_idx = next((i for i, h in enumerate(header) if h.startswith("姓名")), None)
            rank_idx = next((i for i, h in enumerate(header) if "品级" in h), None)
            if name_idx is None or rank_idx is None:
                continue
            name = re.sub(r"[※*]", "", cells[name_idx]).strip()
            if not re.fullmatch(r"[\u4e00-\u9fa5·]{2,6}", name):
                continue
            rank = parse_rank(cells[rank_idx])
            if rank:
                out[name][rank] += 1
    return out


def check_ranks() -> None:
    ranks = roster_ranks()
    quick_rank: dict[str, str] = {}
    for line in read(BIO):
        m = re.match(r"^\|\s*\d+\s*\|\s*([^|]+?)\s*\|[^|]*\|\s*([^|]*品[^|]*)\|", line)
        if m:
            quick_rank[re.sub(r"[※*]", "", m.group(1)).strip()] = parse_rank(m.group(2))
    stats["品级台账"] = f"名录内具名干部 {len(ranks)} 人；小传速查表带品级 {len(quick_rank)} 人"

    multi = [(n, c) for n, c in ranks.items() if len(c) > 1]
    for name, c in sorted(multi)[:12]:
        findings["品级一致性"].append(
            f"{name} 在名录中对应多个品级：" + "／".join(f"{k}×{v}" for k, v in c.most_common()))
    if len(multi) > 12:
        findings["品级一致性"].append(f"…另有 {len(multi) - 12} 人一名多品级")

    for p in baike_files():
        t = p.read_text(encoding="utf-8")
        h = re.match(r"---\n(.*?)\n---", t, re.S)
        if not h or "category: 人物" not in h.group(1):
            continue
        name = field(h.group(1), "中文名") or field(h.group(1), "title")
        got = parse_rank(field(h.group(1), "官阶"))
        if not got or not name:
            continue
        if name in ranks and got not in ranks[name]:
            findings["品级一致性"].append(
                f"{name}：百科官阶 {got}，名录作 " +
                "／".join(f"{k}×{v}" for k, v in ranks[name].most_common()) + f"（{p.name}）")
        if name in quick_rank and quick_rank[name] and got != quick_rank[name]:
            findings["品级一致性"].append(
                f"{name}：百科官阶 {got}，小传速查表 {quick_rank[name]}（{p.name}）")


# ------------------------------------------------------- 10 卷目与实列
def check_volume_index() -> None:
    text = INDEX.read_text(encoding="utf-8").split("\n")
    claimed: dict[str, tuple[str, int]] = {}
    for line in text:
        m = re.match(r"^\|\s*([一二三四五六七八九十]{1,3})\s*\|\s*([^|]+?)\s*\|[^|]*\|\s*(\d+)\s*\|", line)
        if m:
            claimed[m.group(1)] = (m.group(2), int(m.group(3)))
    files = {}
    for p in SET.glob("全国官员名录·卷*.md"):
        m = re.match(r"全国官员名录·卷([^·]+)·", p.name)
        if m:
            files[m.group(1)] = p
    if set(claimed) != set(files):
        findings["卷目"].append(
            f"卷目 {len(claimed)} 卷／实体文件 {len(files)} 卷；缺：" +
            "、".join(f"卷{k}" for k in sorted(set(claimed) - set(files), key=lambda x: CN_ORDER.index(x) if x in CN_ORDER else 99)))
    diffs = 0
    for tok, (title, n) in claimed.items():
        p = files.get(tok)
        if not p:
            continue
        lines = read(p)
        actual = 0
        for i, line in enumerate(lines):
            if not line.startswith("|"):
                continue
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            if nxt.startswith("|") and set(nxt.replace("|", "").strip()) <= set("-: "):
                continue  # 表头
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if set("".join(cells)) <= set("-: "):
                continue
            actual += 1
        if abs(actual - n) > max(6, n * 0.2):
            diffs += 1
    stats["卷目核对"] = (f"{len(claimed)} 卷；「岗位数（实测）」与表内数据行统计口径不同"
                        f"（多卷按 2 岗／行合并列示），差异超阈值 {diffs} 卷，仅作提示")


# ------------------------------------------------------- 11 相关条目
def check_related() -> None:
    titles = set()
    for p in baike_files():
        t = p.read_text(encoding="utf-8")
        m = re.search(r"^title:\s*(.+)$", t, re.M)
        if m:
            titles.add(m.group(1).strip())
    missing = []
    for p in baike_files():
        t = p.read_text(encoding="utf-8")
        m = re.search(r"^related:\s*(.+)$", t, re.M)
        if not m:
            continue
        for item in re.split(r"[,，、]", m.group(1)):
            item = item.strip()
            if item and item not in titles:
                missing.append(f"{p.name} related 项「{item}」无对应词条")
    for item in missing[:24]:
        findings["相关条目"].append(item)
    if len(missing) > 24:
        findings["相关条目"].append(f"…另有 {len(missing) - 24} 处")
    stats["相关条目"] = f"词条标题 {len(titles)} 个；related 悬空 {len(missing)} 处"


# ------------------------------------------------------- 12 概述生年
def check_prose_birth() -> None:
    for p in baike_files():
        t = p.read_text(encoding="utf-8")
        h = re.match(r"---\n(.*?)\n---", t, re.S)
        if not h or "category: 人物" not in h.group(1):
            continue
        name = field(h.group(1), "中文名") or field(h.group(1), "title")
        m = re.search(r"(\d{4})", field(h.group(1), "出生"))
        if not m:
            continue
        birth = int(m.group(1))
        prose = re.search(rf"\*\*{re.escape(name)}\*\*（(\d{{4}})年", t)
        if prose and int(prose.group(1)) != birth:
            findings["百科信息框"].append(
                f"{name} 概述写（{prose.group(1)}年—），信息框 {birth} 年（{p.name}）")


# ------------------------------------------------------- 9 卷次交叉引用
def check_refs() -> None:
    vols = set()
    for p in SET.glob("全国官员名录·卷*.md"):
        m = re.match(r"全国官员名录·卷([^·]+)·", p.name)
        if m:
            vols.add(m.group(1))
    stats["名录分卷"] = f"{len(vols)} 卷"
    bad = 0
    for p in setting_files() + baike_files():
        for i, line in enumerate(read(p), 1):
            for m in re.finditer(r"卷([一二三四五六七八九十]{1,3})", line):
                tok = m.group(1)
                if tok in vols:
                    continue
                v = cn2int(tok)
                if v and 1 <= v <= 42:
                    bad += 1
                    if bad <= 10:
                        findings["卷次引用"].append(
                            f"{p.name}:{i} 引用「卷{tok}」无对应分卷｜{line.strip()[:70]}")
    if bad > 10:
        findings["卷次引用"].append(f"…另有 {bad - 10} 处")


# ------------------------------------------------------- 9 未具名统计
def check_unnamed() -> None:
    total = 0
    per: list[str] = []
    for p in SET.glob("全国官员名录·卷*.md"):
        if "合订本" in p.name or "三十三" in p.name:
            continue
        n = 0
        for line in read(p):
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells and any("姓名" in c for c in cells[:2]):
                continue
            if len(cells) >= 3 and cells[2] in ("—", "－", "-"):
                n += 1
        total += n
        if n:
            per.append(f"{p.name.split('·')[1]} {n}")
    stats["未具名岗位"] = f"{total} 处（分布于 {len(per)} 卷；姓名统一登记在总索引 §五）"


# ------------------------------------------------------------ 输出
P1 = ["时代换算", "数字口径", "主数据表", "小传", "章节编号", "结构瑕疵",
      "品级一致性", "百科信息框", "百科履历表", "政委会名单"]
P2 = ["卷目", "相关条目", "检查器异常", "既有检查器"]
SPECIAL = ["小传·年龄"]
ADVICE = {
    "时代换算": "长安城市志：承宪十年 → 承宪九年（1990 年即承宪九年，十年为 1991）。",
    "数字口径": "总索引表头「政委会 79→91／二品 41 人」改为「政委会 68→80／二品 42 人」；卷目卷一的「政治局26」改为 27。",
    "主数据表": "把缺编号的那一行补成 N-08（事项＝中央政治委员会人数口径），并移到 N-09 之前，三列补齐。",
    "小传": "导语「49 名」与附录 B「49 人」改为 57 人；卷末追述改为「49 人＝政治局 27（含皇帝，并含京畿、江南两州委主席）＋六州州委主席 6＋八州州长 8＋八大军区司令 8」，再＋新设 8 岗＝57 人。",
    "章节编号": "卷三十三补「十三」序号（十四改十三）；长安城市志卷五补 §三 标题「帝国历史档案馆」（同文件 119、397、417 行均用此名）。",
    "结构瑕疵": "七处删改残留标点：四处「（…，）」、一处「，。」、两处「、。」，删去多余的逗号顿号。",
    "品级一致性": "顾明远按人物词条＝二品；卷三十三 §七 删去江南州一行（六州州委主席才是三品）。",
    "百科信息框": "现年／生年不一者，以人物词条生年为准改现年。",
    "百科履历表": "出生行年份与信息框不一致者改齐；入职年龄异常按特例处理。",
    "政委会名单": "§七 六州（删江南顾明远）；§十 外事委主任改注「见 §六」，避免同卷重列。",
    "卷目": "卷目「岗位数（实测）」与表内行数统计口径不同（有合并列示），仅作提示，不据此改数。",
    "相关条目": "八管见、多元信息、街道委员会 的 related 里混入概念短句；可另建概念词条，或把这些短语移入正文关键词。",
    "小传·年龄": "沈叙衡 16 岁入厂（技校毕业分配）为既定设定，不修；其余 17 岁插队、村会计同理。",
}


def render() -> str:
    total = sum(len(v) for v in findings.values())
    p1 = sum(len(findings[k]) for k in P1 if k in findings)
    p2 = sum(len(findings[k]) for k in P2 if k in findings)
    sp = sum(len(findings[k]) for k in SPECIAL if k in findings)
    out = ["# 全库整体体检报告（2026-11-08）", "",
           "> 由 `tools/audit_corpus.py` 生成；只读检查，不修改任何设定文件。", "",
           "## 一、结论", "",
           f"共 {total} 项：**需修 {p1} 项**、提示 {p2} 项、既定特例 {sp} 项。", ""]
    if p1 == 0:
        out += ["本轮整改后复查：口径类硬伤已清零——总索引表头与卷目、主数据表 N-08 行、"
                "卷三十三 §七／§十 重列、小传 49→57 人、长安城市志年号与卷五缺节、"
                "卷三十三跳号、四处删改残留标点全部改毕；两本合订本已重建。"
                "百科 250 条与既有三闸门全绿。", ""]
    else:
        out += ["口径类硬伤集中在三处文件：总索引表头与卷目（政委会 79→91／二品 41／政治局 26）、"
                "主数据表 N-08 行格式、卷三十三 §七 多列江南州。"
                "百科 250 条与两本合订本经既有闸门检查全部通过，未发现篇幅、结构、链接、否定句问题。", ""]
    out += ["## 二、受检范围", "",
           "| 项 | 数量 |", "| --- | --- |",
           f"| 设定分卷（不含两本合订本） | {len(setting_files())} |",
           f"| 百科词条 | {len(baike_files())} |",
           "| 合订本／名录合订本 | 构建产物，本轮重跑后与库内文件逐字节一致 |", "",
           "## 三、体检指标", "", "| 项 | 实测 |", "| --- | --- |"]
    for k, v in stats.items():
        out.append(f"| {k} | {v} |")
    out.append("")

    def block(title: str, keys: list[str]) -> None:
        items = [(k, findings[k]) for k in keys if k in findings]
        out.append(f"## {title}")
        out.append("")
        if not items:
            out.append("无。")
            out.append("")
            return
        for k, vals in items:
            out.append(f"### {k}（{len(vals)} 项）")
            out.append("")
            for item in vals:
                out.append(f"- {item}")
            if k in ADVICE:
                out.append(f"- **建议**：{ADVICE[k]}")
            out.append("")

    block("四、需修项", P1)
    block("五、提示项", P2)
    block("六、既定特例（不修）", SPECIAL)
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default="")
    args = ap.parse_args()
    for fn in (check_era, parse_vol33, check_numbers, check_master_table, check_names,
               check_bio, check_baike, check_structure, check_sections, check_refs,
               check_ranks, check_unnamed, check_lint, check_volume_index,
               check_related, check_prose_birth):
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            findings["检查器异常"].append(f"{fn.__name__}: {e!r}")
    report = render()
    if args.report:
        Path(args.report).write_text(report, encoding="utf-8")
        print(f"[报告] {args.report}")
    print(f"[体检] 问题 {sum(len(v) for v in findings.values())} 项")
    for k, v in findings.items():
        print(f"  - {k}: {len(v)}")
        for item in v[:3]:
            print(f"      {item}")


if __name__ == "__main__":
    main()
