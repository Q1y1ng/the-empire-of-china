#!/usr/bin/env python3
"""军区司令品级修订：三品→二品（级别待遇以军衔确认，上将＝二品）

依据《全国军事编制设定(2026)》第二编「级别待遇对照（2026冻结·作者表）」：
军职职级待遇随军衔——军区司令岗位标准衔为上将，待遇记二品；资浅授中将者享三品。
处理范围：设定/全国官员名录*.md（含全卷合订本）。
规则：
    1) 口径行「舰队司令/军区司令二~三品」→「舰队司令、军区司令二品（上将·资浅授中将者三品）」
    2) 其余含「军区司令」且含「三品」的行（不含政委）→「三品」→「二品」（保留【推演】/（州常第10席）等后缀）
"""
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OLD_KOUJING = "舰队司令/军区司令二~三品"
NEW_KOUJING = "舰队司令、军区司令二品（上将·资浅授中将者三品）"

total_files = 0
total_lines = 0
for path in sorted(glob.glob(os.path.join(ROOT, '设定', '全国官员名录*.md'))):
    with open(path, encoding='utf-8') as fh:
        lines = fh.read().splitlines()
    changed = 0
    out = []
    for line in lines:
        if OLD_KOUJING in line:
            line = line.replace(OLD_KOUJING, NEW_KOUJING)
            changed += 1
        elif '军区司令' in line and '三品' in line and '政委' not in line:
            line, n = re.subn('三品', '二品', line)
            changed += n
        out.append(line)
    if changed:
        total_files += 1
        total_lines += changed
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(out) + '\n')
        print(f'{os.path.basename(path)}: {changed} 处')
print(f'--- 共 {total_files} 文件 / {total_lines} 处 ---')
