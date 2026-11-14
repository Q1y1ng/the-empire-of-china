#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一次性迁移：把《中华帝国世界观总设定 v2.0》按一级标题拆成单章（2026-11-14）。

拆出 30 个文件到 设定/：
    总设定·00·题头说明.md
    总设定·第X编·<编名>.md          ×26
    总设定·附录一·机构品级总表.md
    总设定·附录二·军队层级与军衔表.md
    总设定·附录·设定分类索引.md

约束（见《设定拆分与目录分离·可行性调研》§七）：
  * 标题逐字保留，否则 build_setting_book.ts_block() 匹配不到 → SystemExit；
  * 文件名避免 `·卷N·` 与全角括号，免得撞 roster glob 或路径坑；
  * 只搬家、不改写：拆完拼装结果须与原合订本逐字节一致。

用法：py -3 tools/archive/split_zongshe_once.py [--apply]
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SET = os.path.join(ROOT, '设定')
TS = os.path.join(SET, '中华帝国世界观总设定v2.0.md')


def target_name(title):
    m = re.match(r'^第(.+?)编[：:](.+)$', title)
    if m:
        safe = re.sub(r'[\\/:*?"<>|（）()·]', '', m.group(2))
        return f'总设定·第{m.group(1)}编·{safe}.md'
    if title.startswith('附录一'):
        return '总设定·附录一·机构品级总表.md'
    if title.startswith('附录二'):
        return '总设定·附录二·军队层级与军衔表.md'
    if title.startswith('附录'):
        return '总设定·附录·设定分类索引.md'
    return '总设定·00·题头说明.md'


def main():
    apply = '--apply' in sys.argv
    if not os.path.exists(TS):
        raise SystemExit('源文件不存在，可能已拆分过：%s' % TS)
    text = io.open(TS, encoding='utf-8').read()
    lines = text.split('\n')
    starts = [i for i, l in enumerate(lines) if re.match(r'^# ', l)]
    out = []
    for k, i in enumerate(starts):
        end = starts[k + 1] if k + 1 < len(starts) else len(lines)
        body = '\n'.join(lines[i:end]).strip() + '\n'
        title = lines[i][2:].strip()
        out.append((target_name(title), title, body))

    names = [n for n, _, _ in out]
    if len(set(names)) != len(names):
        raise SystemExit('目标文件名重复：%s' % names)
    print('将拆出 %d 个单章文件：' % len(out))
    for n, t, b in out:
        print('  %-40s %5d 行  ← %s' % (n, b.count('\n'), t))

    if not apply:
        print('\n干跑通过（未落盘）。加 --apply 执行。')
        return 0

    for n, _, b in out:
        with io.open(os.path.join(SET, n), 'w', encoding='utf-8', newline='') as fh:
            fh.write(b)
    os.remove(TS)
    print('\n已写入 %d 个文件，并删除原《中华帝国世界观总设定v2.0.md》。' % len(out))
    print('下一步：重跑 tools/build_setting_book.py，确认合订本与拆分前逐字节一致。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
