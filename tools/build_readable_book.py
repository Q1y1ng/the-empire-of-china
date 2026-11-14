#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《中华帝国设定全书（2026）》可读本生成器。

把《中华帝国设定集·全卷合订本》转为**可手改的活文档**：
  * 去掉「勿手改」锁，明确可编辑；
  * 为每个「总设定」单元加「导读」角色标签（原则层 vs 数据层）；
  * 对有独立分卷的摘要单元，用 H3 小目录 + 指针替代冗余正文（去重）；
  * 末尾附「覆盖清单」与「同步约定」。

用法：
    py -3 tools/build_readable_book.py            # 生成 设定集/中华帝国设定全书(2026).md
    py -3 tools/build_readable_book.py --check    # 只报告，不写文件
"""
import argparse
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOK = os.path.join(ROOT, '设定集')
SRC = os.path.join(BOOK, '中华帝国设定集·全卷合订本(2026).md')
OUT = os.path.join(BOOK, '中华帝国设定全书(2026).md')

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

> **符号约定**：※＝推演创作；【推演】＝可调整的推演项（非冻结）；【待定】＝尚未裁决；【冻结】＝作者已拍板，不再改动。

'''

CHECKLIST = ''


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
        f'> **本编为摘要，全文见本卷后文《{pointer}》。**\n'
        f'>\n{toc}\n'
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
                new_title = title
                dedup_done.append(base)
            elif base in PRINCIPLE:
                new_body = body
                new_title = title
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
    out = '\n\n---\n\n'.join(sections) + '\n'

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
