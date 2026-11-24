"""墙体检 v3（纯 Python，读 bounds.csv）

A. 落地：沿墙长每 2 m 一采样（墙厚方向取中），找「顶面与墙底齐平」或「墙底插在其内」的承托件；
   施底面积 > 200 m² 且顶面不高于墙底 0.4 m 的大平铺件（地坪/河/路）不算承托——
   它们只是地面，墙要落在台明/墙体/台基上才算真落地（但落到地坪上本来就对，故地坪另计一档）。
B. 连接：墙端是否有墙 / 门 / 建筑接住；排除地面类。
C. 埋没：整段墙被别的实体盖住（支撑顶面高于墙顶）——看不见的墙。
D. 墙网络连通分量。

用法： PYTHONIOENCODING=utf-8 py -3 tools/palace/audit_walls2.py
"""
import csv
import json
import math
import os
from collections import Counter, defaultdict

WORK = os.path.join(os.environ.get("TEMP", "/tmp"), "palace_massing")
SRC = os.path.join(WORK, "bounds.csv")

TOL_SIT = 0.16
TOL_TOUCH = 0.35
TOL_LOOSE = 3.0
STEP = 2.0
BIG_AREA = 200.0
TERRAIN = ("地坪", "地面", "河", "岸", "御道", "广场", "草坪", "路", "水面", "湖")


def kind_of(n):
    if ("栏" in n) or ("望柱" in n):
        return "rail"
    if ("院门" in n) or ("门楼" in n) or ("门洞" in n) or ("大门" in n):
        return "gate"
    if ("墙" in n) or ("垛" in n):
        return "wall"
    if ("树" in n) or ("草" in n) or ("假山" in n) or ("石" in n):
        return "prop"
    return "structure"


def is_wall(k, n):
    return k == "wall" and not n.endswith("_瓦")


objs = []
with open(SRC, encoding="utf-8") as f:
    for row in csv.DictReader(f):
        o = {k: (row[k] if k == "name" else float(row[k]))
             for k in ("name", "x0", "x1", "y0", "y1", "z0", "z1")}
        o["area"] = max(0.0, o["x1"] - o["x0"]) * max(0.0, o["y1"] - o["y0"])
        o["kind"] = kind_of(o["name"])
        o["terrain"] = (any(t in o["name"] for t in TERRAIN)) or o["area"] > 3000.0
        objs.append(o)
for i, o in enumerate(objs):
    o["id"] = i
walls = [o for o in objs if is_wall(o["kind"], o["name"])]

CELL = 12.0
grid = defaultdict(list)


def cells(o):
    for ix in range(int(math.floor(o["x0"] / CELL)), int(math.floor(o["x1"] / CELL)) + 1):
        for iy in range(int(math.floor(o["y0"] / CELL)), int(math.floor(o["y1"] / CELL)) + 1):
            yield ix, iy


for o in objs:
    for c in cells(o):
        grid[c].append(o["id"])


def near(px, py, r):
    out = set()
    for ix in range(int(math.floor((px - r) / CELL)), int(math.floor((px + r) / CELL)) + 1):
        for iy in range(int(math.floor((py - r) / CELL)), int(math.floor((py + r) / CELL)) + 1):
            out.update(grid.get((ix, iy), ()))
    return out


def covers(o, px, py, tol=0.0):
    return (o["x0"] - tol <= px <= o["x1"] + tol) and (o["y0"] - tol <= py <= o["y1"] + tol)


def support_at(px, py, zb, selfid, allow_terrain):
    best = None
    for idx in near(px, py, 0.5):
        o = objs[idx]
        if idx == selfid or not covers(o, px, py, 0.02):
            continue
        if o["terrain"] and not allow_terrain:
            continue
        if o["z0"] <= zb <= o["z1"]:
            g = 0.0
        elif zb - TOL_SIT <= o["z1"] <= zb + 0.02:
            g = zb - o["z1"]
        else:
            continue
        if best is None or g < best[0]:
            best = (g, o["name"], o["z0"], o["z1"])
    return best


