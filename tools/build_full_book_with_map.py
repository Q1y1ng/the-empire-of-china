# -*- coding: utf-8 -*-
"""《中华帝国设定全书（2026）》含八州政区图版 PDF 生成器。

用法：
    py -3 tools/build_full_book_with_map.py              # 输出 桌面/中华帝国设定全书(2026)·含八州政区图.pdf
    py -3 tools/build_full_book_with_map.py --pdf 输出.pdf
    py -3 tools/build_full_book_with_map.py --no-map     # 不插图（对照用）

管线与 tools/build_setting_book.py 的 build_pdf 相同（pandoc gfm→typst → typst compile），
差别只有两处：①运行页眉由「设定集·全卷合订本」改为「设定全书」；
②在「第四卷 疆域与首都」卷首插入 docs/assets 的八州政区图与图注。
运行前先跑 `py -3 tools/build_readable_book.py` 生成 设定集/中华帝国设定全书(2026).md。
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, '设定集', '中华帝国设定全书(2026).md')
MAP_SRC = os.path.join(ROOT, 'docs', 'assets', '中华帝国全图(2026)·八州政区图.png')
DEFAULT_OUT = os.path.join(os.path.expanduser('~'), 'Desktop', '中华帝国设定全书(2026)·含八州政区图.pdf')

sys.path.insert(0, os.path.join(ROOT, 'tools'))
from build_setting_book import TYPST_SETTING_INJECT, fix_divider, fix_escaped_bold, fix_figure

CAPTION = (
    '中华帝国全图（2026）·八州政区图。2026 年建制裁并后全国省级行政单位为四十五个（四十三省、二市）：'
    '京畿直隶州辖陕西省（延安）、成都省（成都，含汉中市）、重庆省（重庆）、中原省（洛阳）与长安市；'
    '江南州辖江苏、浙江、安徽、江西、福建、台湾、岭南七省与上海市。'
    '★为首都长安，八州府为北京、沈阳、呼和浩特、乌鲁木齐、上海、南宁、拉萨。'
    '省界仅作示意，文字基准见《疆域与省界表（2026）》。'
)


def main():
    ap = argparse.ArgumentParser(description='生成含八州政区图的《中华帝国设定全书》PDF')
    ap.add_argument('--pdf', metavar='OUT.pdf', default=DEFAULT_OUT, help='输出路径（默认桌面）')
    ap.add_argument('--no-map', action='store_true', help='不插图，用于对照页数')
    args = ap.parse_args()

    if not os.path.exists(SRC):
        raise SystemExit(f'缺少底本：{SRC}（先跑 tools/build_readable_book.py）')

    inject = (TYPST_SETTING_INJECT
              .replace('中华帝国设定集·全卷合订本（2026）', '中华帝国设定全书（2026）')
              .replace('中华帝国设定集 · 全卷合订本（2026）', '中华帝国设定全书（2026）'))

    tmp_dir = tempfile.gettempdir()
    tmp_typ = os.path.join(tmp_dir, 'quanshu_map.tmp.typ')
    subprocess.run(['pandoc', '-f', 'gfm', '--wrap=none', SRC, '-t', 'typst', '-o', tmp_typ], check=True)
    typ = open(tmp_typ, encoding='utf-8').read()
    typ = fix_figure(fix_divider(fix_escaped_bold(typ)))

    if not args.no_map:
        if not os.path.exists(MAP_SRC):
            raise SystemExit(f'缺少地图：{MAP_SRC}')
        shutil.copyfile(MAP_SRC, os.path.join(tmp_dir, 'map.png'))  # typst 按 typ 文件所在目录解析相对路径
        fig = (f'#figure(\n  image("map.png", width: 100%),\n  caption: [{CAPTION}],\n)\n')
        pat = re.compile(r'^= 第四卷 疆域与首都\s*$', re.M)
        if not pat.search(typ):
            raise SystemExit('未找到「第四卷 疆域与首都」标题，图未插入')
        typ = pat.sub('= 第四卷 疆域与首都\n' + fig, typ, count=1)

    open(tmp_typ, 'w', encoding='utf-8').write(inject + typ)
    out = os.path.abspath(args.pdf)
    subprocess.run(['typst', 'compile', tmp_typ, out], check=True)
    raw = open(out, 'rb').read()
    pages = max(int(n) for n in re.findall(rb'/Count\s+(\d+)', raw))
    print(f'[PDF] {out} ({len(raw)/1048576:.1f} MB, {pages} 页)')


if __name__ == '__main__':
    sys.exit(main())
