# -*- coding: utf-8 -*-
"""把 设定/ 源文件的逐行改写同步进《中华帝国设定全书(2026).md》（位于 设定集/）。
做法：取 git diff -U0 的 -/+ 行对（要求 1:1），在全书中做字面替换。
用法：py -3 tools/sync_book_from_setting.py <源文件相对路径> [...]
"""
import io, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOK = os.path.join(ROOT, '设定集', '中华帝国设定全书(2026).md')


def pairs_for(path):
    d = subprocess.run(['git', 'diff', '-U0', '--', path],
                       capture_output=True)
    txt = d.stdout.decode('utf-8')
    hunks = re.split(r'(?m)^@@[^\n]*@@.*$', txt)[1:]
    pairs = []
    for h in hunks:
        minus = [l[1:] for l in h.split('\n') if l.startswith('-')]
        plus = [l[1:] for l in h.split('\n') if l.startswith('+')]
        if len(minus) == len(plus):
            pairs.extend(zip(minus, plus))
        else:
            print(f'  !! 非 1:1 hunk：{len(minus)} -> {len(plus)}；首个 - 行：{minus[0][:60] if minus else ""}')
    return pairs


def main(files):
    book = io.open(BOOK, encoding='utf-8').read()
    total = miss = 0
    for f in files:
        ps = pairs_for(f)
        print(f'{f}: {len(ps)} 对')
        for old, new in ps:
            total += 1
            if old and old in book:
                n = book.count(old)
                book = book.replace(old, new)
                if n > 1:
                    print(f'  · 多处命中 {n}：{old[:40]}')
            else:
                miss += 1
                print(f'  ✗ 全书未命中：{old[:70]}')
    io.open(BOOK, 'w', encoding='utf-8').write(book)
    print(f'完成：{total} 对，未命中 {miss}')


if __name__ == '__main__':
    main(sys.argv[1:])
