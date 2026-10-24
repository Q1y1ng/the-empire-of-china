#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《中华帝国设定集·全卷合订本》混编编译器（十卷制）＋《全国官员名录·全卷合订本》汇编器

用法（在仓库任意位置执行均可）：
    python tools/build_setting_book.py                        # 汇编两份 Markdown 合订本
    python tools/build_setting_book.py --pdf 输出.pdf         # 同时生成设定集 PDF（需 pandoc + typst）
    python tools/build_setting_book.py --roster-pdf 输出.pdf  # 同时生成名录订本 PDF

混编体例（2026-09-26 重编，取代旧的"整卷分块粘贴"式 49 部分结构）：
  * 全部设定打散到「编/卷」级单元，按主题重排为十卷；单元正文逐字保留、不改写不删减；
  * 层级规范：卷＝一级标题，单元＝二级标题，单元内标题整体降一级（跳过围栏代码块）；
  * 各单元保留原编/卷编号（如「第九编：军事体系」），与分册及文内交叉引用对照；
  * 摘要编在前作导读、专卷全文殿后展开（军事/教育/世界/首都四处），两见内容零删减；
  * 内置零遗漏断言：每个源文件的每一行（多重集合）都必须出现在成品中。

PDF 管线：pandoc(gfm→typst) → 注入字体/版式（正文宋体，标题方正小标宋，#outline 两级目录）
          → typst compile。中间文件写入系统临时目录。
