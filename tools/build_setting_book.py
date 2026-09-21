#!/usr/bin/env python3
"""《中华帝国设定集·全卷合订本》整编与发布脚本

用法（在仓库任意位置执行均可）：
    python tools/build_setting_book.py                     # 仅汇编 Markdown 合订本
    python tools/build_setting_book.py --pdf 输出.pdf       # 汇编 + 生成 PDF（需 pandoc + typst）

汇编范围（全部设定文档，不含小说《华北风暴》正文）：
    世界观总设定 v2.0 → 编年史 → 世界近代史推演 → 长安城市志 → 官员名录（总索引 + 卷一…卷四十二）

PDF 管线：pandoc(gfm→typst) → 注入字体/版式（正文宋体 SimSun，标题方正小标宋 FZXiaoBiaoSong-B05S）
          → typst compile。中间文件写入系统临时目录。
"""
import argparse
import glob
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTING = os.path.join(ROOT, '设定')
OUT_MD = os.path.join(SETTING, '中华帝国设定集·全卷合订本(2026).md')

CORE_DOCS = [
    '中华帝国世界观总设定v2.0.md',
    '中华帝国编年史1700-2026.md',
    '世界近代史推演.md',
    '长安城市志.md',
    '全国高等教育设定(2026).md',
]
ORDER_CN = [
    '一', '二', '三', '四', '五', '六', '七', '八', '九', '十',
    '十一', '十二', '十三', '十四', '十五', '十六', '十七', '十八', '十九',
    '二十', '二十一', '二十二', '二十三', '二十四', '二十五',
    '二十六', '二十七', '二十八', '二十九', '三十', '三十一', '三十二',
    '三十三', '三十四', '三十五', '三十六', '三十七', '三十八', '三十九',
    '四十', '四十一', '四十二',
]

HEADER = '''# 《中华帝国设定集·全卷合订本（2026）》

> **收录范围**：中华帝国（架空历史）全部世界观设定文档——《中华帝国世界观总设定 v2.0》《中华帝国编年史（约1360—2026）》《世界近代史推演（约1360—2026）》《长安城市志》《全国官员名录（42 卷＋总索引）》。
> **不含**：小说《华北风暴》正文（单独文件，不入设定集）。
> **编制日期**：2026-09-20（继文十一年）。
> **符号约定**：※＝推演创作；【推演】＝待作者定夺；【冻结】＝作者已拍板，不再改动。
> **分册版本**：各文档分册仍单独保留于本目录。

---

'''

TYPST_INJECT = '''#set document(title: "中华帝国设定集·全卷合订本（2026）", author: "Q1y1ng")
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


def read(path):
    try:
        with open(path, encoding='utf-8') as fh:
            return fh.read()
    except OSError as exc:
        raise SystemExit(f'读取失败: {path} ({exc})') from exc


def collect_parts():
    """按显式中文数字序收集汇编部分（不用 sorted —— 字典序不等于卷序）。"""
    parts = []
    for name in CORE_DOCS:
        parts.append(read(os.path.join(SETTING, name)).strip())
    idx = glob.glob(os.path.join(SETTING, '全国官员名录·总索引*.md'))
    if len(idx) != 1:
        raise SystemExit(f'总索引匹配异常: {idx}')
    parts.append(read(idx[0]).strip())
    for cn in ORDER_CN:
        hits = [p for p in glob.glob(os.path.join(SETTING, f'全国官员名录·卷{cn}·*.md'))
                if '合订本' not in p]
        if len(hits) != 1:
            raise SystemExit(f'卷{cn} 匹配异常: {hits}')
        parts.append(read(hits[0]).strip())
    return parts


def assemble():
    parts = collect_parts()
    out = HEADER + '\n\n---\n\n'.join(parts) + '\n'
    try:
        with open(OUT_MD, 'w', encoding='utf-8') as fh:
            fh.write(out)
    except OSError as exc:
        raise SystemExit(f'写入失败: {OUT_MD} ({exc})') from exc
    h1 = len(re.findall(r'(?m)^# ', out))
    lines = out.count('\n')
    print(f'[汇编] {os.path.basename(OUT_MD)}')
    print(f'       {len(parts)} 部分 / {lines} 行 / {len(out.encode("utf-8")) / 1024.0:.0f} KB / {h1} 个一级标题')
    return out


def build_pdf(pdf_path):
    tmp_typ = os.path.join(tempfile.gettempdir(), 'setting_book.tmp.typ')
    subprocess.run(['pandoc', '-f', 'gfm', OUT_MD, '-t', 'typst', '-o', tmp_typ], check=True)
    try:
        with open(tmp_typ, encoding='utf-8') as fh:
            typ = fh.read()
        with open(tmp_typ, 'w', encoding='utf-8') as fh:
            fh.write(TYPST_INJECT + typ)
    except OSError as exc:
        raise SystemExit(f'中间文件读写失败: {tmp_typ} ({exc})') from exc
    subprocess.run(['typst', 'compile', tmp_typ, pdf_path], check=True)
    size = os.path.getsize(pdf_path) / 1048576.0
    print(f'[PDF ] {pdf_path} ({size:.1f} MB)')


def main():
    ap = argparse.ArgumentParser(description='整编《中华帝国设定集·全卷合订本》')
    ap.add_argument('--pdf', metavar='OUT.pdf', help='同时生成 PDF（需 pandoc + typst 在 PATH）')
    args = ap.parse_args()
    assemble()
    if args.pdf:
        build_pdf(os.path.abspath(args.pdf))
    else:
        print('（未生成 PDF；如需：python tools/build_setting_book.py --pdf 输出.pdf）')


if __name__ == '__main__':
    sys.exit(main())
