"""墙体审计：落地性（底部与支撑面之间的空隙）+ 连接性（墙端是否有东西接住）。

⚠️ 已被 `audit_walls2.py` 取代（更快、更准），留作射线法参考。
   射线法的坑：必须先把墙类 hide_viewport 才能让射线打到支撑面，但「城墙顶 / 垛 /
   门楼上层墙身」这类叠在墙上的构件，其承托件本身就是被隐藏的墙 —— 射线会穿过去
   打到地面，凭空报出 10 m 悬空。现在改用包围盒支撑判定（dump_bounds.py + audit_walls2.py）。

用法：
  blender -b palace_massing.blend -P tools/palace/audit_walls.py

输出（写到 $TEMP/palace_massing/）：
  wall_audit.csv     每段墙：名字 / 世界包围盒 / 底高 / 支撑命中统计 / 承托对象
  wall_audit.txt     人读报告
  wall_ends.csv      每个墙端的连接判定

做法：
1. 把所有「墙 / 垛」网格临时 hide_viewport，让 ray_cast 只打到支撑面（地面 / 台明 / 台基）。
   若不隐藏，从墙内部向下打必然先命中墙自己的底面，得到假的「已落地」。
2. 每段墙在底面上取 3×3 采样点，从 z_bot + 1.5 向下打射线，
   gap = z_bot - hit_z。gap <= 0 表示压在支撑里（正常），gap > 0.12 视为悬空。
3. 连接性：用世界平面矩形做空间哈希，逐端查「谁接住了这个端头」，
   分四类：wall（另一段墙）/ structure（殿身·台明·廊庑）/ gate（院门门楼）/ open（真断头）。
"""
import bpy
import json
import math
import os
import sys
import time
from collections import Counter, defaultdict
from mathutils import Vector

T0 = time.time()
WORK = os.path.join(os.environ.get("TEMP", "/tmp"), "palace_massing")
os.makedirs(WORK, exist_ok=True)

WALL_KEY = ("墙", "垛")          # 名字里含这些字即为「墙类」
GATE_KEY = ("院门", "门楼", "门洞", "大门")
STRUCT_KEY = ("台基", "台明", "廊", "殿", "宫", "殿身", "楼", "阁", "屋")

TOL_GAP = 0.12        # 底面与支撑面之间允许的空隙
TOL_TOUCH = 0.30      # 端头与别的实体「算接上」的平面距离


def name_of(ob):
    return ob.name


def world_bbox(ob):
    mw = ob.matrix_world
    cs = [mw @ Vector(c) for c in ob.bound_box]
    xs = [c.x for c in cs]
    ys = [c.y for c in cs]
    zs = [c.z for c in cs]
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


def is_wall(ob):
    n = ob.name
    if ob.type != "MESH":
        return False
    if not any(k in n for k in WALL_KEY):
        return False
    # 「栏板 / 围栏」不算墙
    if "栏" in n:
        return False
    return True


sc = bpy.context.scene
dg = bpy.context.evaluated_depsgraph_get()

walls = []
others = []
for ob in sc.objects:
    if ob.type != "MESH":
        continue
    bb = world_bbox(ob)
    rec = {"ob": ob, "name": ob.name, "bb": bb,
           "rot": abs(ob.matrix_world.to_euler().z)}
    if is_wall(ob):
        walls.append(rec)
    else:
        others.append(rec)
print("墙类 %d 段 / 非墙 %d 件 / %.1fs" % (len(walls), len(others), time.time() - T0))

# ---------------------------------------------------------------- 1. 隐藏墙，量落地
for w in walls:
    w["ob"].hide_viewport = True
dg = bpy.context.evaluated_depsgraph_get()
dg.update()
print("隐藏墙后 depsgraph 更新 %.1fs" % (time.time() - T0))

# 控制实验：随便挑一段墙，从它的底面上方往下打，看命中是不是它自己
_w = walls[0]
_x0, _x1, _y0, _y1, _z0, _z1 = _w["bb"]
_hit, _loc, _nrm, _idx, _obj, _m = sc.ray_cast(dg, Vector(((_x0 + _x1) / 2, (_y0 + _y1) / 2, _z1 + 2.0)), Vector((0, 0, -1)))
print("控制：%s 顶上方下打 → %s z=%.2f（自身 z_top=%.2f）"
      % (_w["name"], _obj.name if _obj else None, _loc.z if _hit else -999, _z1))


