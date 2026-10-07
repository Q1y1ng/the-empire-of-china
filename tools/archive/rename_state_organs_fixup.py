# -*- coding: utf-8 -*-
"""定点补扫：词根缺漏、办公室后缀、○○通配。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "设定"

replacements = [
    # 合订本/名录边角
    ("华北州审计部办公室", "华北州审计厅办公室"),
    ("卷六州财政部行", "卷六州财政厅行"),
    ("州○○部（州政府组成机关，含州宣传厅）", "州○○厅（州政府组成机关，含州宣传厅）"),
    ("州○○部（州政府组成机关，含州宣传部）", "州○○厅（州政府组成机关，含州宣传厅）"),
    ("州应急管理部", "州应急管理厅"),
    ("对外贸易部负责", "对外贸易厅负责"),
    ("原华北州公安部部长", "原华北州公安厅厅长"),
    ("原华北州公安部", "原华北州公安厅"),
    ("（州财政部·卷六现任）", "（州财政厅·卷六现任）"),
    ("- **部**：州政府办公厅", "- **厅**：州政府办公厅"),
    ("组成机关以\"○○部\"命名", "组成机关以\"○○厅\"命名"),
    ("组成机关以“○○部”命名", "组成机关以“○○厅”命名"),
]

changed = 0
for path in sorted(ROOT.rglob("*.md")):
    text = path.read_text(encoding="utf-8")
    orig = text
    for a, b in replacements:
        text = text.replace(a, b)
    if text != orig:
        path.write_text(text, encoding="utf-8")
        print(path.name)
        changed += 1
print(f"changed={changed}")