"""
import argparse
import collections
import datetime
import glob
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTING = os.path.join(ROOT, '设定')
OUT_MD = os.path.join(SETTING, '中华帝国设定集·全卷合订本(2026).md')
OUT_ROSTER_MD = os.path.join(SETTING, '全国官员名录·全卷合订本(2026).md')

TS_FILE = '中华帝国世界观总设定v2.0.md'
DOC_FILES = [
    '中华帝国编年史1700-2026.md',
    '世界近代史推演.md',
    '长安城市志.md',
    '全国高等教育设定(2026).md',
    '全国军事编制设定(2026).md',
    '帝国主数据表(2026).md',
    '疆域与省界表(2026).md',
    '国民议会(2026).md',
    '法律要目(2026).md',
    '帝国高层人物小传(2026).md',
    '经济数据切片(2026).md',
    '非常设机构通则(2026).md',
]
ORDER_CN = [
    '一', '二', '三', '四', '五', '六', '七', '八', '九', '十',
    '十一', '十二', '十三', '十四', '十五', '十六', '十七', '十八', '十九',
    '二十', '二十一', '二十二', '二十三', '二十四', '二十五',
    '二十六', '二十七', '二十八', '二十九', '三十', '三十一', '三十二',
    '三十三', '三十四', '三十五', '三十六', '三十七', '三十八', '三十九',
    '四十', '四十一', '四十二',
]
TS_CLASSIFY_INDEX = '附录：设定分类索引'

# ---- 十卷制映射表（单元类型：ts＝总设定一级标题块；doc＝核心分卷整卷；idx＝名录总索引；juan＝名录卷N）----
VOLUMES = [
    ('第一卷', '总纲',
     '本卷为全书总纲：《中华帝国世界观总设定 v2.0》题头说明与第一编（世界观总览），给出这一世界的定位、读法与基本盘；其后九卷均为本卷框架的分领域展开。',
     [('ts', '《中华帝国世界观总设定 v2.0》'), ('ts', '第一编：世界观总览'), ('doc', '帝国主数据表(2026).md')]),
    ('第二卷', '历史·内史',
     '本卷为帝国内部历史。先列总设定第二编（帝国起源与建国·设定层）；继以《编年史》全文（序章、第一至七编、尾声，约1360—2026编年叙事，附历史循环总模型、五个时代一览、皇室世系年表）；殿以总设定第十七编（帝国历史年表·史表速查）。',
     [('ts', '第二编：帝国起源与建国'), ('doc', '中华帝国编年史1700-2026.md'), ('ts', '第十七编：帝国历史年表')]),
    ('第三卷', '世界·外史',
     '本卷为外部世界历史，与卷二互为表里。总设定第十八编（世界近现代历史影响）、第十九编（亚洲/欧亚国际秩序）为摘要导读；《世界近代史推演》全文（第一至七编及附一总因果链、附二分区域大事年表）为完整展开。',
     [('ts', '第十八编：世界近现代历史影响'), ('ts', '第十九编：亚洲/欧亚国际秩序'), ('doc', '世界近代史推演.md')]),
    ('第四卷', '疆域与首都',
     '本卷为疆域、区划与首都。总设定第三编（疆域与行政区划）、第十六编（长安与国家象征体系）、第二十六编（国家象征体系·推演细化）为设定层；《长安城市志》全文（卷一至卷十＋大事年表）为首都深度志书。',
     [('ts', '第三编：疆域与行政区划'), ('doc', '疆域与省界表(2026).md'), ('ts', '第十六编：长安与国家象征体系'), ('ts', '第二十六编：国家象征体系（推演细化）'), ('doc', '长安城市志.md')]),
    ('第五卷', '皇室与政制',
     '本卷为国家治理结构：皇室与皇位继承、现代政治制度、中央国家机构、地方行政制度（含官员品级与选拔）、司法监察与监督；殿以总设定附录一《帝国机构品级总表》（2026冻结版）。',
     [('ts', '第四编：皇室与皇位继承'), ('ts', '第五编：现代政治制度'), ('ts', '第六编：中央国家机构'),
      ('ts', '第七编：地方行政制度'), ('ts', '第八编：司法、监察与监督'),
      ('doc', '国民议会(2026).md'), ('doc', '法律要目(2026).md'), ('doc', '帝国高层人物小传(2026).md'),
      ('ts', '附录一：帝国机构品级总表（按一把手品级算·2026冻结版）')]),
    ('第六卷', '军事',
     '本卷为军事。总设定第九编（军事体系）为摘要导读，附录二《帝国军队层级与军衔表》（2026修订版）为冻结口径；《全国军事编制设定》全文（七编＋附录A装备核算、附录B待定清单）为三军编制完整展开。级别待遇对照（2026冻结·作者表）见第九编与军事分卷第二编。',
     [('ts', '第九编：军事体系'), ('ts', '附录二：帝国军队层级与军衔表（2026修订版·独立于文官品级）'), ('doc', '全国军事编制设定(2026).md')]),
    ('第七卷', '经济与民生',
     '本卷为经济与民生：经济体系（财政、税收、国有与私营、产业政策）、社会福利体系（保障、流动、日常生活）、社会生活与民俗（推演细化）。',
     [('ts', '第十编：经济体系'), ('doc', '经济数据切片(2026).md'), ('ts', '第十一编：社会福利体系'), ('ts', '第二十五编：社会生活与民俗（推演细化）'), ('doc', '非常设机构通则(2026).md')]),
    ('第八卷', '文教·科技·民族',
     '本卷为文教、科技与民族。总设定第十二编（教育与人才体系）为摘要导读；《全国高等教育设定》全文（七编，覆盖国立/州立/省立/专科与联盟名录）为完整展开；继以总设定第十三编（科技与AI时代）、第十四编（民族与自治制度）、第十五编（文化、身份与国家认同）。',
     [('ts', '第十二编：教育与人才体系'), ('doc', '全国高等教育设定(2026).md'), ('ts', '第十三编：科技与AI时代'),
      ('ts', '第十四编：民族与自治制度'), ('ts', '第十五编：文化、身份与国家认同')]),
    ('第九卷', '理论与推演',
     '本卷为理论与推演：政治理论（八个关键词与六大理论）、合法性理论、王朝周期律与大革命理论、典型政治事件推演（案例A—H）、仍待确定的设定（待定与已解决两清单）。※【推演】与【冻结】标注照录原文。',
     [('ts', '第二十编：帝国政治理论'), ('ts', '第二十一编：合法性理论'), ('ts', '第二十二编：王朝周期律与大革命理论'),
      ('ts', '第二十三编：典型政治事件推演'), ('ts', '第二十四编：仍待确定的设定')]),
    ('第十卷', '全国官员名录',
     '本卷为全国官员名录：总索引（42卷卷目总表、政治局常委会与八州州委主席/州长速查、冻结台账、使用指南）＋卷一至卷四十二，按中央→京畿→八州→省署→城市→基层→专题纵深顺次排列，一品至吏级全序列（约4,300+岗位，口径见总索引）。卷序与分册一致。',
     [('idx',)] + [('juan', cn) for cn in ORDER_CN]),
]

TYPST_SETTING_INJECT = '''#set document(title: "中华帝国设定集·全卷合订本（2026）", author: "Q1y1ng")
#set text(font: ("SimSun", "FZXiaoBiaoSong-B05S", "Microsoft YaHei", "Libertinus Serif"), size: 10.5pt, lang: "zh")
#set par(justify: true)
#show heading.where(level: 1): set text(font: ("FZXiaoBiaoSong-B05S", "SimSun"), size: 16pt, weight: "regular")
#show heading.where(level: 2): set text(font: ("FZXiaoBiaoSong-B05S", "SimSun"), size: 13pt, weight: "regular")
#show heading.where(level: 3): set text(font: ("FZXiaoBiaoSong-B05S", "SimSun"), size: 11.5pt, weight: "regular")
#show heading.where(level: 4): set text(font: ("FZXiaoBiaoSong-B05S", "SimSun"), size: 10.5pt, weight: "regular")
#show heading: set block(above: 1.2em, below: 0.6em)
#set page(margin: (x: 1.8cm, y: 2.0cm), numbering: "1")
#set table(stroke: 0.4pt, inset: (x: 4pt, y: 2.5pt))
#show table: set text(font: ("SimSun", "Microsoft YaHei"), size: 9pt)
#outline(title: "目 录", depth: 2)
#pagebreak()

'''

TYPST_ROSTER_INJECT = '''#set document(title: "全国官员名录·全卷合订本（2026）", author: "Q1y1ng")
#set text(font: ("SimSun", "FZXiaoBiaoSong-B05S", "Microsoft YaHei", "Libertinus Serif"), size: 10.5pt, lang: "zh")
#set par(justify: true)
#show heading.where(level: 1): set text(font: ("FZXiaoBiaoSong-B05S", "SimSun"), size: 16pt, weight: "regular")
#show heading.where(level: 2): set text(font: ("FZXiaoBiaoSong-B05S", "SimSun"), size: 13pt, weight: "regular")
#show heading.where(level: 3): set text(font: ("FZXiaoBiaoSong-B05S", "SimSun"), size: 11.5pt, weight: "regular")
#show heading: set block(above: 1.2em, below: 0.6em)
#set page(margin: (x: 1.8cm, y: 2.0cm), numbering: "1")
#set table(stroke: 0.4pt, inset: (x: 4pt, y: 2.5pt))
#show table: set text(font: ("SimSun", "Microsoft YaHei"), size: 9pt)
#outline(title: "目 录", depth: 1)
#pagebreak()

'''

HEADING_RE = re.compile(r'^(#{1,5}) ')
H1_RE = re.compile(r'^# (?!#)(.*)$')


def read(path):
    try:
        with open(path, encoding='utf-8-sig') as fh:
            return fh.read()
    except OSError as exc:
        raise SystemExit(f'读取失败: {path} ({exc})') from exc


def shift_headings(text, level=1):
    """所有 ATX 标题整体降 level 级（跳过 ``` 围栏代码块），正文逐字不动。"""
    out, in_fence = [], False
    for line in text.split('\n'):
        if line.lstrip().startswith('```'):
            in_fence = not in_fence
            out.append(line)
            continue
        if not in_fence:
            m = HEADING_RE.match(line)
            if m:
                n = min(len(m.group(1)) + level, 6)
                line = '#' * n + line[len(m.group(1)):]
        out.append(line)
    return '\n'.join(out)


