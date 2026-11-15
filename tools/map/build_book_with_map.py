# -*- coding: utf-8 -*-
"""一次性：把八州政区图插入《中华帝国设定全书》并输出新版 PDF。"""
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, r"E:\AI\帝国\tools")
from build_setting_book import (TYPST_SETTING_INJECT, fix_divider,
                                fix_escaped_bold, fix_figure)

ROOT = r"E:\AI\帝国"
MD = os.path.join(ROOT, "设定集", "中华帝国设定全书(2026).md")
MAP_SRC = os.path.join(ROOT, "docs", "assets", "中华帝国全图(2026)·八州政区图.png")
MAP_TMP = os.path.join(tempfile.gettempdir(), "empire_map_for_book.png")
TYP = os.path.join(tempfile.gettempdir(), "book_with_map.typ")
OUT = r"E:\桌面\中华帝国设定全书(2026)·含八州政区图.pdf"

shutil.copyfile(MAP_SRC, MAP_TMP)
subprocess.run(["pandoc", "-f", "gfm", "--wrap=none", MD, "-t", "typst", "-o", TYP],
               check=True)
with open(TYP, encoding="utf-8") as fh:
    typ = fh.read()
typ = fix_figure(fix_divider(fix_escaped_bold(typ)))

marker = "= 第四卷 疆域与首都\n<第四卷-疆域与首都>"
if marker not in typ:
    raise SystemExit("找不到第四卷标题")
fig = marker + """

#v(0.3em)
#figure(
  image("%s", width: 100%%),
  caption: [中华帝国全图（2026）·八州政区图　京畿直隶州—长安／华北州—北京／东北州—沈阳／蒙古州—呼和浩特／西北州—乌鲁木齐／江南州—上海／云贵州—南宁／青藏州—拉萨]
)
#pagebreak()
""" % os.path.basename(MAP_TMP)
typ = typ.replace(marker, fig, 1)

inject = TYPST_SETTING_INJECT.replace(
    "中华帝国设定集·全卷合订本（2026）", "中华帝国设定全书（2026）"
).replace(
    "中华帝国设定集 · 全卷合订本（2026）", "中华帝国设定全书（2026）"
)
with open(TYP, "w", encoding="utf-8") as fh:
    fh.write(inject + typ)

subprocess.run(["typst", "compile", TYP, OUT], check=True)
print("OK", OUT, os.path.getsize(OUT) / 1048576, "MB")

