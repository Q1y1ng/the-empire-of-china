# -*- coding: utf-8 -*-
"""第二批：补掉第一批扫漏的同型变体（"无数字上限"、中苏安全轨、直隶州议会、小传闻否定句）。"""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(ROOT, '设定')
T = lambda *p: os.path.join(S, *p)

EDITS = [
    dict(f=T('中华帝国世界观总设定v2.0.md'), n=1,
         old='| 79人（列举式，无数字上限） |', new='| 79人（列举式） |'),
    dict(f=T('中华帝国世界观总设定v2.0.md'), n=1,
         old='- 但不能自行决定州长（州长由中央政委会提名、州议会同意后任命）',
         new='- 州长由中央政委会提名、州议会同意后任命——州议会就此行使同意权'),
    dict(f=T('中华帝国世界观总设定v2.0.md'), n=1,
         old='＋安全轨（年度战略磋商、危机热线、联合军演观察员），**不设共同防御条款、不互驻军队**。',
         new='＋安全轨（年度战略磋商、危机热线、联合军演观察员）；两军关系限于安全轨所列三事。'),
    dict(f=T('全国官员名录·卷一·中央与京畿直隶州(2026).md'), n=1,
         old='## 四、中央政治委员会（79人·列举式·无数字上限）',
         new='## 四、中央政治委员会（79人·列举式）'),
    dict(f=T('全国官员名录·总索引(2026).md'), n=1,
         old='政委会 68→79（列举式、无数字上限）', new='政委会 68→79（列举式）'),
    dict(f=T('全国官员名录·总索引(2026).md'), n=1,
         old='79人（列举式、无数字上限）', new='79人（列举式）'),
    dict(f=T('全国官员名录·总索引(2026).md'), n=1,
         old='构成由《中央政治委员会组织法》列举，无数字上限。',
         new='构成由《中央政治委员会组织法》列举确定。'),
    dict(f=T('国别志(2026).md'), n=1,
         old='帝国在此不驻军、不设租界，只做长期购销与技术换资源',
         new='帝国在此以长期购销与技术换资源往来'),
    dict(f=T('帝国高层人物小传(2026).md'), n=1,
         old='③八州州长三品、不任委员（只列席）；', new='③八州州长三品、列席全体会议；'),
]


def main():
    apply = '--apply' in sys.argv
    cache, rows, bad = {}, [], 0
    for i, e in enumerate(EDITS, 1):
        p = e['f']
        if p not in cache:
            with io.open(p, 'r', encoding='utf-8', newline='') as fh:
                cache[p] = fh.read()
        c = cache[p].count(e['old'])
        ok = (c == e['n'])
        bad += 0 if ok else 1
        rows.append((i, os.path.basename(p), e['n'], c, ok))
        if ok and apply:
            cache[p] = cache[p].replace(e['old'], e['new'], e['n'])
    for i, name, exp, got, ok in rows:
        print('%s #%02d %-42s expect=%d got=%d' % ('OK  ' if ok else 'MISS', i, name, exp, got))
    print('\n合计 %d 条，命中异常 %d 条' % (len(EDITS), bad))
    if bad:
        return 1
    if not apply:
        print('干跑通过（未落盘）。加 --apply 执行。')
        return 0
    for p, text in cache.items():
        with io.open(p, 'w', encoding='utf-8', newline='') as fh:
            fh.write(text)
    print('已写入 %d 个文件。' % len(cache))
    return 0


if __name__ == '__main__':
    sys.exit(main())