def split_h1_blocks(text):
    """按一级标题切块，返回 [(标题, 块全文)]；文件首行即标题，无前置内容。"""
    blocks, cur, title, in_fence = [], [], None, False
    for line in text.split('\n'):
        if line.lstrip().startswith('```'):
            in_fence = not in_fence
            cur.append(line)
            continue
        if not in_fence and H1_RE.match(line):
            if title is not None:
                blocks.append((title, '\n'.join(cur).strip()))
            title, cur = line[2:].strip(), [line]
            continue
        cur.append(line)
    if title is not None:
        blocks.append((title, '\n'.join(cur).strip()))
    return blocks


def first_h1_title(text):
    for line in text.split('\n'):
        m = H1_RE.match(line)
        if m:
            return m.group(1).strip()
    raise SystemExit('文件缺少一级标题')


def roster_paths():
    idx = glob.glob(os.path.join(SETTING, '全国官员名录·总索引*.md'))
    if len(idx) != 1:
        raise SystemExit(f'总索引匹配异常: {idx}')
    juans = []
    for cn in ORDER_CN:
        hits = [p for p in glob.glob(os.path.join(SETTING, f'全国官员名录·卷{cn}·*.md'))
                if '合订本' not in p]
        if len(hits) != 1:
            raise SystemExit(f'卷{cn} 匹配异常: {hits}')
        juans.append(hits[0])
    return idx[0], juans


