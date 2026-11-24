"""包围盒查询小工具：打印与给定平面矩形相交的所有构件（按底高排序）。

用法： PYTHONIOENCODING=utf-8 py -3 tools/palace/where.py X0 X1 Y0 Y1 [名字过滤]
"""
import csv
import os
import sys

WORK = os.path.join(os.environ.get("TEMP", "/tmp"), "palace_massing")
SRC = os.path.join(WORK, "bounds.csv")

x0, x1, y0, y1 = (float(v) for v in sys.argv[1:5])
flt = sys.argv[5] if len(sys.argv) > 5 else ""

rows = []
with open(SRC, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        ax0, ax1 = float(r["x0"]), float(r["x1"])
        ay0, ay1 = float(r["y0"]), float(r["y1"])
        if ax1 < x0 or ax0 > x1 or ay1 < y0 or ay0 > y1:
            continue
        if flt and flt not in r["name"]:
            continue
        rows.append((float(r["z0"]), r["name"], ax0, ax1, ay0, ay1,
                     float(r["z0"]), float(r["z1"])))
rows.sort()
print("命中 %d 件  区域 x[%g,%g] y[%g,%g]  过滤=%r" % (len(rows), x0, x1, y0, y1, flt))
print("%-34s %-30s %-28s %s" % ("名字", "x0..x1", "y0..y1", "z0..z1"))
for _, n, ax0, ax1, ay0, ay1, z0, z1 in rows[:120]:
    print("%-34s %10.2f..%-10.2f %10.2f..%-10.2f %7.2f..%-7.2f" % (n, ax0, ax1, ay0, ay1, z0, z1))