def ground_probe(x, y, z_bot):
    """返回 (gap, hit_name, hit_z)。从 z_bot+1.5 向下打。"""
    hit, loc, nrm, idx, ob, m = sc.ray_cast(
        dg, Vector((x, y, z_bot + 1.5)), Vector((0, 0, -1)), distance=400.0)
    if not hit:
        return (None, None, None)
    return (z_bot - loc.z, ob.name if ob else "?", loc.z)


for w in walls:
    x0, x1, y0, y1, z0, z1 = w["bb"]
    w["rot_deg"] = math.degrees(w["rot"])
    gaps = []
    hits = Counter()
    worst = (None, None, None)
    for i in range(3):
        for j in range(3):
            fx = 0.1 + 0.4 * i
            fy = 0.1 + 0.4 * j
            px = x0 + (x1 - x0) * fx
            py = y0 + (y1 - y0) * fy
            g, hn, hz = ground_probe(px, py, z0)
            gaps.append(g)
            if hn:
                hits[hn.split("·")[0]] += 1
            if g is not None:
                if worst[0] is None or g > worst[0]:
                    worst = (g, hn, hz)
    valid = [g for g in gaps if g is not None]
    w["gap_max"] = max(valid) if valid else None
    w["gap_min"] = min(valid) if valid else None
    w["n_hit"] = len(valid)
    w["n_void"] = 9 - len(valid)
    w["n_floating"] = sum(1 for g in valid if g > TOL_GAP)
    w["supports"] = dict(hits)
    w["worst"] = worst
print("落地探测完成 %.1fs" % (time.time() - T0))

# ---------------------------------------------------------------- 2. 连接性
# 空间哈希：所有实体（含墙）的世界平面矩形
CELL = 10.0
grid = defaultdict(list)
solid = []


def add_solid(rec, kind):
    x0, x1, y0, y1, z0, z1 = rec["bb"]
    rec["kind"] = kind
    rec["ix0"] = int(math.floor(x0 / CELL))
    rec["ix1"] = int(math.floor(x1 / CELL))
    rec["iy0"] = int(math.floor(y0 / CELL))
    rec["iy1"] = int(math.floor(y1 / CELL))
    rec["id"] = len(solid)
    solid.append(rec)


for w in walls:
    w["ob"].hide_viewport = False
    add_solid(w, "wall")
for o in others:
    n = o["name"]
    if any(k in n for k in GATE_KEY):
        k = "gate"
    elif any(k in n for k in STRUCT_KEY):
        k = "structure"
    else:
        k = "other"
    add_solid(o, k)
for rec in solid:
    for ix in range(rec["ix0"], rec["ix1"] + 1):
        for iy in range(rec["iy0"], rec["iy1"] + 1):
            grid[(ix, iy)].append(rec["id"])
print("空间哈希 %d 件 / %.1fs" % (len(solid), time.time() - T0))


def nearby(px, py, r=TOL_TOUCH + CELL):
    out = set()
    for ix in range(int(math.floor((px - r) / CELL)), int(math.floor((px + r) / CELL)) + 1):
        for iy in range(int(math.floor((py - r) / CELL)), int(math.floor((py + r) / CELL)) + 1):
            out.update(grid.get((ix, iy), ()))
    return out


def covers(rec, px, py, tol):
    x0, x1, y0, y1 = rec["bb"][:4]
    return (x0 - tol <= px <= x1 + tol) and (y0 - tol <= py <= y1 + tol)


