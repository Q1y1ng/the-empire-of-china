"""间隙体检（纯 Python，读 bounds.csv）：找「本该贴面、却隔着 2–15 cm 缝」的两构件。

判据：两个盒子在某一轴上「相邻不相交」（间距 0.02–0.15 m），另两轴的重叠都 ≥ 0.4 m。
这正是接缝最刺眼的一类——两块该咬合的面之间留了一条细缝，从任何角度都是一道黑线。

用法： PYTHONIOENCODING=utf-8 py -3 tools/palace/audit_gaps.py
"""
import csv
import os
from collections import Counter, defaultdict

WORK = os.path.join(os.environ.get("TEMP", "/tmp"), "palace_massing")
SRC = os.path.join(WORK, "bounds.csv")
GAP_LO, GAP_HI = 0.02, 0.15
OVER = 0.4
CELL = 20.0


def cls(n):
    p = n.split("·")
    return p[0] if len(p) > 1 else n


objs = []
with open(SRC, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        o = {"name": r["name"],
             "x0": float(r["x0"]), "x1": float(r["x1"]),
             "y0": float(r["y0"]), "y1": float(r["y1"]),
             "z0": float(r["z0"]), "z1": float(r["z1"])}
        o["id"] = len(objs)
        objs.append(o)

grid = defaultdict(list)
for o in objs:
    for ix in range(int(o["x0"] // CELL), int(o["x1"] // CELL) + 1):
        for iy in range(int(o["y0"] // CELL), int(o["y1"] // CELL) + 1):
            grid[(ix, iy)].append(o["id"])

pairs = set()
for ids in grid.values():
    if len(ids) < 2:
        continue
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            pairs.add((a, b) if a < b else (b, a))
print("同格对 %d" % len(pairs))

found = []
for (i, j) in pairs:
    a, b = objs[i], objs[j]
    for ax in ("x", "y", "z"):
        u, v = {"x": ("y", "z"), "y": ("x", "z"), "z": ("x", "y")}[ax]
        ou = min(a[u + "1"], b[u + "1"]) - max(a[u + "0"], b[u + "0"])
        ov = min(a[v + "1"], b[v + "1"]) - max(a[v + "0"], b[v + "0"])
        if ou < OVER or ov < OVER:
            continue
        g = max(a[ax + "0"] - b[ax + "1"], b[ax + "0"] - a[ax + "1"])
        if GAP_LO <= g <= GAP_HI:
            found.append((round(g, 3), a["name"], b["name"], ax,
                          round(ou, 2), round(ov, 2)))
            break

print("\n===== 2–15 cm 的贴面缝：%d 处 =====" % len(found))
c = Counter((cls(a), cls(b)) for _g, a, b, _ax, _u, _v in found)
for (a, b), n in c.most_common(12):
    print("   %4d 处  %s × %s" % (n, a, b))
print("\n—— 明细（前 25）——")
for g, a, b, ax, ou, ov in sorted(found)[:25]:
    print("   %5.2f cm  %-24s × %-24s  沿%s 重叠 %.1f×%.1f m"
          % (g * 100, a, b, ax, ou, ov))
print("\nGAPS_DONE")
