"""平面级共面体检（纯 Python，读 faces.csv）：找「同向、同平面、互相重叠」的两张真面。

与 audit_faces.py（包围盒法）的区别：这里用的是**真实多边形**的平面与外接矩形，
斜屋面不再被误判，平面数值也来自实际顶点。

用法： PYTHONIOENCODING=utf-8 py -3 tools/palace/audit_planes.py
"""
import csv
import os
from collections import defaultdict

WORK = os.path.join(os.environ.get("TEMP", "/tmp"), "palace_massing")
SRC = os.path.join(WORK, "faces.csv")
EPS = 0.004          # 同平面容差（4 mm）
MIN_OVER = 0.02      # 两张面的重叠面积下限（m²）

faces = []
with open(SRC, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        faces.append((r["name"], int(r["axis"]), int(r["sign"]), float(r["const"]),
                      float(r["u0"]), float(r["u1"]), float(r["v0"]), float(r["v1"]),
                      float(r["area"])))
print("轴对齐大面 %d 张" % len(faces))

# 按 (轴, 方向, 平面常数) 分桶；常数按 EPS 取整
buckets = defaultdict(list)
for f in faces:
    key = (f[1], f[2], round(f[3] / EPS))
    buckets[key].append(f)
print("平面桶 %d 个" % len(buckets))

pairs = defaultdict(float)
where = {}
for key, fl in buckets.items():
    if len(fl) < 2:
        continue
    # 朝下的面一律不报：两张「朝下 + 同平面」的面必然都藏在别的实体里
    # （墙底压阶条、河床压驳岸底），从任何机位都看不见，属噪声。
    if key[0] == 2 and key[1] < 0:
        continue
    for i in range(len(fl)):
        a = fl[i]
        for j in range(i + 1, len(fl)):
            b = fl[j]
            if a[0] == b[0]:
                continue                      # 同一构件自叠（合并网格内部）
            ou = min(a[5], b[5]) - max(a[4], b[4])
            ov = min(a[7], b[7]) - max(a[6], b[6])
            if ou <= 0 or ov <= 0:
                continue
            over = ou * ov
            if over < MIN_OVER:
                continue
            k = (a[0], b[0]) if a[0] < b[0] else (b[0], a[0])
            pairs[k] += over
            where.setdefault(k, (key[0], key[1], round(a[3], 2)))

print("\n===== 共面重叠的构件对：%d 对 =====" % len(pairs))
tot = 0.0
for (a, b), s in sorted(pairs.items(), key=lambda kv: -kv[1])[:40]:
    ax, sg, c = where[(a, b)]
    tot += s
    print("  %9.2f m²  %-26s × %-26s  @ %s%s=%.2f"
          % (s, a, b, "xyz"[ax], "+" if sg > 0 else "-", c))
allsum = sum(pairs.values())
print("\n合计 %.1f m²（前 40 对占 %.1f m²）" % (allsum, tot))
print("\n===== 按构件名归类（前 15） =====")
agg = defaultdict(float)
for (a, b), s in pairs.items():
    agg[a] += s
    agg[b] += s
for k, v in sorted(agg.items(), key=lambda kv: -kv[1])[:15]:
    print("  %9.2f m²  %s" % (v, k))
print("\nPLANES_DONE")