# ---------------------------------------------------------------- A. 落地（密集采样）
print("总构件 %d，墙类 %d" % (len(objs), len(walls)))
bad = []
for w in walls:
    zb, zt = w["z0"], w["z1"]
    along_x = (w["x1"] - w["x0"]) >= (w["y1"] - w["y0"])
    L = (w["x1"] - w["x0"]) if along_x else (w["y1"] - w["y0"])
    n = max(3, int(math.ceil(L / STEP)))
    means = Counter()
    n_hard = n_terr = 0
    worst = None
    first_bad = None
    for i in range(n + 1):
        t = i / n
        if along_x:
            px = w["x0"] + (w["x1"] - w["x0"]) * t
            py = (w["y0"] + w["y1"]) / 2
        else:
            py = w["y0"] + (w["y1"] - w["y0"]) * t
            px = (w["x0"] + w["x1"]) / 2
        s = support_at(px, py, zb, w["id"], allow_terrain=True)
        s2 = support_at(px, py, zb, w["id"], allow_terrain=False)
        if s2 is None:
            n_hard += 1
        if s is None:
            n_terr += 1
            if first_bad is None:
                first_bad = (round(px, 1), round(py, 1))
        else:
            means[s[1].split("·")[0]] += 1
            if worst is None or s[0] > worst[0]:
                worst = s
    w["n_hard"] = n_hard
    w["n_void"] = n_terr
    w["n_samp"] = n + 1
    w["supports"] = dict(means)
    w["worst"] = worst
    w["first_bad"] = first_bad
    if n_hard or n_terr:
        bad.append(w)

print("\n===== A. 落地：%d 段墙有悬空采样 =====" % len(bad))
for w in sorted(bad, key=lambda o: -(o["n_hard"] * 10 + o["n_void"]))[:40]:
    print("  %-30s 底%7.2f 顶%7.2f  无承托 %d/%d 含地面也空 %d  首个缺口 (%s,%s) 承托=%s"
          % (w["name"], w["z0"], w["z1"], w["n_void"], w["n_samp"], w["n_hard"],
             w["first_bad"][0] if w["first_bad"] else "-",
             w["first_bad"][1] if w["first_bad"] else "-", w["supports"]))

print("\n===== A2. 支撑面有缝（0.03 < gap_max ≤ 0.16）的墙 =====")
seam = [w for w in walls if w["worst"] and w["worst"][0] > 0.03 and w["n_void"] == 0]
print("  共 %d 段" % len(seam))
for w in sorted(seam, key=lambda o: -o["worst"][0])[:20]:
    print("  %-30s gap=%5.3f 承托=%s" % (w["name"], w["worst"][0], w["worst"][1]))

# ---------------------------------------------------------------- C. 埋没
# 树是两个合并网格（树·干 / 树·冠，一棵树的几何塞进同一个 mesh），
# 它的包围盒等于整座宫城 —— 包围盒法在这里必然误报，直接排除。
_MERGED = ("树·冠", "树·干")
buried = []
for w in walls:
    if w["name"] in _MERGED:
        continue
    s = support_at((w["x0"] + w["x1"]) / 2, (w["y0"] + w["y1"]) / 2, w["z0"], w["id"], True)
    if s and s[1] in _MERGED:
        s = None
    if s and s[3] >= w["z1"] - 0.05 and (s[3] - s[2]) > 1.0:
        buried.append((w["name"], w["z0"], w["z1"], s[1], s[2], s[3]))
print("\n===== C. 整段被实体埋没的墙 %d 段 =====" % len(buried))
for b in buried[:25]:
    print("  %-30s 墙[%7.2f..%7.2f] 被 %s [%7.2f..%7.2f] 盖住" % b)

# ---------------------------------------------------------------- B. 连接
ends = []
for w in walls:
    along_x = (w["x1"] - w["x0"]) >= (w["y1"] - w["y0"])
    for side in ("A", "B"):
        if along_x:
            ea, eb0, eb1 = (w["x0"] if side == "A" else w["x1"]), w["y0"], w["y1"]
        else:
            ea, eb0, eb1 = (w["y0"] if side == "A" else w["y1"]), w["x0"], w["x1"]
        kinds, who = Counter(), Counter()
        for t in (0.25, 0.5, 0.75):
            v = eb0 + (eb1 - eb0) * t
            d = -0.05 if side == "A" else 0.05
            px, py = (ea + d, v) if along_x else (v, ea + d)
            seen = set()
            for idx in near(px, py, TOL_TOUCH):
                o = objs[idx]
                if o["id"] == w["id"] or idx in seen or o["terrain"]:
                    continue
                if not covers(o, px, py, TOL_TOUCH):
                    continue
                if o["z1"] < w["z0"] - 1.2 or o["z0"] > w["z0"] + 2.2:
                    continue
                kinds[o["kind"]] += 1
                who[o["name"]] += 1
                seen.add(idx)
        verdict = "open"
        for k in ("wall", "gate", "structure", "rail"):
            if kinds.get(k, 0) >= 2:
                verdict = k
                break
        ends.append({"wall": w["name"], "side": side, "verdict": verdict,
                     "kinds": dict(kinds), "who": who.most_common(3),
                     "x": ((w["x0"] if side == "A" else w["x1"]) if along_x
                           else (w["x0"] + w["x1"]) / 2),
                     "y": ((w["y0"] + w["y1"]) / 2 if along_x
                           else (w["y0"] if side == "A" else w["y1"]))})

