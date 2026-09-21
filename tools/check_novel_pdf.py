#!/usr/bin/env python3
"""《华北风暴》PDF 验收脚本（四级校验）

直接运行即可（依赖缺失时自动用 uv 建临时环境重跑自身）：
    py -3 tools/check_novel_pdf.py
    py -3 tools/check_novel_pdf.py --pdf 其他.pdf
    # 手动跑（离线/无 uv 时）：
    uv run --no-project --index-url https://pypi.tuna.tsinghua.edu.cn/simple \\
        --with pypdf --with fonttools --with pymupdf python tools/check_novel_pdf.py

四级校验：
    A 源结构   ：章号 1..54 连续无重复；部标题/尾声/后记齐全；分隔线分类统计
    B 字体覆盖 ：正文用字全部在仿宋 cmap 内；标题用字全部在方正小标宋 cmap 内（fonttools 直接读 cmap）
    C PDF 实物 ：页数/元数据；逐页字体枚举 + 是否嵌入；章标题页与目录页码交叉核对；
                 场景分隔符与罕见字（窸/窣/镚）在文本层可检索；空白页与文件完整性
    D 版式几何 ：A4 尺寸与版心边距；正文/标题的字号与字族；首行缩进恰为 2 字符；
                 行距；标题居中；页码居中且与目录一致；封面/目录无页码（pymupdf 逐 span 坐标）

退出码：0 全部通过；1 存在失败项。
"""
import argparse
import os
import re
import subprocess
import sys

MIRROR = 'https://pypi.tuna.tsinghua.edu.cn/simple'
DEPS = ('pypdf', 'fonttools', 'pymupdf')
RELAUNCH_ENV = 'NOVEL_CHECK_RELAUNCHED'


def relaunch_with_uv():
    """依赖缺失时用 uv 建临时环境重跑本脚本（uv 自带 python，不污染全局）。"""
    if os.environ.get(RELAUNCH_ENV) or not hasattr(subprocess, 'run'):
        return None
    cmd = ['uv', 'run', '--no-project', '--index-url', MIRROR]
    for dep in DEPS:
        cmd += ['--with', dep]
    cmd += ['python', os.path.abspath(__file__), *sys.argv[1:]]
    env = dict(os.environ, **{RELAUNCH_ENV: '1'})
    try:
        return subprocess.call(cmd, env=env)
    except OSError:
        return None


try:
    import pymupdf  # type: ignore[import-not-found]
    from fontTools.ttLib import TTFont  # type: ignore[import-not-found]
    from pypdf import PdfReader  # type: ignore[import-not-found]
except ImportError as exc:  # pragma: no cover - 取决于运行环境
    code = relaunch_with_uv()
    if code is None:
        raise SystemExit(
            f'缺少依赖（{exc}），且 uv 不可用。请手动执行：\n'
            f'  uv run --no-project --index-url {MIRROR} '
            + ' '.join(f'--with {d}' for d in DEPS)
            + ' python tools/check_novel_pdf.py'
        ) from exc
    raise SystemExit(code) from exc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, '华北风暴·正文·扩写稿.md')
DEFAULT_PDF = os.path.join(os.path.expanduser('~'), 'Desktop', '华北风暴(2026).pdf')
BODY_FONT = r'C:\Windows\Fonts\simfang.ttf'
TITLE_FONT = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'Fonts', '方正小标宋简.TTF')
RARE_CHARS = '窸窣镚'
CN_NUM = {c: i for i, c in enumerate('零一二三四五六七八九')}

# 版式基准（与 tools/build_novel_book.py 的注入参数一致）
BODY_PT = 12.0          # 正文字号
BODY_LEADING = 0.95     # typst par(leading:) 附加值
INDENT_PT = 24.0        # 首行缩进 2em = 2 × 12pt
# typst 行高 = 字体固有行高 + leading；本机仿宋 @12pt 固有行高实测 ≈ 8.0pt（0.667em），
# 故 0.95em 的行距 ≈ 8.0 + 11.4 = 19.4pt（≈1.62 倍）。段间距用同一值，保持全篇一致。
BODY_PITCH_PT = 19.4
MARGIN_X_PT = 2.2 * 72 / 2.54
MARGIN_Y_PT = 2.0 * 72 / 2.54
HEAD_PT = {'chapter': 20.0, 'part': 26.0, 'toc': 24.0}

