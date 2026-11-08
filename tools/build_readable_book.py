#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《中华帝国设定全书（2026）》可读本生成器。

把《中华帝国设定集·全卷合订本》转为**可手改的活文档**：
  * 去掉「勿手改」锁，明确可编辑；
  * 为每个「总设定」单元加「导读」角色标签（原则层 vs 数据层）；
  * 对有独立分卷的摘要单元，用 H3 小目录 + 指针替代冗余正文（去重）；
  * 末尾附「覆盖清单」与「同步约定」。

用法：
    py -3 tools/build_readable_book.py            # 生成 设定/中华帝国设定全书(2026).md
    py -3 tools/build_readable_book.py --check    # 只报告，不写文件
"""
import argparse
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTING = os.path.join(ROOT, '设定')
SRC = os.path.join(SETTING, '中华帝国设定集·全卷合订本(2026).md')
OUT = os.path.join(ROOT, '中华帝国设定全书(2026).md')

# 摘要单元 -> 独立分卷（去重：正文替换为导读小目录 + 指针）
#   匹配 compendium 中的 H2 标题（无 〔总设定〕 标记）
DEDUP = {
    '第十八编：世界近现代历史影响': '《世界近代史推演（约1360—2026）》（本卷后文）',
    '第十九编：亚洲/欧亚国际秩序': '《世界近代史推演（约1360—2026）》（本卷后文）',
    '第三编：疆域与行政区划': '《疆域与省界表（2026）》（本卷后文）',
    '第十六编：长安与国家象征体系': '《长安城市志》（本卷后文）',
    '第二十六编：国家象征体系（推演细化）': '《长安城市志》（本卷后文）',
    '第九编：军事体系': '《全国军事编制设定（2026）》（本卷后文）',
}

# 原则层单元（保留正文，但标角色）——总设定独有内容，无独立分卷或互补
PRINCIPLE = {
    '第一编：世界观总览',
    '第二编：帝国起源与建国',
    '第四编：皇室与皇位继承',
    '第五编：现代政治制度',
    '第六编：中央国家机构',
    '第七编：地方行政制度',
    '第八编：司法、监察与监督',
    '第十编：经济体系',
    '第十一编：社会福利体系',
    '第十二编：教育与人才体系',
    '第十三编：科技与AI时代',
    '第十四编：民族与自治制度',
    '第十五编：文化、身份与国家认同',
    '第十七编：帝国历史年表',
    '第二十编：帝国政治理论',
    '第二十一编：合法性理论',
    '第二十二编：王朝周期律与大革命理论',
    '第二十三编：典型政治事件推演',
    '第二十四编：已裁决问题与待决清单',
    '第二十五编：社会生活与民俗（推演细化）',
    '附录一：帝国机构品级总表（按一把手品级算·2026冻结版）',
    '附录二：帝国军队层级与军衔表（2026修订版·独立于文官品级）',
}

FRONT = '''# 《中华帝国设定全书（2026）》

> **性质**：本册是**整编产物**（`tools/build_readable_book.py` 自《中华帝国设定集·全卷合订本(2026)》生成），替代 2026-11 之前的手工整编本。它以分册为唯一来源，重跑即覆盖；**要长期改动请改分册后重跑本脚本**，不要只改本册。
> **与分册的关系**：分册（`设定/` 下各 `.md`）仍是**权威源**；本册是它们的**策展与整合**。若本册与分册冲突，**以分册为准**，重跑脚本即可消除差异。
> **与《合订本》的关系**：《中华帝国设定集·全卷合订本(2026).md》为零遗漏全文本（含名录，脚本生成），供归档与完整性校验；本册是它的「可读、去重」版本，并移除全国官员名录。
> **人物口径**：本可读本**只保留有人物小传的官员**（见第五卷《帝国高层人物小传》57 人：政治局 27（含皇帝、京畿与江南两州委主席）＋六州州委主席 6＋八州州长 8＋八大军区司令 8，另 2026.12 新设副国级 8 人），全国官员名录（42 卷）已移出本册；名录源文件本身未改动。
> **体例**：卷为一级标题、单元为二级标题、单元内标题整体降一级；各单元保留原编/卷编号，以便与分册及文内交叉引用对照。
> **角色标签**：〔总设定〕单元中，标【原则层】者保留制度条款（总设定的独有内容），标【导读】者已去重、正文替换为小目录与指针（全文见本卷后文的专用分卷）。【冻结】【推演】【待定】标注照录原文。
> **同步约定**：本册由脚本生成，改动分册后重跑 `tools/build_readable_book.py` 即同步；CHANGELOG「### 修复／### 变更」照常记录。
> **编制日期**：{date}（继文十一年）。

**总目**

{toc}

---

'''

CHECKLIST = '''

---

# 附录：覆盖清单与同步约定

## A. 覆盖清单（本册 ↔ 分册）

| 分册 | 在本册中的位置 | 状态 |
|---|---|---|
| 《中华帝国世界观总设定 v2.0》 | 第一~第九卷各〔总设定〕单元 | 已整合（原则层保留、摘要层去重） |
| 《中华帝国编年史 1700-2026》 | 第二卷「内史」 | 已整合（全文） |
| 《世界近代史推演》 | 第三卷「世界·外史」 | 已整合（全文） |
| 《长安城市志》 | 第四卷「疆域与首都」 | 已整合（全文） |
| 《全国高等教育设定(2026)》 | 第八卷「文教·科技·民族」 | 已整合（全文） |
| 《全国军事编制设定(2026)》 | 第六卷「军事」 | 已整合（全文） |
| 《全国官员名录》总索引+42卷 | —— | **本可读本已移除**（用户裁决：只保留有人物小传的官员；名录源文件仍保留于 `设定/`，未改动） |
| 《帝国主数据表(2026)》 | 第一卷「总纲」 | 已整合（全文） |
| 《疆域与省界表(2026)》 | 第四卷「疆域与首都」 | 已整合（全文） |
| 《国民议会(2026)》 | 第五卷「皇室与政制」 | 已整合（全文） |
| 《法律要目(2026)》 | 第五卷「皇室与政制」 | 已整合（全文） |
| 《帝国高层人物小传(2026)》 | 第五卷「皇室与政制」 | 已整合（全文） |
| 《帝国百科·沈叙衡(2026)》 | 第五卷「皇室与政制」 | 已整合（全文） |
| 《经济数据切片(2026)》 | 第七卷「经济与民生」 | 已整合（全文） |
| 《非常设机构通则(2026)》 | 第七卷「经济与民生」 | 已整合（全文） |

## B. 同步约定（给编辑者）

1. **分册是权威源**：本册与分册冲突时，以分册为准。
2. **改动分册后**：如影响本册，同步对应单元；在 CHANGELOG「### 变更」记一行。
3. **新增分册**：必须同步到本册对应卷，或在本附录登记「未整合」。
4. **去重原则**：总设定单元只保留「原则层」；数据/名录一律只在专用分卷出现一次。若发现重复，删摘要侧，保留分卷侧。
5. **数字**：冻结值只在《帝国主数据表》写全值；本册其他位置写「值（见主表 X-XX）」或直接引用，不重复定义口径。

## C. 去重记录（本次生成）

- 去重单元（正文 → 导读小目录+指针）：{dedup_list}
- 原则层单元（保留正文，标【原则层】）：{principle_list}
- 其余〔总设定〕单元：保留正文（无独立分卷，本单元为唯一叙述）。

*本附录由 `tools/build_readable_book.py` 生成；本册其余内容可自由手改。*
'''


def read(path):
    with open(path, encoding='utf-8') as fh:
        return fh.read()


def split_units(text):
    """把全文拆成 (卷列表)：每卷 = (H1行, [ (H2标题, 正文块) ])。"""
    lines = text.split('\n')
    volumes = []  # list of (h1_line, list of (h2_title, body_lines))
    cur_vol = None
    cur_unit = None
    cur_body = []
    for line in lines:
        if line.startswith('# ') and not line.startswith('## '):
            if cur_vol is not None:
                if cur_unit is not None:
                    cur_vol[1].append((cur_unit, '\n'.join(cur_body).strip()))
                volumes.append(cur_vol)
            cur_vol = [line, []]
            cur_unit = None
            cur_body = []
            continue
        if line.startswith('## '):
            if cur_vol is None:
                cur_vol = [None, []]
            if cur_unit is not None:
                cur_vol[1].append((cur_unit, '\n'.join(cur_body).strip()))
            cur_unit = line[3:].strip()
            cur_body = []
            continue
        if cur_vol is not None:
            cur_body.append(line)
    if cur_vol is not None:
        if cur_unit is not None:
            cur_vol[1].append((cur_unit, '\n'.join(cur_body).strip()))
        volumes.append(cur_vol)
    return volumes


def h3_titles(body):
    return [m.group(1).strip() for m in re.finditer(r'^### (.+)$', body, re.M)]


def dedup_body(title, body, pointer):
    h3s = h3_titles(body)
    toc = '\n'.join(f'- {h}' for h in h3s) if h3s else '- （无子节）'
    return (
        f'> **导读（已去重）**：本单元为《中华帝国世界观总设定 v2.0》对应编的**摘要层**；'
        f'全文与数据见本卷后文的 **{pointer}**。本处仅保留节名索引与指针，避免与全文重复。\n'
        f'> **本编节名索引**：\n{toc}\n'
        f'> **全文位置**：见本卷「{pointer}」单元。\n'
    )


def principle_note(title):
    return (
        f'> **角色**：【原则层】本单元为《中华帝国世界观总设定 v2.0》对应编的**制度原则**（总设定独有内容），'
        f'数据/名录见本卷后文的专用分卷。本单元保留全文。\n'
    )


def light_note(title):
    return (
        f'> **角色**：本单元为《中华帝国世界观总设定 v2.0》对应编（无独立分卷，本单元为唯一叙述）。\n'
    )


def build(check_only=False):
    import datetime
    text = read(SRC)
    # 跳过合订本自身的题名与前言（到第一个 --- 为止），只取十卷正文
    sep = text.find('\n---\n')
    if sep >= 0:
        text = text[sep + len('\n---\n'):]
    volumes = split_units(text)
    # 用户裁决：只保留有人物小传的官员，删去全国官员名录（第十卷）——仅从本可读本移除，其余文件不动
    volumes = [v for v in volumes if '第十卷 全国官员名录' not in (v[0] or '')]

    # build TOC
    toc_lines = []
    for h1, units in volumes:
        if h1 is None:
            continue
        h1_disp = h1[2:] if h1.startswith('# ') else h1
        toc_lines.append(f'- **{h1_disp}**')
        for title, _ in units:
            toc_lines.append(f'  - {title}')

    # transform
    out_vols = []
    dedup_done = []
    principle_done = []
    for h1, units in volumes:
        if h1 is None:
            out_vols.append((h1, units))
            continue
        new_units = []
        for title, body in units:
            base = title.strip()
            if base in DEDUP:
                new_body = dedup_body(title, body, DEDUP[base])
                new_title = title + ' 〔导读〕'
                dedup_done.append(base)
            elif base in PRINCIPLE:
                new_body = principle_note(title) + '\n' + body
                new_title = title + ' 〔原则层〕'
                principle_done.append(base)
            else:
                new_body = body
                new_title = title
            new_units.append((new_title, new_body))
        out_vols.append((h1, new_units))

    # assemble
    sections = []
    front_text = FRONT.format(
        date=__import__('datetime').date.today().isoformat(),
        toc='\n'.join(toc_lines),
    )
    sections.append(front_text.rstrip())
    for h1, units in out_vols:
        if h1 is None:
            for title, body in units:
                sections.append(f'## {title}\n\n{body}'.strip())
            continue
        body = '\n\n'.join(f'## {title}\n\n{body}'.strip() for title, body in units)
        sections.append(f'{h1}\n\n{body}'.strip())

    checklist = CHECKLIST.format(
        dedup_list='、'.join(dedup_done) if dedup_done else '无',
        principle_list='、'.join(principle_done) if principle_done else '无',
    )
    out = '\n\n---\n\n'.join(sections) + '\n' + checklist + '\n'

    if check_only:
        print(f'[校验] 卷数 {len(out_vols)} / 去重单元 {len(dedup_done)} / 原则层 {len(principle_done)}')
        print('去重:', dedup_done)
        print('原则层:', principle_done)
        return

    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(out)
    print(f'[生成] {OUT}')
    print(f'       {len(out.split(chr(10)))} 行 / {len(out.encode("utf-8"))/1024:.0f} KB')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--pdf', metavar='OUT.pdf', help='同时生成 PDF（需 pandoc + typst 在 PATH）')
    args = ap.parse_args()
    build(check_only=args.check)
    if args.pdf and not args.check:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from build_setting_book import build_pdf, TYPST_SETTING_INJECT
        build_pdf(OUT, os.path.abspath(args.pdf), TYPST_SETTING_INJECT)


if __name__ == '__main__':
    main()
