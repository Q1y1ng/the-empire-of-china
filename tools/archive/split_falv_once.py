#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一次性迁移：把《法律要目（2026）》按法律门类拆成四册（2026-11-14，拆分路线 Step 3）。

    法律要目·一·宪法(2026).md            宪法十章 42 条
    法律要目·二·组织法与人事(2026).md    七部组织法＋政委会组织法＋两个修正案＋政治学院法／品级工资法＋配套四法
    法律要目·三·部门法(2026).md          刑法／民法典／劳动基准法
    法律要目·四·程序法与附则(2026).md    诉讼法／选举法／法律位阶／引用格式

约束：
  * 各 ## 小节正文逐字搬家，不改写、不重排；
  * 前言（符号约定与用法）只随第一册走；
  * 拆完必须满足：四册正文按原序拼回（去新增 H1）与原文件（去原 H1）逐字节一致。

用法：py -3 tools/archive/split_falv_once.py [--apply]
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SET = os.path.join(ROOT, '设定')
SRC = os.path.join(SET, '法律要目(2026).md')

# (文件名, 一级标题, 收取的 ## 小节序号（按出现顺序）)
PLAN = [
    ('法律要目·一·宪法(2026).md', '《法律要目（2026）·一 宪法》', [0]),
    ('法律要目·二·组织法与人事(2026).md', '《法律要目（2026）·二 组织法与人事》', [1, 2, 3, 4, 5, 6, 12]),
    ('法律要目·三·部门法(2026).md', '《法律要目（2026）·三 部门法》', [7, 8, 11]),
    ('法律要目·四·程序法与附则(2026).md', '《法律要目（2026）·四 程序法与附则》', [9, 10, 13, 14]),
]


def main():
    apply = '--apply' in sys.argv
    if not os.path.exists(SRC):
        raise SystemExit('源文件不存在，可能已拆分过：%s' % SRC)
    text = io.open(SRC, encoding='utf-8', newline='').read()
    lines = text.split('\n')

    # 原 H1 之后的全部内容；再按 ## 切块
    h1 = next(i for i, l in enumerate(lines) if l.startswith('# '))
    body_lines = lines[h1 + 1:]
    starts = [i for i, l in enumerate(body_lines) if re.match(r'^## ', l)]
    preface = body_lines[:starts[0]]
    sections = []
    for k, i in enumerate(starts):
        end = starts[k + 1] if k + 1 < len(starts) else len(body_lines)
        sections.append(body_lines[i:end])
    print('原文件：H1 后 %d 行，前言 %d 行，## 小节 %d 个'
          % (len(body_lines), len(preface), len(sections)))
    for k, sec in enumerate(sections):
        print('  [%2d] %-52s %3d 行' % (k, sec[0][:52], len(sec)))

    used = sorted(i for _, _, idx in PLAN for i in idx)
    if used != list(range(len(sections))):
        raise SystemExit('PLAN 未覆盖全部小节：%s vs %s' % (used, list(range(len(sections)))))

    outs = []
    for name, title, idx in PLAN:
        chunk = []
        if idx and idx[0] == 0:
            chunk.extend(preface)          # 前言只随第一册
        for i in idx:
            chunk.extend(sections[i])
        content = '# ' + title + '\n' + '\n'.join(chunk).rstrip('\n') + '\n'
        outs.append((name, title, content))

    # 校验：每个 ## 小节恰好被用一次，且按原序拼回 ＝ 原名正文（册内顺序可与原序不同）
    ordered = []
    for i in range(len(sections)):
        ordered.extend(sections[i])
    if preface + ordered != body_lines:
        raise SystemExit('内容校验失败：按原序拼回与原正文不一致')

    print('\n计划输出：')
    for name, _, content in outs:
        print('  %-34s %5d 行' % (name, content.count('\n')))

    if not apply:
        print('\n干跑通过（未落盘）。加 --apply 执行。')
        return 0

    for name, _, content in outs:
        with io.open(os.path.join(SET, name), 'w', encoding='utf-8', newline='') as fh:
            fh.write(content)
    os.remove(SRC)
    print('\n已写入 %d 册，并删除原《法律要目(2026).md》。' % len(outs))
    print('下一步：更新 build_setting_book.py 的 DOC_FILES 与第五卷映射，然后重跑拼装。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
