# -*- coding: utf-8 -*-
"""名录低层卷：表格姓名列去名（表头改「姓名（略）」，单元格置 —）。"""
import io, os, re, sys


def strip(text):
    lines = text.split('\n')
    out, i, changed = [], 0, 0
    while i < len(lines):
        if not lines[i].startswith('|'):
            out.append(lines[i]); i += 1; continue
        j = i
        while j < len(lines) and lines[j].startswith('|'):
            j += 1
        block = lines[i:j]
        header = [c.strip() for c in block[0].strip('|').split('|')]
        idx = [k for k, h in enumerate(header) if h in ('姓名', '人名')]
        if idx:
            for k in idx:
                block[0] = block[0].replace('| ' + header[k] + ' |', '| 姓名（略） |', 1) if False else block[0]
            # 直接按列重建表头
            hc = block[0].strip('|').split('|')
            for k in idx:
                hc[k] = ' 姓名（略） '
            block[0] = '|' + '|'.join(hc) + '|'
            for r in range(1, len(block)):
                cells = block[r].strip('|').split('|')
                if len(cells) != len(hc):
                    continue
                for k in idx:
                    if re.match(r'^\s*-{2,}\s*$', cells[k]):
                        continue
                    if cells[k].strip():
                        cells[k] = ' — '
                        changed += 1
                block[r] = '|' + '|'.join(cells) + '|'
        out.extend(block)
        i = j
    return '\n'.join(out), changed


if __name__ == '__main__':
    total = 0
    for p in sys.argv[1:]:
        t = io.open(p, encoding='utf-8').read()
        nt, c = strip(t)
        if c:
            io.open(p, 'w', encoding='utf-8').write(nt)
            total += c
        print(f'{os.path.basename(p)}: 去名 {c}')
    print('合计', total)
