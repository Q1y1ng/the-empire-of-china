#!/usr/bin/env python3
"""《华北风暴》正文 PDF 生成脚本

用法（在仓库任意位置执行均可）：
    py -3 tools/build_novel_book.py                 # 默认输出到 桌面/华北风暴(2026).pdf
    py -3 tools/build_novel_book.py --pdf 输出.pdf   # 指定输出路径
    py -3 tools/build_novel_book.py --keep-tmp      # 保留中间 .typ（排查用）

管线：
    源 markdown（华北风暴·正文·扩写稿.md）
      → 规范化（抽出封面元信息；删除纯结构分隔线 `---`；压缩连续空行）
      → pandoc -f gfm -t typst
      → 注入封面 / 目录 / 字体版式（正文仿宋 FangSong，标题方正小标宋 FZXiaoBiaoSong-B05S）
      → typst compile

版式约定：
    · 正文：仿宋 12pt，首行缩进 2 字符，两端对齐，行距 1.68 倍
    · 章标题（二级）：方正小标宋 20pt，居中，另起一页
    · 部标题（一级）：方正小标宋 26pt，居中，另起一页（上一部内容页不强制补白）
    · 引用块（作者附记／引文）：仿宋 11pt，左缩进，首行不缩进
    · 封面无页码；目录无页码；正文页码从 1 起

中间文件写入系统临时目录，不污染仓库。
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, '华北风暴·正文·扩写稿.md')
AUTHOR = 'Q1y1ng'
YEAR_CN = '二〇二六年'

BODY_FONT = ('FangSong', 'SimSun', 'Microsoft YaHei')
TITLE_FONT = ('FZXiaoBiaoSong-B05S', 'SimSun')

HEAD = '''#set document(title: "{title}", author: "{author}")
// 行距说明（实测）：typst 行高 = 字体固有行高（本机仿宋 @12pt ≈ 8.0pt = 0.667em）
// + par(leading)；而段间距用的是 par(spacing) 替代 leading，所以两处必须取同一值，
// 否则段落之间的间距会比行距更紧。0.95em ⇒ 行高 ≈ 19.4pt（≈1.62 倍）。
#set text(font: {body_font}, size: 12pt, lang: "zh")
#set par(justify: true, first-line-indent: 2em, leading: 0.95em, spacing: 0.95em)
#set page(paper: "a4", margin: (x: 2.2cm, y: 2.0cm), numbering: none, number-align: center)

#let zbs = {title_font}

// —— 章标题（二级）：方正小标宋，居中，另起一页 ——
#show heading.where(level: 2): it => {{
  pagebreak(weak: true)
  v(1.2cm)
  align(center, text(font: zbs, size: 20pt, weight: "regular", it.body))
  v(1.1cm)
}}
// —— 部标题（一级）：方正小标宋加大，居中，另起一页 ——
#show heading.where(level: 1): it => {{
  pagebreak(weak: false)
  v(3.4cm)
  align(center, text(font: zbs, size: 26pt, weight: "regular", it.body))
  v(1.8cm)
}}
#show heading.where(level: 3): set text(font: zbs, size: 14pt, weight: "regular")
#show heading: set block(above: 1.1em, below: 0.6em)

// —— 场景分隔（源文件中排在章节中部的 `---`，pandoc 产出 #divider()）——
#show divider: it => {{
  v(0.5em)
  align(center, text(size: 11pt)[※　※　※])
  v(0.5em)
}}

// —— 引用块（作者附记／题记）：左缩进、首行不缩进 ——
#show quote: it => block(inset: (left: 1.8em, right: 1.2em), above: 0.5em, below: 0.5em, {{
  set text(size: 11pt)
  set par(first-line-indent: 0em, justify: true, leading: 0.95em)
  it
}})


// —— 目录：部标题加粗留白，章标题带点线页码 ——
#show outline.entry.where(level: 1): it => {{
  v(0.55em)
  strong(it)
}}

// ======================= 封面 =======================
#v(4.4cm)
#align(center, text(font: zbs, size: 36pt, weight: "regular")[{title}])
#v(1.1cm)
#align(center, text(size: 15pt)[{subtitle}])
#v(2.6cm)
#align(center, block(width: 12.5cm, {{
  set text(size: 11pt)
  set par(first-line-indent: 0em, leading: 1.0em)
  align(center)[
{meta}
  ]
}}))
#v(1.2cm)
#place(bottom + center, block({{
  set par(first-line-indent: 0em, leading: 1.2em)
  set text(size: 11pt)
  align(center)[
    {author}　著

    {year}
  ]
}}))

#pagebreak()

// ======================= 目录（无页码） =======================
// 注：目录标题用自绘文字，不用 outline(title:)——后者是 1 级 heading，
//     会被上面的部标题 show 规则接管（额外分页 + 部标题字号）。
#align(center, text(font: zbs, size: 24pt, weight: "regular")[目　录])
#v(1.4cm)
#outline(depth: 2, indent: auto, title: none)

#pagebreak()
#counter(page).update(1)
#set page(numbering: "1")

'''


def unlink_quiet(path):
    """删除临时文件；文件不存在或正被占用时不打断流程。"""
    try:
        os.remove(path)
    except OSError:
        return False
    return True


def with_utf8_stdout():
    """Windows 控制台默认 GBK，直出中文会乱码——统一切 UTF-8。"""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, 'reconfigure', None)
        if reconfigure is not None:
            reconfigure(encoding='utf-8', errors='replace')


def read(path):
    try:
        with open(path, encoding='utf-8') as fh:
            return fh.read()
    except OSError as exc:
        raise SystemExit(f'读取失败: {path} ({exc})') from exc


def write(path, text):
    try:
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(text)
    except OSError as exc:
        raise SystemExit(f'写入失败: {path} ({exc})') from exc


def esc(text):
    """转义 typst 标记模式下的特殊字符（用于注入的封面文字）。"""
    out = []
    for ch in text:
        if ch in '\\#$[]*_`<>@':
            out.append('\\' + ch)
        else:
            out.append(ch)
    return ''.join(out)


def split_source(text):
    """拆出书名、副标题行、封面元信息行与正文（跳过原 H1 与题头引用块）。"""
    lines = text.replace('\r\n', '\n').split('\n')
    title, subtitle, meta, start = None, None, [], None

    for i, line in enumerate(lines):
        if title is None:
            m = re.match(r'^# (.+)$', line)
            if m:
                title = m.group(1).strip()
            continue
        s = line.strip()
        if s == '':
            continue
        if s.startswith('>'):
            item = s.lstrip('>').strip()
            if not item:
                continue
            if subtitle is None and '：' not in item:
                subtitle = item
            else:
                meta.append(item)
            continue
        if s.startswith('## '):
            start = i
            break

    if title is None or start is None:
        raise SystemExit(f'源文件结构异常（未找到书名或首个章标题）: {SRC}')
    if subtitle is None:
        subtitle = '中华帝国官场长篇小说'
    return title, subtitle, meta, lines[start:]


def normalize(lines):
    """删标题前结构分隔线与文末收尾分隔线（PDF 中不渲染）；章节中部的
    场景分隔线保留为 `---`（pandoc 转成 #divider()，由 typst 侧样式化）。
    另压缩连续空行、去尾部空白。返回 (正文, 各类分隔线计数)。"""
    out, dropped, kept, blank = [], 0, 0, 0
    for i, line in enumerate(lines):
        if re.fullmatch(r'-{3,}\s*', line):
            j = i + 1
            while j < len(lines) and (lines[j].strip() == '' or re.fullmatch(r'-{3,}\s*', lines[j])):
                j += 1
            if j < len(lines) and not lines[j].startswith('#'):
                kept += 1  # 场景分隔：保留
            else:
                dropped += 1  # 标题前结构线／文末收尾：剔除
                continue
        if line.strip() == '':
            blank += 1
            if blank > 1:
                continue
            out.append('')
        else:
            blank = 0
            out.append(line.rstrip())
    while out and out[-1] == '':
        out.pop()
    return '\n'.join(out) + '\n', dropped, kept


def build_pdf(src_lines, src_meta, head_values, pdf_path, keep_tmp):
    tmp_md = os.path.join(tempfile.gettempdir(), 'novel_book.tmp.md')
    tmp_typ = os.path.join(tempfile.gettempdir(), 'novel_book.tmp.typ')
    write(tmp_md, src_lines)
    head = HEAD.format(**head_values)
    subprocess.run(['pandoc', '-f', 'gfm', '-t', 'typst', tmp_md, '-o', tmp_typ], check=True)
    write(tmp_typ, head + read(tmp_typ))
    subprocess.run(['typst', 'compile', tmp_typ, pdf_path], check=True)
    if not keep_tmp:
        for p in (tmp_md, tmp_typ):
            unlink_quiet(p)
    else:
        print(f'[中间] {tmp_typ}')
    return os.path.getsize(pdf_path)


def main():
    with_utf8_stdout()
    ap = argparse.ArgumentParser(description='生成《华北风暴》正文 PDF')
    ap.add_argument('--pdf', metavar='OUT.pdf',
                    default=os.path.join(os.path.expanduser('~'), 'Desktop', '华北风暴(2026).pdf'),
                    help='输出 PDF 路径（默认 桌面/华北风暴(2026).pdf）')
    ap.add_argument('--body-font', default=','.join(BODY_FONT), help='正文字体族（逗号分隔，按序回退）')
    ap.add_argument('--title-font', default=','.join(TITLE_FONT), help='标题字体族（逗号分隔，按序回退）')
    ap.add_argument('--keep-tmp', action='store_true', help='保留中间 typ（排查用）')
    args = ap.parse_args()

    raw = read(SRC)
    title, subtitle, meta, body_lines = split_source(raw)
    body, dropped_hr, kept_hr = normalize(body_lines)
    head_values = {
        'title': esc(title),
        'subtitle': esc(subtitle),
        'meta': '\n'.join('    ' + esc(m) for m in meta),
        'author': esc(AUTHOR),
        'year': YEAR_CN,
        'body_font': '(' + ', '.join(f'"{f.strip()}"' for f in args.body_font.split(',') if f.strip()) + ')',
        'title_font': '(' + ', '.join(f'"{f.strip()}"' for f in args.title_font.split(',') if f.strip()) + ')',
    }

    n_h1 = len(re.findall(r'(?m)^# ', body))
    n_h2 = len(re.findall(r'(?m)^## ', body))
    print(f'[源  ] {os.path.basename(SRC)}')
    print(f'       书名《{title}》／副题「{subtitle}」／封面元信息 {len(meta)} 行')
    print(f'       正文 {body.count(chr(10))} 行／部标题 {n_h1}／章标题 {n_h2}／'
          f'剔除结构分隔线 {dropped_hr} 条／保留场景分隔 {kept_hr} 条')

    pdf_path = os.path.abspath(args.pdf)
    out_dir = os.path.dirname(pdf_path)
    try:
        os.makedirs(out_dir, exist_ok=True)
    except OSError as exc:
        raise SystemExit(f'输出目录不可用: {out_dir} ({exc})') from exc
    size = build_pdf(body, meta, head_values, pdf_path, args.keep_tmp)
    print(f'[PDF ] {pdf_path} ({size / 1048576.0:.2f} MB)')
    print(f'       校验：py -3 tools/check_novel_pdf.py --pdf "{pdf_path}"')
    return 0


if __name__ == '__main__':
    sys.exit(main())
