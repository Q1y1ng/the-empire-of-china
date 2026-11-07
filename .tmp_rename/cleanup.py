# -*- coding: utf-8 -*-
"""改名后收尾：清复用标记、删附录A、改符号约定与生年注。"""
import io, os, re

BOOK = '中华帝国设定全书(2026).md'
BIO = '设定/帝国高层人物小传(2026).md'


def read(p):
    return io.open(p, encoding='utf-8').read()


def write(p, t):
    io.open(p, 'w', encoding='utf-8').write(t)


def strip_markers(t):
    t = t.replace('※复用', '')
    t = t.replace('（复用）', '')
    t = t.replace('复用名人物', '本卷人物')
    return t


# ---- 1. 小传：删附录A，改写口径与生年注 ----
t = read(BIO)
start = t.find('## 附录A')
if start >= 0:
    nxt = t.find('\n## ', start + 5)
    if nxt < 0:
        nxt = len(t)
    t = t[:start] + t[nxt + 1:]
t = strip_markers(t)
t = t.replace('> †＝史实原型生年（卒年见附录A）。※人物生年落在 1959—1970 年，2026 年在位年龄 56—67 岁，符合"55～68 岁"推演带。',
              '> ※＝推演创作。人物生年落在 1951—1970 年，2026 年在位年龄 56—75 岁。')
t = re.sub(r'> \*\*生年口径补注（2026-10 裁决）\*\*：.*?(?=\n)', '> **生年口径补注**：本卷人物生年一律取虚构生年，2026 年在位年龄按 55～75 岁推演带设定。', t, flags=re.S)
write(BIO, t)

# ---- 2. 全书：同款清理 ----
t = read(BOOK)
start = t.find('## 附录A')
while start >= 0:
    nxt = t.find('\n## ', start + 5)
    if nxt < 0:
        nxt = len(t)
    t = t[:start] + t[nxt + 1:]
    start = t.find('## 附录A')
t = strip_markers(t)
t = t.replace('> **符号约定**：姓名后标※＝推演创作；标"复用"＝复用中共历史上已故正面人物姓名（被双规、违法犯罪者不复用）。【推演】＝可调整的推演项（非冻结）。',
              '> **符号约定**：姓名后标※＝推演创作；【推演】＝可调整的推演项（非冻结）。')
t = t.replace('> †＝史实原型生年（卒年见附录A）。※人物生年落在 1959—1970 年，2026 年在位年龄 56—67 岁，符合"55～68 岁"推演带。',
              '> ※＝推演创作。人物生年落在 1951—1970 年，2026 年在位年龄 56—75 岁。')
t = re.sub(r'> \*\*生年口径补注（2026-10 裁决）\*\*：.*?(?=\n)', '> **生年口径补注**：本卷人物生年一律取虚构生年，2026 年在位年龄按 55～75 岁推演带设定。', t, flags=re.S)
t = t.replace('**1. 朱昭文**（皇族，非复用名）', '**1. 朱昭文**（皇族）')
write(BOOK, t)

# ---- 3. 各名录卷：符号约定行 ----
files = []
for root, dirs, fs in os.walk('设定'):
    for f in fs:
        if f.endswith('.md'):
            files.append(os.path.join(root, f))
files.append(BOOK)
for p in files:
    t = read(p)
    o = t
    t = strip_markers(t)
    t = t.replace('；※复用＝复用已故正面人物姓名', '')
    t = t.replace('；注明"复用"＝中共历史上已故正面人物姓名', '')
    t = t.replace('；标"复用"＝复用中共历史上已故正面人物姓名（被双规、违法犯罪者不复用）', '')
    t = t.replace('复用中共历史上已故正面人物姓名者不改名（被双规、违法犯罪者一律不复用）', '人物姓名一律为推演创作')
    t = t.replace('注明"复用"＝中共历史上已故正面人物姓名', '')
    if t != o:
        write(p, t)
print('done')
