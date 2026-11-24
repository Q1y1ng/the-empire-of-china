"""共面容差体检（纯 Python，读 bounds.csv）：找「两张面落在同一个平面上还互相重叠」的构件对。

两类问题：
  1. **完全重合件**——包围盒在 1 cm 内相同：要么是重复建模，要么是同一构件被建了两遍
     （值房那一轮删掉 13 对，就是这一类）。
  2. **共面重叠面**——A 的某个面与 B 的同一个面同向同平面（差 < 5 mm）、且在另两轴上重叠
     超过 0.3 m × 0.3 m：两片朝向相同的面挤在一个平面上，只要机位一动就会 z-fighting。
     注意「贴面对接」（A.x1 == B.x0，两片法线相反）是**正常接缝**，不算。

用法： PYTHONIOENCODING=utf-8 py -3 tools/palace/audit_faces.py
"""
import csv
import os
from collections import defaultdict

WORK = os.path.join(os.environ.get("TEMP", "/tmp"), "palace_massing")
SRC = os.path.join(WORK, "bounds.csv")
EPS = 0.005          # 共面判定的容差（5 mm）
MIN_A = 0.3 * 0.3    # 共面重叠的最小面积（m²）
CELL = 24.0

objs = []
with open(SRC, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        o = {"name": r["name"],
             "x0": float(r["x0"]), "x1": float(r["x1"]),
             "y0": float(r["y0"]), "y1": float(r["y1"]),
             "z0": float(r["z0"]), "z1": float(r["z1"])}
        o["id"] = len(objs)
        objs.append(o)
print("构件 %d" % len(objs))


def cells(o):
    for ix in range(int(o["x0"] // CELL), int(o["x1"] // CELL) + 1):
        for iy in range(int(o["y0"] // CELL), int(o["y1"] // CELL) + 1):
            yield ix, iy


grid = defaultdict(list)
for o in objs:
    for c in cells(o):
        grid[c].append(o["id"])

pairs = set()
for c, ids in grid.items():
    if len(ids) < 2:
        continue
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            pairs.add((ids[i], ids[j]) if ids[i] < ids[j] else (ids[j], ids[i]))
print("包围盒同格对 %d" % len(pairs))

dup, cop = [], []
for (i, j) in pairs:
    a, b = objs[i], objs[j]
    # 完全重合
    if (abs(a["x0"] - b["x0"]) < 0.01 and abs(a["x1"] - b["x1"]) < 0.01
            and abs(a["y0"] - b["y0"]) < 0.01 and abs(a["y1"] - b["y1"]) < 0.01
            and abs(a["z0"] - b["z0"]) < 0.01 and abs(a["z1"] - b["z1"]) < 0.01):
        dup.append((a["name"], b["name"], round(a["x1"] - a["x0"], 1),
                    round(a["y1"] - a["y0"], 1), round(a["z1"] - a["z0"], 1)))
        continue
    # 同向共面：同一条边的两个面在同一平面、法线同向
    for ax in ("x", "y", "z"):
        u, v = {"x": ("y", "z"), "y": ("x", "z"), "z": ("x", "y")}[ax]
        for side in ("0", "1"):
            k = ax + side
            if abs(a[k] - b[k]) > EPS:
                continue
            ou = min(a[u + "1"], b[u + "1"]) - max(a[u + "0"], b[u + "0"])
            ov = min(a[v + "1"], b[v + "1"]) - max(a[v + "0"], b[v + "0"])
            if ou > 0 and ov > 0 and ou * ov > MIN_A:
                cop.append((round(ou * ov, 2), a["name"], b["name"],
                            "%s%s=%.2f" % (ax, "+" if side == "1" else "-", a[k]),
                            round(ou, 2), round(ov, 2)))
                break

print("\n===== 完全重合件 %d 对 =====" % len(dup))
for d in dup[:15]:
    print("   %-24s = %-24s  尺寸 %.1f×%.1f×%.1f" % d)

cop.sort(reverse=True)
print("\n===== 同向共面重叠 %d 处（面积 > 0.09 m²） =====" % len(cop))
for c in cop[:25]:
    print("   %8.2f m²  %-22s × %-22s  @ %s  重叠 %.2f×%.2f" % c)

# 按构件对归并，方便判断是该"挪一件"还是"删一件"
agg = defaultdict(float)
for a, x, y, pl, ou, ov in cop:
    agg[(x, y)] += a
print("\n===== 共面最多的 12 对 =====")
for (x, y), s in sorted(agg.items(), key=lambda kv: -kv[1])[:12]:
    print("   %8.2f m²  %s × %s" % (s, x, y))
print("\nFACES_DONE")