vc = Counter(e["verdict"] for e in ends)
print("\n===== B. 墙端 %d 个 =====" % len(ends))
for k, v in vc.most_common():
    print("   %-10s %d" % (k, v))

open_ends = [e for e in ends if e["verdict"] == "open"]
print("\n   —— 真断头 %d 个 ——" % len(open_ends))
detail = []
for e in open_ends:
    px, py = e["x"], e["y"]
    cands = []
    for idx in near(px, py, TOL_LOOSE):
        o = objs[idx]
        if o["id"] == -1:
            continue
        dx = max(o["x0"] - px, 0.0, px - o["x1"])
        dy = max(o["y0"] - py, 0.0, py - o["y1"])
        d = math.hypot(dx, dy)
        if d <= TOL_LOOSE:
            cands.append((d, o["name"], o["z0"], o["z1"]))
    cands.sort()
    detail.append((e, cands[:3]))
    print("   %-28s (%7.1f,%7.1f) -> %s" % (
        e["wall"], px, py,
        " | ".join("%.2fm %s[z%.1f..%.1f]" % c for c in cands[:3]) or "3m 内空无一物"))

# ---------------------------------------------------------------- D. 分量
parent = list(range(len(walls)))


def find(a):
    while parent[a] != a:
        parent[a] = parent[parent[a]]
        a = parent[a]
    return a


def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[rb] = ra


wid = {}
for i, w in enumerate(walls):
    wid.setdefault(w["name"], i)
for e in ends:
    if e["verdict"] == "wall":
        for nm, _c in e["who"]:
            if nm in wid and wid[nm] != wid[e["wall"]]:
                union(wid[e["wall"]], wid[nm])
comp = defaultdict(list)
for i, w in enumerate(walls):
    comp[find(i)].append(w["name"])
print("\n===== D. 墙网络 %d 段 -> %d 块 =====" % (len(walls), len(comp)))
for root, names in sorted(comp.items(), key=lambda kv: -len(kv[1]))[:10]:
    print("   %4d 段  %s" % (len(names), " / ".join(names[:5]) + (" …" if len(names) > 5 else "")))
singles = [n[0] for n in comp.values() if len(n) == 1]
print("   孤立单段 %d：%s" % (len(singles), " / ".join(singles[:15])))

with open(os.path.join(WORK, "wall_audit3.json"), "w", encoding="utf-8") as f:
    json.dump({"walls": walls, "ends": ends,
               "open": [{"wall": e["wall"], "x": e["x"], "y": e["y"],
                         "near": [(round(d, 2), n, round(z0, 2), round(z1, 2)) for d, n, z0, z1 in c]}
                        for e, c in detail]}, f, ensure_ascii=False, indent=1)
print("\nAUDIT3_DONE")

# ---------------------------------------------------------------- E. 树 vs 墙
# 树是两个合并网格，包围盒法查不出来（见 C 段说明）；改查落位表 trees.csv：
# 每棵树心到任一墙/城墙矩形的平面距离必须 ≥ 树冠半径 4.3 m。
_TCSV = os.path.join(WORK, "trees.csv")
if os.path.exists(_TCSV):
    trees = []
    with open(_TCSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            trees.append((float(row["x"]), float(row["y"])))
    bad = []
    for (tx, ty) in trees:
        for w in walls:
            dx = max(w["x0"] - tx, 0.0, tx - w["x1"])
            dy = max(w["y0"] - ty, 0.0, ty - w["y1"])
            if math.hypot(dx, dy) < 4.3:
                bad.append((round(tx, 1), round(ty, 1), w["name"],
                            round(math.hypot(dx, dy), 2)))
                break
    print("\n===== E. 树 vs 墙：%d 棵，侵入墙/城墙 4.3 m 内 %d 棵 =====" % (len(trees), len(bad)))
    for b in bad[:15]:
        print("   树(%s,%s) ↮ %s  距 %.2f m" % b)
    if not bad:
        print("   OK：全部行道树都在禁区之外（树冠半径 4.3 m）")