RESULTS = []


def with_utf8_stdout():
    """Windows 控制台默认 GBK，直出中文与符号会乱码或报错——统一切 UTF-8。"""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, 'reconfigure', None)
        if reconfigure is not None:
            reconfigure(encoding='utf-8', errors='replace')


def record(section, name, ok, detail=''):
    RESULTS.append((section, name, ok, detail))
    print(f'  [{"OK " if ok else "FAIL"}] {name}' + (f' —— {detail}' if detail else ''))


def cn2int(text):
    """中文数字（一/十/二十一/五十四…）转整数，失败返回 None。"""
    val, tmp = 0, 0
    for ch in text:
        if ch == '十':
            tmp = (tmp or 1) * 10
            val += tmp
            tmp = 0
        elif ch == '百':
            tmp = (tmp or 1) * 100
            val += tmp
            tmp = 0
        elif ch in CN_NUM:
            tmp = CN_NUM[ch]
        else:
            return None
    return val + tmp


def read_source():
    try:
        with open(SRC, encoding='utf-8') as fh:
            return fh.read()
    except OSError as exc:
        raise SystemExit(f'读取源文件失败: {SRC} ({exc})') from exc


def read_bytes(path):
    """读文件字节；路径不可读时终止并给出可读提示。"""
    try:
        with open(path, 'rb') as fh:
            return fh.read()
    except OSError as exc:
        raise SystemExit(f'读取失败: {path} ({exc})') from exc


def norm(text):
    """去掉所有空白——PDF 文本层会在中西文之间插空格，比对前需归一。"""
    return re.sub(r'\s+', '', text)


def cmap_of(path):
    font = TTFont(path, fontNumber=0, lazy=True)
    codes = set()
    for table in font['cmap'].tables:
        codes |= set(table.cmap.keys())
    font.close()
    return codes


# ---------------------------------------------------------------- A. 源结构

def check_source(text):
    print('\nA. 源结构')
    heads = re.findall(r'(?m)^(#{1,2}) (.+)$', text)
    h1 = [t for lvl, t in heads if lvl == '#']
    h2 = [t for lvl, t in heads if lvl == '##']
    nums = []
    for title in h2:
        m = re.match(r'第([一二三四五六七八九十百]+)章', title)
        if m:
            value = cn2int(m.group(1))
            if value is not None:
                nums.append(value)
    record('A', '章标题连续', nums == list(range(1, len(nums) + 1)),
           f'{len(nums)} 章，编号 {min(nums)}–{max(nums)}')
    record('A', '章标题无重复', len(set(h2)) == len(h2), f'去重后 {len(set(h2))} 条')
    extra = [t for t in h2 if not re.match(r'第[一二三四五六七八九十百]+章', t)]
    record('A', '章外条目（尾声/后记）', extra == ['尾声 盆还在', '尾声 盆还在·续', '全书后记'], '、'.join(extra))
    record('A', '部标题', len(h1) == 3, '、'.join(h1))

    lines = text.split('\n')
    hr = struct = scene = tail = 0
    for i, line in enumerate(lines):
        if not re.fullmatch(r'-{3,}\s*', line):
            continue
        hr += 1
        j = i + 1
        while j < len(lines) and (lines[j].strip() == '' or re.fullmatch(r'-{3,}\s*', lines[j])):
            j += 1
        if j >= len(lines):
            tail += 1
        elif lines[j].startswith('#'):
            struct += 1
        else:
            scene += 1
    record('A', '结构分隔线（标题前/文末）不入正文', struct + tail == hr - scene and scene == 2,
           f'共 {hr} 条 = 标题前 {struct} + 场景分隔 {scene} + 文末 {tail}')
    record('A', '场景分隔线落在章节内部', scene == 2,
           '2 处（渲染为 ※　※　※，不丢失）')
    return h2, extra


# ---------------------------------------------------------------- B. 字体覆盖