def ts_block(key):
    """按标题取总设定的一个一级标题块（标题精确匹配优先，前缀匹配兜底）。"""
    blocks = split_h1_blocks(read(os.path.join(SETTING, TS_FILE)).strip())
    exact = [(t, b) for t, b in blocks if t == key]
    if len(exact) == 1:
        return exact[0][1]
    prefix = [(t, b) for t, b in blocks if t.startswith(key)]
    if len(prefix) == 1:
        return prefix[0][1]
    raise SystemExit(f'总设定单元匹配异常: {key} -> {[t for t, _ in blocks]}')


def resolve_volumes():
    """把十卷映射解析为 [(卷号, 卷名, 导读, [(单元题, 降级后正文)])]。"""
    idx_path, juan_paths = roster_paths()
    vols = []
    for no, name, intro, specs in VOLUMES:
        items = []
        for spec in specs:
            kind = spec[0]
            if kind == 'ts':
                raw, disp = ts_block(spec[1]), spec[1] + '〔总设定〕'
            elif kind == 'doc':
                raw = read(os.path.join(SETTING, spec[1])).strip()
                disp = first_h1_title(raw)
            elif kind == 'idx':
                raw = read(idx_path).strip()
                disp = first_h1_title(raw)
            elif kind == 'juan':
                raw = read(juan_paths[ORDER_CN.index(spec[1])]).strip()
                disp = first_h1_title(raw)
            else:
                raise SystemExit(f'未知单元类型: {spec}')
            items.append((disp, shift_headings(raw, 1)))
        vols.append((no, name, intro, items))
    return vols


def norm_line(line):
    """断言用：标题行只比文本（层级已按规则位移），正文行原样比对。"""
    s = line.rstrip()
    m = re.match(r'^#{1,6} (.*)$', s)
    return m.group(1) if m else s


def check_completeness(out_text, sources):
    """零遗漏断言：每个源文件的每一非空行（多重集合）都必须出现在成品中。"""
    out_counter = collections.Counter(norm_line(l) for l in out_text.split('\n') if l.strip())
    problems = []
    for name, text in sources.items():
        need = collections.Counter(norm_line(l) for l in text.split('\n') if l.strip())
        for line, cnt in need.items():
            if out_counter[line] < cnt:
                problems.append(f'{name} 缺行: {line[:60]!r} (需{cnt}处,成品{out_counter[line]}处)')
    if problems:
        raise SystemExit('零遗漏断言失败:\n  ' + '\n  '.join(problems[:20]))


