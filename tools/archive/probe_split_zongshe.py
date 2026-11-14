# -*- coding: utf-8 -*-
"""可行性探针：把总设定按 30 个一级标题拆成单章文件，在临时目录里改构建设计，跑一遍拼装，
再与仓库里现存的合订本逐字节比对。全程只在 %TEMP% 里操作。"""
import io
import os
import re
import shutil
import subprocess
import sys

REPO = r'E:\AI\帝国'
TMP = os.path.join(os.environ['TEMP'], 'split_probe')
SRC_SET = os.path.join(REPO, '设定')
SRC_TOOLS = os.path.join(REPO, 'tools')
TS = '中华帝国世界观总设定v2.0.md'

# 1) 复制源与工具
if os.path.isdir(TMP):
    shutil.rmtree(TMP)
os.makedirs(os.path.join(TMP, '设定'))
os.makedirs(os.path.join(TMP, 'tools'))
for name in os.listdir(SRC_SET):
    if name.endswith('.md'):
        shutil.copy2(os.path.join(SRC_SET, name), os.path.join(TMP, '设定', name))
for name in os.listdir(SRC_TOOLS):
    if name.endswith('.py'):
        shutil.copy2(os.path.join(SRC_TOOLS, name), os.path.join(TMP, 'tools', name))

SET = os.path.join(TMP, '设定')

# 2) 按一级标题拆
text = io.open(os.path.join(SET, TS), encoding='utf-8').read()
lines = text.split('\n')
starts = [i for i, l in enumerate(lines) if re.match(r'^# ', l)]
blocks = []
for k, i in enumerate(starts):
    end = starts[k + 1] if k + 1 < len(starts) else len(lines)
    body = '\n'.join(lines[i:end]).strip() + '\n'
    title = lines[i][2:].strip()
    blocks.append((title, body))

CN = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '十一', '十二', '十三',
      '十四', '十五', '十六', '十七', '十八', '十九', '二十', '二十一', '二十二', '二十三',
      '二十四', '二十五', '二十六']

new_files = []
for k, (title, body) in enumerate(blocks):
    m = re.match(r'^第(.+)编[：:](.+)$', title)
    if m:
        safe = re.sub(r'[\\/:*?"<>|（）()]', '', m.group(2))
        fname = f'总设定·第{m.group(1)}编·{safe}.md'
    elif title.startswith('附录一'):
        fname = '总设定·附录一·机构品级总表.md'
    elif title.startswith('附录二'):
        fname = '总设定·附录二·军队层级与军衔表.md'
    elif title.startswith('附录'):
        fname = '总设定·附录·设定分类索引.md'
    else:
        fname = '总设定·00·题头说明.md'
    with io.open(os.path.join(SET, fname), 'w', encoding='utf-8', newline='') as fh:
        fh.write(body)
    new_files.append(fname)

os.remove(os.path.join(SET, TS))
print('拆出 %d 个单章文件' % len(new_files))

# 3) 改构建设计：TS_FILE → TS_FILES（按文件名中编序排序，题头最前、附录最后）
order_key = lambda n: (0 if '00·题头' in n else 3 if '附录' in n and '附录一' not in n and '附录二' not in n
                       else 2 if '附录' in n else 1,
                       CN.index(re.search(r'第(.+?)编', n).group(1)) if '编' in n and '第' in n else
                       (1 if '附录一' in n else 2 if '附录二' in n else 9))
ts_files = sorted(new_files, key=order_key)

bp = os.path.join(TMP, 'tools', 'build_setting_book.py')
src = io.open(bp, encoding='utf-8').read()

src = src.replace(
    "TS_FILE = '中华帝国世界观总设定v2.0.md'",
    "TS_FILES = " + repr(ts_files))

src = src.replace(
    '''def ts_block(key):
    """按标题取总设定的一个一级标题块（标题精确匹配优先，前缀匹配兜底）。"""
    blocks = split_h1_blocks(read(os.path.join(SETTING, TS_FILE)).strip())''',
    '''_TS_CACHE = {}


def _all_ts_blocks():
    if 'v' not in _TS_CACHE:
        blocks = []
        for name in TS_FILES:
            blocks.extend(split_h1_blocks(read(os.path.join(SETTING, name)).strip()))
        _TS_CACHE['v'] = blocks
    return _TS_CACHE['v']


def ts_block(key):
    """按标题取总设定的一个一级标题块（标题精确匹配优先，前缀匹配兜底）。"""
    blocks = _all_ts_blocks()''')

src = src.replace(
    "covered = {TS_FILE} | set(DOC_FILES)",
    "covered = set(TS_FILES) | set(DOC_FILES)")

src = src.replace(
    "sources = {TS_FILE: read(os.path.join(SETTING, TS_FILE))}",
    "sources = {n: read(os.path.join(SETTING, n)) for n in TS_FILES}")

io.open(bp, 'w', encoding='utf-8', newline='').write(src)

# 4) 跑拼装
r = subprocess.run([sys.executable, os.path.join(TMP, 'tools', 'build_setting_book.py')],
                   cwd=TMP, capture_output=True, text=True, encoding='utf-8', errors='replace')
print('--- 构建输出 ---')
print(r.stdout.strip())
if r.stderr.strip():
    print('--- stderr ---')
    print(r.stderr.strip()[:2000])

# 5) 与仓库现存合订本逐字节比对
real = os.path.join(SRC_SET, '中华帝国设定集·全卷合订本(2026).md')
probe = os.path.join(SET, '中华帝国设定集·全卷合订本(2026).md')
if os.path.exists(probe):
    a = io.open(real, encoding='utf-8').read()
    b = io.open(probe, encoding='utf-8').read()
    print('--- 比对 ---')
    print('仓库合订本 %d 字符 / 探针合订本 %d 字符' % (len(a), len(b)))
    print('完全一致' if a == b else '不一致：长度差 %d' % (len(b) - len(a)))
    if a != b:
        la, lb = a.split('\n'), b.split('\n')
        for i in range(min(len(la), len(lb))):
            if la[i] != lb[i]:
                print('首个差异行 %d:\n  仓库: %r\n  探针: %r' % (i + 1, la[i][:120], lb[i][:120]))
                break