def check_font_coverage(text, h2):
    print('\nB. 字体覆盖（fonttools 读 cmap）')
    body_chars = {c for c in text if c not in '\n\r\t'}
    head_text = ''.join(h2) + ''.join(re.findall(r'(?m)^# (.+)$', text))
    body_cmap, title_cmap = cmap_of(BODY_FONT), cmap_of(TITLE_FONT)
    miss_body = sorted(c for c in body_chars if ord(c) not in body_cmap)
    miss_head = sorted(c for c in set(head_text) if ord(c) not in title_cmap)
    record('B', f'正文用字全部在仿宋字库内（{os.path.basename(BODY_FONT)}）', not miss_body,
           f'{len(body_chars)} 个不同字符，缺 {len(miss_body)}' + (f'：{"".join(miss_body)}' if miss_body else ''))
    record('B', f'标题用字全部在方正小标宋字库内（{os.path.basename(TITLE_FONT)}）', not miss_head,
           f'{len(set(head_text))} 个不同字符，缺 {len(miss_head)}' + (f'：{"".join(miss_head)}' if miss_head else ''))
    return miss_head


# ---------------------------------------------------------------- C. PDF 实物

def page_fonts(page):
    """返回该页 (字体名, 是否嵌入) 列表。"""
    out = []
    res = page.get('/Resources')
    fonts = res.get('/Font') if res else None
    if not fonts:
        return out
    for key in fonts:
        font = fonts[key].get_object()
        name = str(font.get('/BaseFont', key))
        desc = font.get('/FontDescriptor')
        if desc is None and '/DescendantFonts' in font:
            desc = font['/DescendantFonts'][0].get_object().get('/FontDescriptor')
        embedded = False
        if desc is not None:
            d = desc.get_object()
            embedded = any(k in d for k in ('/FontFile', '/FontFile2', '/FontFile3'))
        out.append((name, embedded))
    return out


def footer_number(text):
    tail = [line.strip() for line in text.strip().split('\n') if line.strip()]
    return tail[-1] if tail and re.fullmatch(r'\d+', tail[-1]) else None