def assert_no_uncovered_source():
    """设定目录下除两个成品外的每个 .md 都必须被十卷制映射覆盖。"""
    idx_path, juan_paths = roster_paths()
    covered = {TS_FILE} | set(DOC_FILES) | {os.path.basename(idx_path)} | {
        os.path.basename(p) for p in juan_paths}
    all_md = {os.path.basename(p) for p in glob.glob(os.path.join(SETTING, '*.md'))
              if '合订本' not in os.path.basename(p)}
    missing = all_md - covered
    if missing:
        raise SystemExit(f'以下分卷未被十卷制映射覆盖（零遗漏断言）: {sorted(missing)}')


def build_setting_book():
    assert_no_uncovered_source()
    vols = resolve_volumes()
    n_units = sum(len(items) for *_, items in vols)
    classify_index = shift_headings(ts_block(TS_CLASSIFY_INDEX), 1)
    toc = ['- **卷首**：编纂说明、总目、附录：设定分类索引〔总设定〕']
    for no, name, _, items in vols:
        toc.append(f'- **{no} {name}**')
        toc.extend(f'  - {disp}' for disp, _ in items)
    date = datetime.date.today().isoformat()
    front = f'''# 《中华帝国设定集·全卷合订本（2026）》

> **体例**：本册为**混编重编本**——全部设定打散到编/卷级单元、按主题重排为十卷；单元正文逐字保留，不改写、不删减，※【推演】与【冻结】标注照录。
> **层级与编号**：卷为一级标题、单元为二级标题、单元内标题整体降一级；各单元保留原编/卷编号（如「第九编：军事体系」），以便与分册及文内交叉引用对照。总目中〔总设定〕标记表示该编出自《中华帝国世界观总设定 v2.0》。
> **层次约定**：同主题「摘要编在前作导读、专卷全文殿后展开」（军事、教育、世界、首都四处）；两见内容为设定层与全文层互备，零删减。
> **收录范围**：中华帝国（架空历史）全部世界观设定文档——《中华帝国世界观总设定 v2.0》《中华帝国编年史（约1360—2026）》《世界近代史推演（约1360—2026）》《长安城市志》《全国高等教育设定（2026）》《全国军事编制设定（2026）》《全国官员名录（总索引＋42卷）》。
> **不含**：小说《华北风暴》正文（单独成册，不入设定集；其人物与空间锚点见卷四十二及城市志卷九）。
> **编制日期**：{date}（继文十一年）。
> **符号约定**：※＝推演创作；【推演】＝待作者定夺；【冻结】＝作者已拍板，不再改动。
> **分册版本**：各文档分册仍单独保留于设定目录。

**总目**

{chr(10).join(toc)}

---

{classify_index}'''

    sections = [front]
    for no, name, intro, items in vols:
        body = '\n\n'.join(text for *_, text in items)
        sections.append(f'# {no} {name}\n\n{intro}\n\n{body}')
    out = '\n\n---\n\n'.join(sections) + '\n'

    h1 = len(re.findall(r'(?m)^# ', out))
    if h1 != 1 + len(VOLUMES):
        raise SystemExit(f'一级标题数异常: {h1}（应为 {1 + len(VOLUMES)}）')
    idx_path, juan_paths = roster_paths()
    sources = {TS_FILE: read(os.path.join(SETTING, TS_FILE))}
    for name in DOC_FILES:
        sources[name] = read(os.path.join(SETTING, name))
    for p in [idx_path] + juan_paths:
        sources[os.path.basename(p)] = read(p)
    check_completeness(out, sources)

    try:
        with open(OUT_MD, 'w', encoding='utf-8') as fh:
            fh.write(out)
    except OSError as exc:
        raise SystemExit(f'写入失败: {OUT_MD} ({exc})') from exc
    lines = out.count('\n')
    print(f'[汇编] {os.path.basename(OUT_MD)}（混编十卷制）')
    print(f'       {len(VOLUMES)} 卷 / {n_units} 单元 / {lines} 行 / '
          f'{len(out.encode("utf-8")) / 1024.0:.0f} KB / {h1} 个一级标题')
    return out