ends = []
for w in walls:
    x0, x1, y0, y1, z0, z1 = w["bb"]
    along_x = (x1 - x0) >= (y1 - y0)
    for side, (pa, pb) in (("A", (x0, y0)), ("B", (x1, y1))):
        if along_x:
            ea, eb0, eb1 = (x0 if side == "A" else x1), y0, y1
        else:
            ea, eb0, eb1 = (y0 if side == "A" else y1), x0, x1
        probes = []
        for t in (0.3, 0.5, 0.7):
            v = eb0 + (eb1 - eb0) * t
            px, py = (ea - 0.05, v) if (along_x and side == "A") else \
                     (ea + 0.05, v) if along_x else \
                     (v, ea - 0.05) if side == "A" else (v, ea + 0.05)
            probes.append((px, py))
        kinds = Counter()
        who = Counter()
        for px, py in probes:
            for idx in nearby(px, py):
                r = solid[idx]
                if r["id"] == w["id"]:
                    continue
                # 高度上要真的在墙底附近有实体（-1 m .. +2 m 的带）
                if r["bb"][5] < z0 - 1.0 or r["bb"][4] > z0 + 2.0:
                    continue
                if covers(r, px, py, TOL_TOUCH):
                    kinds[r["kind"]] += 1
                    who[r["name"]] += 1
        best = "open"
        for k in ("wall", "gate", "structure"):
            if kinds.get(k, 0) >= 2:
                best = k
                break
        ends.append({"wall": w["name"], "side": side,
                     "x": (x0 + x1) / 2 if not along_x else (x0 if side == "A" else x1),
                     "y": (y0 + y1) / 2 if along_x else (y0 if side == "A" else y1),
                     "verdict": best, "kinds": dict(kinds),
                     "who": who.most_common(2)})
print("连接性判定完成 %.1fs" % (time.time() - T0))

# ---------------------------------------------------------------- 3. 输出
vc = Counter(e["verdict"] for e in ends)
print("\n===== 墙端连接构成 =====")
for k, v in vc.most_common():
    print("  %-10s %d" % (k, v))

floating = [w for w in walls if w["n_floating"] > 0 or w["n_void"] > 0]
print("\n===== 悬空墙 %d 段 =====" % len(floating))
for w in sorted(floating, key=lambda r: -(r["gap_max"] or 99))[:40]:
    print("  %-26s 底 z=%7.2f  top=%7.2f  gap_max=%s  悬空采样 %d/9  深度 %d/9  支撑=%s"
          % (w["name"], w["bb"][4], w["bb"][5],
             ("%.2f" % w["gap_max"]) if w["gap_max"] is not None else "∞",
             w["n_floating"], w["n_void"], w["supports"]))

open_ends = [e for e in ends if e["verdict"] == "open"]
print("\n===== 断头墙端 %d 个 =====" % len(open_ends))
for e in open_ends[:80]:
    print("  %-26s %s 端  (%8.1f, %8.1f)" % (e["wall"], e["side"], e["x"], e["y"]))

# 墙网络连通分量（仅墙-墙）
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


wid = {w["name"]: i for i, w in enumerate(walls)}
for e in ends:
    if e["verdict"] == "wall":
        for nm, _c in e["who"]:
            if nm in wid:
                union(wid[e["wall"]], wid[nm])
comp = Counter(find(i) for i in range(len(walls)))
print("\n===== 墙网络：%d 段墙 → %d 个连通块 =====" % (len(walls), len(comp)))
big = comp.most_common(8)
for root, n in big:
    names = [walls[i]["name"] for i in range(len(walls)) if find(i) == root][:4]
    print("  %4d 段  %s" % (n, " / ".join(names)))

# CSV
with open(os.path.join(WORK, "wall_audit.csv"), "w", encoding="utf-8") as f:
    f.write("name,x0,x1,y0,y1,z_bot,z_top,rot_deg,gap_min,gap_max,n_floating,n_void,supports\n")
    for w in walls:
        x0, x1, y0, y1, z0, z1 = w["bb"]
        f.write("%s,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.1f,%s,%s,%d,%d,%s\n" % (
            w["name"], x0, x1, y0, y1, z0, z1, w["rot_deg"],
            "" if w["gap_min"] is None else "%.3f" % w["gap_min"],
            "" if w["gap_max"] is None else "%.3f" % w["gap_max"],
            w["n_floating"], w["n_void"], "|".join(w["supports"])))

with open(os.path.join(WORK, "wall_ends.csv"), "w", encoding="utf-8") as f:
    f.write("wall,side,x,y,verdict,kinds,who\n")
    for e in ends:
        f.write("%s,%s,%.2f,%.2f,%s,%s,%s\n" % (
            e["wall"], e["side"], e["x"], e["y"], e["verdict"],
            json.dumps(e["kinds"], ensure_ascii=False),
            "|".join("%s" % n for n, _ in e["who"])))

with open(os.path.join(WORK, "wall_audit.json"), "w", encoding="utf-8") as f:
    json.dump({"walls": [{k: v for k, v in w.items() if k != "ob"} for w in walls],
               "ends": ends}, f, ensure_ascii=False, indent=1)

print("\nAUDIT_DONE %.1fs  %s" % (time.time() - T0, WORK))