def check_pdf(pdf_path, h2, miss_head):
    print(f'\nC. PDF 实物（{pdf_path}）')
    if not os.path.exists(pdf_path):
        raise SystemExit(f'PDF 不存在: {pdf_path}')
    raw = read_bytes(pdf_path)
    record('C', 'PDF 文件完整（%%EOF 结尾）', raw.rstrip().endswith(b'%%EOF'), f'{len(raw) / 1048576.0:.2f} MB')

    reader = PdfReader(pdf_path)
    pages = [p.extract_text() or '' for p in reader.pages]
    meta = reader.metadata or {}
    record('C', '元数据 title/author', str(meta.get('/Title')) == '华北风暴' and str(meta.get('/Author')) == 'Q1y1ng',
           f'《{meta.get("/Title")}》／{meta.get("/Author")}')

    font_pages, embedded_fail, n_embedded = {}, [], 0
    for page in reader.pages:
        for name, embedded in page_fonts(page):
            font_pages[name] = font_pages.get(name, 0) + 1
            if embedded:
                n_embedded += 1
            else:
                embedded_fail.append(name)
    record('C', '全部字体已嵌入', not embedded_fail, '、'.join(f'{k}×{v}页' for k, v in sorted(font_pages.items())))
    has_body = any(('FangSong' in k) or ('SimFan' in k) or ('仿宋' in k) for k in font_pages)
    has_title = any(('XiaoBiaoSong' in k) or ('FZXBS' in k) or ('小标宋' in k) for k in font_pages)
    record('C', '正文仿宋 + 标题方正小标宋两种字体齐备', has_body and has_title, f'嵌入引用 {n_embedded} 处')

    blank = [i + 1 for i, t in enumerate(pages) if not t.strip()]
    record('C', '无空白页', not blank, f'空白页：{blank}' if blank else f'共 {len(pages)} 页')

    n_pages = [norm(t) for t in pages]
    toc_idx = next((i for i, t in enumerate(n_pages) if '目录' in t), None)
    body_start = None
    if toc_idx is not None:
        for i in range(toc_idx, len(pages)):
            if norm(h2[0]) in n_pages[i] and footer_number(pages[i]):
                body_start = i
                break
    if body_start is None:
        record('C', '正文起始页（章节首页）可定位', False, '未定位到正文首页，后续页码核对跳过')
    else:
        record('C', '正文起始页（章节首页）可定位', True,
               f'PDF 第 {body_start + 1} 页 = 正文第 {footer_number(pages[body_start])} 页')

    missing, page_pairs = [], []
    for title in h2:
        hit = None
        for i, text in enumerate(n_pages):
            if body_start is not None and i < body_start:
                continue
            if norm(title) in text:
                hit = i
                break
        if hit is None:
            missing.append(title)
        else:
            page_pairs.append((title, footer_number(pages[hit]), hit))
    record('C', '全部章标题在 PDF 文本层可检索', not missing, f'{len(page_pairs)}/{len(h2)} 条命中'
           + (f'；缺：{missing}' if missing else ''))
    distinct = len({i for _, _, i in page_pairs})
    record('C', '每章独立起页（无两章同页）', distinct == len(page_pairs),
           f'{distinct} 个不同首页 / {len(page_pairs)} 章')
    toc_pages = n_pages[toc_idx:toc_idx + 4] if toc_idx is not None else []
    in_toc = [t for t in h2 if any(norm(t) in p for p in toc_pages)]
    record('C', '目录含全部章标题', len(in_toc) == len(h2),
           f'{len(in_toc)}/{len(h2)} 条在目录页（PDF 第 {(toc_idx or 0) + 1} 页起）')

    page_of = {norm(t): n for t, n, _ in page_pairs}
    entries, cursor = [], 0
    toc_norm = ''.join(toc_pages)
    for title in h2:
        key = norm(title)
        idx = toc_norm.find(key, cursor)
        if idx < 0:
            continue
        j = idx + len(key)
        while j < len(toc_norm) and toc_norm[j] in '.·‧．…':
            j += 1
        m = re.match(r'\d+', toc_norm[j:])
        if m:
            entries.append((title, m.group(0)))
            cursor = j + m.end()
    mism = [(t, n, page_of.get(norm(t))) for t, n in entries if page_of.get(norm(t)) != n]
    record('C', '目录页码与实际页脚一致', len(entries) == len(h2) and not mism,
           f'解析目录条目 {len(entries)}/{len(h2)} 条，错位 {len(mism)}' + (f'：{mism[:3]}' if mism else ''))

    scene_marks = sum(n.count('※※※') for n in n_pages)
    record('C', '场景分隔符 ※※※ 渲染 2 处', scene_marks == 2, f'文本层命中 {scene_marks} 处'
           + ('（源文本无 ※ 字符，命中即渲染产物）' if scene_marks == 2 else ''))

    rare_ok = all(c in ''.join(pages) for c in RARE_CHARS)
    record('C', '罕见字未丢失（窸/窣/镚）', rare_ok and not miss_head,
           '、'.join(f'{c}×{sum(p.count(c) for p in pages)}' for c in RARE_CHARS))

    # 引号归一：PDF 文本层不应再出现半角直引号
    all_text = ''.join(pages)
    straight = all_text.count('"') + all_text.count("'")
    curly = all_text.count('“') + all_text.count('”')
    record('C', '半角引号已全部转为中文引号', straight == 0 and curly >= 2600,
           f'直引号 {straight} 个／中文引号 {curly} 个')

    first, last = pages[body_start] if body_start is not None else '', pages[-1]
    record('C', '首页正文抽样', '中发' in first or '第一章' in first, first.replace('\n', ' ')[:60])
    record('C', '尾页正文抽样', '制度' in last or '盆' in last, last.replace('\n', ' ')[-60:])
    print(f'  页数：{len(pages)}；目录 PDF 第 {(toc_idx or 0) + 1} 页；正文 '
          f'{footer_number(pages[body_start]) if body_start is not None else "?"}–'
          f'{footer_number(pages[-1]) or "?"} 页')
    return pages, body_start or 0


# ---------------------------------------------------------------- D. 版式几何

def pymupdf_lines(page):
    """按行汇总 pymupdf 的 span 坐标（升序 y）。"""
    out = []
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines', []):
            spans = [s for s in line['spans'] if s['text'].strip()]
            if not spans:
                continue
            out.append({
                'x0': min(s['bbox'][0] for s in spans),
                'x1': max(s['bbox'][2] for s in spans),
                'y0': min(s['bbox'][1] for s in spans),
                'y1': max(s['bbox'][3] for s in spans),
                'text': ''.join(s['text'] for s in spans),
                'size': round(spans[0]['size'], 2),
                'font': spans[0]['font'],
            })
    return sorted(out, key=lambda row: row['y0'])


