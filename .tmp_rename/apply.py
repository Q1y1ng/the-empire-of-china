# -*- coding: utf-8 -*-
"""批量改名：正文 + 生年 + 百科 slug/文件名。"""
import io, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from people import PEOPLE

ROOT = '.'
SKIP_DIRS = {'.git', 'build', 'node_modules', 'refs', '.tmp_rename'}
OLD = {o for o, *_ in PEOPLE}

# 冲突自检
names_new = [n for _, n, *_ in PEOPLE]
assert len(set(names_new)) == len(names_new), '新名重复'

files = []
for root, dirs, fs in os.walk(ROOT):
    dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
    for f in fs:
        if not f.endswith('.md'):
            continue
        if '合订本' in f or '华北风暴' in f or f == 'CHANGELOG.md':
            continue
        files.append(os.path.join(root, f))

collisions = []
name_hits = {o: 0 for o in OLD}
year_fix = 0

for p in files:
    lines = io.open(p, encoding='utf-8').read().split('\n')
    changed = False
    for i, l in enumerate(lines):
        hit = [o for o in OLD if o in l]
        if not hit:
            continue
        for o, n, slug, yr in PEOPLE:
            if o in l:
                name_hits[o] += l.count(o)
                l = l.replace(o, n)
        # 生年：本行若带历史生年，替换为虚构生年（取本行出现的第一个人）
        m = re.search(r'1[89]\d\d†', l)
        if m and len(hit) == 1:
            yr = next(y for o, n, s, y in PEOPLE if o == hit[0])
            l = l[:m.start()] + str(yr) + l[m.end():]
            year_fix += 1
        lines[i] = l
        changed = True
    if changed:
        io.open(p, 'w', encoding='utf-8').write('\n'.join(lines))

missing = [o for o, c in name_hits.items() if c == 0]
print('改名文件数', len(files), '| 生年替换', year_fix)
print('未命中原名（需检查）:', missing)

# 百科：改 slug 与文件名
SRC = 'docs/baike/src'
renamed = []
for o, n, slug, yr in PEOPLE:
    for f in os.listdir(SRC):
        if not f.endswith('.md'):
            continue
        t = io.open(os.path.join(SRC, f), encoding='utf-8').read()
        m = re.search(r'^slug:\s*(.+)$', t, re.M)
        if not m:
            continue
        old_slug = m.group(1).strip()
        ti = re.search(r'^title:\s*(.+)$', t, re.M)
        if not ti or ti.group(1).strip() != n:
            continue
        t2 = re.sub(r'^slug:\s*.+$', 'slug: ' + slug, t, count=1, flags=re.M)
        io.open(os.path.join(SRC, f), 'w', encoding='utf-8').write(t2)
        os.replace(os.path.join(SRC, f), os.path.join(SRC, slug + '.md'))
        renamed.append((f, slug + '.md'))
        break
print('百科改名', len(renamed))
for a, b in renamed:
    print('  ', a, '->', b)