def build_roster_book():
    idx_path, juan_paths = roster_paths()
    files = [idx_path] + juan_paths
    texts = [read(p).strip() for p in files]
    toc = '\n'.join(f'- {first_h1_title(t)}' for t in texts)
    date = datetime.date.today().isoformat()
    front = f'''# 《全国官员名录·全卷合订本（2026）》

> **收录范围**：《全国官员名录》总索引＋卷一至卷四十二，一品至吏级全序列（约4,300+岗位，口径见总索引）。
> **体例**：本册为整卷粘贴式抽印本；2026-09-26 重建时修正卷序错乱，现按总索引＋卷一至卷四十二顺次排列，与分册一致。
> **编制日期**：{date}（继文十一年）。
> **符号约定**：※＝推演创作；【推演】＝待作者定夺；【冻结】＝作者已拍板，不再改动。
> **分册版本**：四十二卷分册仍单独保留于设定目录。

**总目**

{toc}'''
    sections = [front] + texts
    out = '\n\n---\n\n'.join(sections) + '\n'

    # 卷序断言：成品中 42 个卷标题必须按卷一→卷四十二顺次出现
    titles = re.findall(r'(?m)^# 《全国官员名录·卷([一二三四五六七八九十]+)：', out)
    if titles != ORDER_CN:
        raise SystemExit(f'名录卷序断言失败: {titles}')

    sources = {os.path.basename(p): t for p, t in zip(files, texts)}
    check_completeness(out, sources)

    try:
        with open(OUT_ROSTER_MD, 'w', encoding='utf-8') as fh:
            fh.write(out)
    except OSError as exc:
        raise SystemExit(f'写入失败: {OUT_ROSTER_MD} ({exc})') from exc
    h1 = len(re.findall(r'(?m)^# ', out))
    lines = out.count('\n')
    print(f'[汇编] {os.path.basename(OUT_ROSTER_MD)}（卷序修正版）')
    print(f'       {len(files)} 单元 / {lines} 行 / '
          f'{len(out.encode("utf-8")) / 1024.0:.0f} KB / {h1} 个一级标题')
    return out


def build_pdf(md_path, pdf_path, inject):
    tmp_typ = os.path.join(tempfile.gettempdir(), os.path.basename(md_path) + '.tmp.typ')
    subprocess.run(['pandoc', '-f', 'gfm', md_path, '-t', 'typst', '-o', tmp_typ], check=True)
    try:
        with open(tmp_typ, encoding='utf-8') as fh:
            typ = fh.read()
        with open(tmp_typ, 'w', encoding='utf-8') as fh:
            fh.write(inject + typ)
    except OSError as exc:
        raise SystemExit(f'中间文件读写失败: {tmp_typ} ({exc})') from exc
    subprocess.run(['typst', 'compile', tmp_typ, pdf_path], check=True)
    size = os.path.getsize(pdf_path) / 1048576.0
    print(f'[PDF ] {pdf_path} ({size:.1f} MB)')


def main():
    ap = argparse.ArgumentParser(description='整编《中华帝国设定集·全卷合订本》（混编十卷制）')
    ap.add_argument('--pdf', metavar='OUT.pdf', help='同时生成设定集 PDF（需 pandoc + typst 在 PATH）')
    ap.add_argument('--roster-pdf', metavar='OUT.pdf', help='同时生成名录订本 PDF（需 pandoc + typst 在 PATH）')
    args = ap.parse_args()
    build_setting_book()
    build_roster_book()
    if args.pdf:
        build_pdf(OUT_MD, os.path.abspath(args.pdf), TYPST_SETTING_INJECT)
    if args.roster_pdf:
        build_pdf(OUT_ROSTER_MD, os.path.abspath(args.roster_pdf), TYPST_ROSTER_INJECT)
    if not args.pdf and not args.roster_pdf:
        print('（未生成 PDF；如需：python tools/build_setting_book.py --pdf 输出.pdf）')


if __name__ == '__main__':
    sys.exit(main())