def baseline_rows(page, size, tol=0.05):
    """按基线聚簇还原「视觉行」。

    pymupdf 的 line 分组在中文排版下会把同一行拆开或跨行合并，基线（origin y）
    聚簇才可靠——行距、缩进、居中都以它为准。
    """
    pts = []
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines', []):
            for span in line['spans']:
                if span['text'].strip() and abs(span['size'] - size) < tol:
                    pts.append((round(span['origin'][1], 2), span['bbox'][0], span['bbox'][2]))
    pts.sort(key=lambda item: item[0])
    rows, cur = [], []
    for item in pts:
        if cur and item[0] - cur[-1][0] > 1.0:
            rows.append(cur)
            cur = []
        cur.append(item)
    if cur:
        rows.append(cur)
    return [{'baseline': max(item[0] for item in r), 'x0': min(item[1] for item in r),
             'x1': max(item[2] for item in r)} for r in rows]


def check_layout(pdf_path, pages_text, body_start):
    print('\nD. 版式几何（pymupdf 逐 span 坐标）')
    doc = pymupdf.open(pdf_path)
    page_w, page_h = doc[0].rect.width, doc[0].rect.height
    record('D', '页面 A4 尺寸', abs(page_w - 595.28) < 1.0 and abs(page_h - 841.89) < 1.0,
           f'{page_w:.1f}×{page_h:.1f}pt')

    body_lines = pymupdf_lines(doc[body_start])

    # 版心与边距（含标点悬挂；缩进/行距都以此页的视觉行为准）
    body_rows = baseline_rows(doc[body_start], BODY_PT)
    # 页脚页码在版心之外，算版心高时排除
    body_bottom = max(row['y1'] for row in body_lines if row['y0'] < page_h - MARGIN_Y_PT)
    left = min(row['x0'] for row in body_rows)
    right_lim = max(row['x1'] for row in body_rows)
    hang = max(0.0, right_lim - (page_w - MARGIN_X_PT))
    record('D', '版心边距（左右 2.2cm / 上下 2.0cm）',
           abs(left - MARGIN_X_PT) < 2.0 and hang <= BODY_PT * 0.55
           and min(row['y0'] for row in body_lines) >= MARGIN_Y_PT - 1
           and body_bottom <= page_h - MARGIN_Y_PT + 1,
           f'左 {left:.1f}pt／右留白 {page_w - right_lim:.1f}pt（基准 {MARGIN_X_PT:.1f}；'
           f'标点悬挂 {hang:.1f}pt）／正文底 {body_bottom:.1f}pt（上限 {page_h - MARGIN_Y_PT:.1f}）')

    # 正文字族/字号
    body_spans = [row for row in body_lines if abs(row['size'] - BODY_PT) < 0.05]
    body_txt = ''.join(row['text'] for row in body_spans)
    record('D', f'正文字号 {BODY_PT:.0f}pt', len(body_txt) > 300, f'{len(body_spans)} 行 / {len(body_txt)} 字')
    record('D', '正文字族为仿宋', all('FangSong' in row['font'] or 'SimFan' in row['font'] for row in body_spans),
           f'字族 {sorted({row["font"] for row in body_spans})}')

    # 标题：字号 + 方正小标宋 + 居中（中文标点参与对齐，容差取 0.35em）
    def centered(rows, size, name):
        if not rows:
            return record('D', name, False, '未找到该字号标题')
        off = abs((rows[0]['x0'] + rows[0]['x1']) / 2 - page_w / 2)
        return record('D', name, off < size * 0.35 and
                      all(('XiaoBiaoSong' in row['font']) or ('FZXBS' in row['font']) for row in rows),
                      f'{len(rows)} 处；{rows[0]["font"]}；居中偏差 {off:.1f}pt；{rows[0]["text"][:16]}')

    chap = [row for row in body_lines if abs(row['size'] - HEAD_PT['chapter']) < 0.05]
    centered(chap, HEAD_PT['chapter'], f'章标题 {HEAD_PT["chapter"]:.0f}pt + 方正小标宋 + 居中')

    part_page = next((i for i, t in enumerate(pages_text) if '第二部' in norm(t) and i > body_start), None)
    part = [row for row in (pymupdf_lines(doc[part_page]) if part_page is not None else [])
            if abs(row['size'] - HEAD_PT['part']) < 0.05]
    centered(part, HEAD_PT['part'], f'部标题 {HEAD_PT["part"]:.0f}pt + 方正小标宋 + 居中'
             + (f'（第 {part_page + 1} 页）' if part_page is not None else ''))
    centered([row for row in pymupdf_lines(doc[1]) if abs(row['size'] - HEAD_PT['toc']) < 0.05],
             HEAD_PT['toc'], f'目录标题 {HEAD_PT["toc"]:.0f}pt + 方正小标宋 + 居中')

    # 首行缩进：行首 x 应聚成两簇——版心左界 与 左界 + 2em
    starts = sorted({round(row['x0'], 1) for row in body_rows})
    margin = starts[0]
    indented = [x for x in starts if abs(x - margin - INDENT_PT) < 1.5]
    flush = [x for x in starts if abs(x - margin) < 1.5]
    record('D', f'首行缩进恰为 2 字符（{INDENT_PT:.0f}pt）', bool(indented) and bool(flush),
           f'缩进行首 x={indented[0] if indented else "-"}pt／不缩进 x={margin}pt（差 '
           f'{indented[0] - margin if indented else "-"}pt）')

    # 行距：视觉行基线差（缩进相同的算行内，缩进切换的算段间）
    inside, between = [], []
    for i in range(len(body_rows) - 1):
        step = round(body_rows[i + 1]['baseline'] - body_rows[i]['baseline'], 2)
        if abs(body_rows[i + 1]['x0'] - body_rows[i]['x0']) > 0.6:
            between.append(step)
        else:
            inside.append(step)
    med_in = sorted(inside)[len(inside) // 2] if inside else 0.0
    med_bt = sorted(between)[len(between) // 2] if between else 0.0
    record('D', f'行距 ≈ {BODY_PITCH_PT}pt（{BODY_PITCH_PT / BODY_PT:.2f} 倍）',
           bool(inside) and abs(med_in - BODY_PITCH_PT) <= 1.0, f'实测中位 {med_in:.2f}pt（{len(inside)} 处）')
    record('D', '段间距与行距一致（无额外段距）',
           bool(between) and abs(med_bt - med_in) <= 0.6, f'段间中位 {med_bt:.2f}pt vs 行内 {med_in:.2f}pt')

    # 页码：正文页脚居中且与目录编号一致；封面与目录页无页码
    def bottom_line(idx):
        lines = pymupdf_lines(doc[idx])
        return [row for row in lines if row['y0'] > page_h - MARGIN_Y_PT]

    foot = bottom_line(body_start)
    foot_centered = bool(foot) and abs((foot[0]['x0'] + foot[0]['x1']) / 2 - page_w / 2) < 3.0
    record('D', '正文页码居中于页脚', foot_centered,
           f'{foot[0]["text"] if foot else "-"}（x 中心 {((foot[0]["x0"] + foot[0]["x1"]) / 2):.1f}pt）' if foot else '')
    record('D', '封面与目录不编页码', not bottom_line(0) and not bottom_line(1),
           f'封面页脚 {len(bottom_line(0))} 行／目录页脚 {len(bottom_line(1))} 行')
    doc.close()


def main():
    with_utf8_stdout()
    ap = argparse.ArgumentParser(description='《华北风暴》PDF 验收')
    ap.add_argument('--pdf', default=DEFAULT_PDF, help='待校验 PDF（默认 桌面/华北风暴(2026).pdf）')
    args = ap.parse_args()

    text = read_source()
    print(f'源文件：{SRC}')
    h2, extra = check_source(text)
    miss_head = check_font_coverage(text, h2)
    pdf_path = os.path.abspath(args.pdf)
    pages, body_start = check_pdf(pdf_path, h2, miss_head)
    check_layout(pdf_path, pages, body_start)

    bad = [(s, n, d) for s, n, ok, d in RESULTS if not ok]
    print(f'\n结论：{len(RESULTS) - len(bad)}/{len(RESULTS)} 项通过' + ('' if not bad else f'，失败 {len(bad)}：{bad}'))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
