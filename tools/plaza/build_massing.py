"""国家广场与广场建筑群 —— 3D 体量白模（Blender 5.x 无头）。

数据全部来自 plaza_data.py；坐标原点与宫城模型相同（宫城平面中心）。
本版是「白模」：体块、台基、柱廊、檐口、局部琉璃顶、绿化带与大街，
不做斗拱、隔扇、瓦垄、石材分缝——那些留到精模。

用法：
    blender -b --factory-startup -P build_massing.py -- \
        --out <输出目录> [--samples 64] [--res 1920] [--only 鸟瞰]

产物：
    <out>/国家广场(2026)·体量白模·*.png
    <out>/国家广场(2026)·体量白模.glb
    $TEMP/plaza_massing/plaza_massing.blend
"""

import argparse
import json
import math
import os
import random
import sys
import time

import bpy
import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import plaza_data as D  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default=os.path.join(HERE, "..", "..", "docs", "assets"))
ap.add_argument("--samples", type=int, default=64)
ap.add_argument("--res", type=int, default=1920)
ap.add_argument("--only", default="", help="只渲染名字含该串的机位")
ap.add_argument("--no-glb", action="store_true")
args = ap.parse_args(argv)

WORK = os.path.join(os.environ.get("TEMP", HERE), "plaza_massing")
os.makedirs(WORK, exist_ok=True)
os.makedirs(args.out, exist_ok=True)

# ------------------------------------------------------------------ 场景
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.unit_settings.system = "METRIC"
sc.unit_settings.scale_length = 1.0
col = sc.collection


def mat(name, rgb, rough=0.75, metal=0.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    return m


MAT = {
    "stone": mat("石·暖灰", (0.62, 0.59, 0.52), 0.85),
    "stone_light": mat("石·浅", (0.74, 0.71, 0.64), 0.85),
    "stone_dark": mat("石·深", (0.42, 0.40, 0.36), 0.9),
    "marble": mat("汉白玉", (0.82, 0.80, 0.74), 0.7),
    "glass": mat("玻璃", (0.08, 0.14, 0.17), 0.18, 0.15),
    "roof_tile": mat("琉璃·青", (0.16, 0.24, 0.20), 0.5),
    "roof_gold": mat("琉璃·金", (0.52, 0.36, 0.08), 0.45),
    "roof_flat": mat("平屋面", (0.36, 0.36, 0.34), 0.95),
    "lawn": mat("草地", (0.22, 0.33, 0.14), 0.95),
    "tree": mat("树冠", (0.18, 0.28, 0.12), 0.9),
    "trunk": mat("树干", (0.20, 0.14, 0.09), 0.95),
    "road": mat("沥青", (0.10, 0.10, 0.10), 0.95),
    "sidewalk": mat("人行道", (0.52, 0.50, 0.45), 0.9),
    "paving": mat("广场铺装", (0.64, 0.61, 0.54), 0.9),
    "paving_axis": mat("御道石", (0.74, 0.71, 0.64), 0.85),
    "water": mat("水面", (0.03, 0.09, 0.12), 0.06, 0.2),
    "wall_red": mat("宫墙红", (0.34, 0.06, 0.05), 0.85),
    "ground": mat("场外地面", (0.30, 0.29, 0.26), 0.95),
    "white": mat("灯柱白", (0.85, 0.84, 0.80), 0.6),
}


def link(ob):
    col.objects.link(ob)
    return ob


def mesh_object(name, verts, faces, material, smooth=False, recalc=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate()
    if recalc:
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
    me.update()
    ob = bpy.data.objects.new(name, me)
    if isinstance(material, (list, tuple)):
        for m in material:
            ob.data.materials.append(m)
    elif material:
        ob.data.materials.append(material)
    link(ob)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    return ob


def box(name, w, d, h, x, y, z0=0.0, material=None, rz=0.0):
    hw, hd = w / 2, d / 2
    verts = [(-hw, -hd, 0), (hw, -hd, 0), (hw, hd, 0), (-hw, hd, 0),
             (-hw, -hd, h), (hw, -hd, h), (hw, hd, h), (-hw, hd, h)]
    faces = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1),
             (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    ob = mesh_object(name, verts, faces, material)
    ob.location = (x, y, z0)
    ob.rotation_euler[2] = rz
    return ob


def cyl(name, r, h, x, y, z0=0.0, material=None, n=12):
    verts, faces = [], []
    for i in range(n):
        a = 2 * math.pi * i / n
        verts.append((r * math.cos(a), r * math.sin(a), 0))
    for i in range(n):
        a = 2 * math.pi * i / n
        verts.append((r * math.cos(a), r * math.sin(a), h))
    faces.append(tuple(range(n - 1, -1, -1)))
    faces.append(tuple(range(n, 2 * n)))
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    ob = mesh_object(name, verts, faces, material, smooth=True)
    ob.location = (x, y, z0)
    return ob


def hip_roof(name, w, d, h, x, y, z, material, overhang=4.0, ridge_mat=None):
    W, D = w + 2 * overhang, d + 2 * overhang
    hw, hd = W / 2, D / 2
    z0, z1 = 0.0, h
    if abs(W - D) < 1.0:                      # 攒尖
        verts = [(-hw, -hd, z0), (hw, -hd, z0), (hw, hd, z0), (-hw, hd, z0), (0, 0, z1)]
        faces = [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)]
    elif W > D:                                # 脊沿 X
        L = (W - D) / 2
        verts = [(-hw, -hd, z0), (hw, -hd, z0), (hw, hd, z0), (-hw, hd, z0),
                 (-L, 0, z1), (L, 0, z1)]
        faces = [(0, 1, 5, 4), (2, 3, 4, 5), (3, 0, 4), (1, 2, 5)]
    else:                                      # 脊沿 Y
        L = (D - W) / 2
        verts = [(-hw, -hd, z0), (hw, -hd, z0), (hw, hd, z0), (-hw, hd, z0),
                 (0, -L, z1), (0, L, z1)]
        faces = [(0, 1, 4), (1, 2, 5, 4), (2, 3, 5), (3, 0, 4, 5)]
    ob = mesh_object(name, verts, faces, material)
    ob.location = (x, y, z)
    # 檐口
    box(name + "·檐口", W + 0.6, D + 0.6, 0.55, x, y, z - 0.55, ridge_mat or MAT["stone_dark"])
    # 正脊
    if abs(W - D) >= 1.0:
        if W > D:
            box(name + "·正脊", W - D + 1.0, 0.9, 0.7, x, y, z + h - 0.7,
                ridge_mat or MAT["roof_gold"])
        else:
            box(name + "·正脊", 0.9, D - W + 1.0, 0.7, x, y, z + h - 0.7,
                ridge_mat or MAT["roof_gold"])
    else:
        box(name + "·宝顶", 1.2, 1.2, 1.2, x, y, z + h - 0.4, ridge_mat or MAT["roof_gold"])
    return ob


def flat_roof(name, w, d, x, y, z, material=None, parapet=1.6):
    box(name, w, d, 0.7, x, y, z, material or MAT["roof_flat"])
    t = 0.7
    for (ww, dd, xx, yy) in ((w, t, x, y - d / 2 + t / 2), (w, t, x, y + d / 2 - t / 2),
                             (t, d, x - w / 2 + t / 2, y), (t, d, x + w / 2 - t / 2, y)):
        box(name + "·女儿墙", ww, dd, parapet, xx, yy, z + 0.7, MAT["stone"])


def wall_segments(site, gates):
    """按门洞断开的院墙（3D）。"""
    x0, x1, y0, y1 = site["x0"], site["x1"], site["y0"], site["y1"]
    t, h, z = 1.5, 3.5, 0.12

    def cuts(side, lo, hi):
        spans = sorted((c - w / 2, c + w / 2) for sd, c, w in gates if sd == side)
        out, cur = [], lo
        for a, b in spans:
            if a > cur:
                out.append((cur, min(a, hi)))
            cur = max(cur, b)
        if cur < hi:
            out.append((cur, hi))
        return out

    for side, lo, hi, fixed in (("S", x0, x1, y0), ("N", x0, x1, y1)):
        for a, b in cuts(side, lo, hi):
            if b - a > 0.2:
                box(f"院墙·{side}", b - a, t, h, (a + b) / 2, fixed, z, MAT["stone"])
                box(f"院墙·{side}·压顶", b - a + 0.3, t + 0.5, 0.28,
                    (a + b) / 2, fixed, z + h, MAT["stone_dark"])
    for side, lo, hi, fixed in (("W", y0, y1, x0), ("E", y0, y1, x1)):
        for a, b in cuts(side, lo, hi):
            if b - a > 0.2:
                box(f"院墙·{side}", t, b - a, h, fixed, (a + b) / 2, z, MAT["stone"])
                box(f"院墙·{side}·压顶", t + 0.5, b - a + 0.3, 0.28,
                    fixed, (a + b) / 2, z + h, MAT["stone_dark"])
    # 门洞两侧门垛
    for side, c, w in gates:
        for s in (-1, 1):
            if side in ("E", "W"):
                xx = x1 if side == "E" else x0
                box(f"门垛·{side}", 2.2, 2.2, 5.2, xx, c + s * (w / 2 + 1.1), z, MAT["stone"])
            else:
                yy = y1 if side == "N" else y0
                box(f"门垛·{side}", 2.2, 2.2, 5.2, c + s * (w / 2 + 1.1), yy, z, MAT["stone"])


def glass_facade(name, length, h, fixed, axis, side, z0=3.0, spacing=12.0):
    """现代民族形式的石材柱廊＋玻璃幕墙（只做广场面）。"""
    if axis == "y":
        box(name + "·玻璃", 0.5, length - 16, h - 6, fixed, 0, z0, MAT["glass"])
    else:
        box(name + "·玻璃", length - 16, 0.5, h - 6, 0, fixed, z0, MAT["glass"])
    n = max(3, int(length / spacing))
    for i in range(n + 1):
        p = -length / 2 + i * (length / n)
        if axis == "y":
            box(name + f"·柱{i}", 1.7, 1.7, h - 2.5, fixed + side * 0.9, p, 0.15, MAT["stone_light"])
        else:
            box(name + f"·柱{i}", 1.7, 1.7, h - 2.5, p, fixed + side * 0.9, 0.15, MAT["stone_light"])


def portico(name, rect, h, facade_side):
    x0, x1, y0, y1 = rect
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w, d = x1 - x0, y1 - y0
    box(name + "·台", w + 3, d + 3, 1.1, cx, cy, 0.15, MAT["marble"])
    if facade_side in ("E", "W"):
        n = max(4, int(w / 8) + 1)
        ox = x1 - 1.0 if facade_side == "E" else x0 + 1.0
        for i in range(n):
            yy = y0 + 2 + i * (d - 4) / (n - 1)
            cyl(name + f"·柱{i}", 0.95, h - 2.5, ox, yy, 1.25, MAT["marble"], n=12)
        box(name + "·檐部", w, d + 1, 2.2, cx, cy, 1.25 + h - 2.5, MAT["stone_light"])
        box(name + "·顶", w + 1, d + 1, 0.7, cx, cy, 1.25 + h - 0.3, MAT["stone_light"])
    else:
        n = max(4, int(w / 8) + 1)
        oy = y1 - 1.0 if facade_side == "N" else y0 + 1.0
        for i in range(n):
            xx = x0 + 2 + i * (w - 4) / (n - 1)
            cyl(name + f"·柱{i}", 0.95, h - 2.5, xx, oy, 1.25, MAT["marble"], n=12)
        box(name + "·檐部", w + 1, d, 2.2, cx, cy, 1.25 + h - 2.5, MAT["stone_light"])
        box(name + "·顶", w + 1, d + 1, 0.7, cx, cy, 1.25 + h - 0.3, MAT["stone_light"])


def steps(name, cx, cy, w, side, depth=8.0, n=3):
    for i in range(n):
        h = (i + 1) * 0.36
        dd = depth * (n - i) / n
        if side == "E":
            box(f"{name}·踏步{i}", dd, w, h, cx + dd / 2, cy, 0.15, MAT["marble"])
        elif side == "W":
            box(f"{name}·踏步{i}", dd, w, h, cx - dd / 2, cy, 0.15, MAT["marble"])
        elif side == "N":
            box(f"{name}·踏步{i}", w, dd, h, cx, cy + dd / 2, 0.15, MAT["marble"])
        else:
            box(f"{name}·踏步{i}", w, dd, h, cx, cy - dd / 2, 0.15, MAT["marble"])


# ------------------------------------------------------------------ 地面 / 广场
GW, GD = 2600.0, 2800.0
GY = -1100.0
box("场外地面", GW, GD, 0.2, 0, GY, -0.2, MAT["ground"])

# 承天门大街
A = D.AVENUE
box("大街·车行道", A["x1"] - A["x0"], A["width"] - 2 * A["sidewalk"], 0.10,
    (A["x0"] + A["x1"]) / 2, (A["y_north"] + A["y_south"]) / 2, 0.02, MAT["road"])
for yy, nm in ((A["y_north"] - A["sidewalk"] / 2, "北人行道"),
               (A["y_south"] + A["sidewalk"] / 2, "南人行道")):
    box(f"大街·{nm}", A["x1"] - A["x0"], A["sidewalk"], 0.22,
        (A["x0"] + A["x1"]) / 2, yy, 0.02, MAT["sidewalk"])
yc = (A["y_north"] + A["y_south"]) / 2
box("大街·中央分隔带", A["x1"] - A["x0"], A["median"], 0.30,
    (A["x0"] + A["x1"]) / 2, yc, 0.02, MAT["lawn"])
box("大街·轴心过街", 40.0, A["width"], 0.26, 0, yc, 0.02, MAT["paving_axis"])
# 车道虚线
for k, dy in enumerate((-24.0, -10.5, 10.5, 24.0)):
    x = A["x0"] + 6
    while x < A["x1"] - 6:
        box(f"车道线·{k}", 7.0, 0.35, 0.12, x, yc + dy, 0.12, MAT["white"])
        x += 18.0

# 广场铺装
P = D.PLAZA
box("广场铺装", P["width"], P["depth"], 0.16, 0, (P["y_north"] + P["y_south"]) / 2,
    0.02, MAT["paving"])
box("中轴御道", 40.0, P["depth"], 0.22, 0, (P["y_north"] + P["y_south"]) / 2,
    0.02, MAT["paving_axis"])
e = D.FEATURES["east_road"]
box("广场东侧道", e["x1"] - e["x0"], e["y1"] - e["y0"], 0.20,
    (e["x0"] + e["x1"]) / 2, (e["y0"] + e["y1"]) / 2, 0.02, MAT["sidewalk"])

# 周边道路
for r in D.ROADS:
    box("周边道路", r["x1"] - r["x0"], r["y1"] - r["y0"], 0.10,
        (r["x0"] + r["x1"]) / 2, (r["y0"] + r["y1"]) / 2, 0.02, MAT["road"])

# 护城河、桥、宫城南墙、承天门
PW = D.PALACE
hw = PW["width"] / 2
box("护城河·南", 2 * (hw + 55), PW["moat_w"], 0.3, 0, -509.5, -0.05, MAT["water"])
b = D.FEATURES["bridge"]
box("承天门桥", b["x1"] - b["x0"], b["y1"] - b["y0"], b["h"],
    (b["x0"] + b["x1"]) / 2, (b["y0"] + b["y1"]) / 2, 0.25, MAT["stone_light"])
for x in (-47.5, 47.5):
    box("承天门桥·栏板", 1.2, b["y1"] - b["y0"], 1.1, x, (b["y0"] + b["y1"]) / 2,
        0.25 + b["h"], MAT["marble"])
box("宫城南墙", 2 * (hw + 3), PW["wall_t"], 10.0, 0, PW["south_wall_face"], 0.1, MAT["wall_red"])
box("宫城南墙·压顶", 2 * (hw + 3) + 0.8, PW["wall_t"] + 0.6, 0.5, 0,
    PW["south_wall_face"], 10.1, MAT["stone_dark"])
g = PW["gate"]
box("承天门·城台", g["w"], g["d"], 12.0, 0, g["cy"], 0.1, MAT["wall_red"])
r = D.FEATURES["review"]
box("承天门·阅兵台", r["x1"] - r["x0"], r["y1"] - r["y0"], r["h"],
    0, (r["y0"] + r["y1"]) / 2, 12.1, MAT["stone_light"])
box("承天门·城楼", 62, 26, 13.0, 0, g["cy"], 12.1, MAT["wall_red"])
hip_roof("承天门·城楼顶", 62, 26, 6.0, 0, g["cy"], 25.1, MAT["roof_gold"], overhang=5)
for sx in (-1, 1):
    box("承天门·雁翅楼", 38, 20, 11.0, sx * 62, -497, 0.1, MAT["wall_red"])
    hip_roof("承天门·雁翅楼顶", 38, 20, 4.2, sx * 62, -497, 11.1, MAT["roof_gold"], overhang=3)

# ------------------------------------------------------------------ 建筑群
SITES = {s["key"]: s for s in D.SITES}
for s in D.SITES:
    box(f'{s["key"]}·草地', s["x1"] - s["x0"] - 4, s["y1"] - s["y0"] - 4, 0.25,
        (s["x0"] + s["x1"]) / 2, (s["y0"] + s["y1"]) / 2, 0.05, MAT["lawn"])
    wall_segments(s, D.GATES.get(s["key"], []))


def plinth(name, w, d, x, y, h=2.2):
    box(name + "·台基", w, d, h, x, y, 0.12, MAT["marble"])
    box(name + "·台基压顶", w + 0.8, d + 0.8, 0.3, x, y, 0.12 + h - 0.3, MAT["stone_light"])


# 大会堂：230 × 600，三段式
HX, HY = -425.0, -1035.5
plinth("大会堂", 238, 608, HX, HY)
for m in D.MASSES:
    if m["parent"] != "hall" or m["kind"] == "portico":
        continue
    cx, cy = (m["x0"] + m["x1"]) / 2, (m["y0"] + m["y1"]) / 2
    w, d, h = m["x1"] - m["x0"], m["y1"] - m["y0"], m["h"]
    box("大会堂·" + m["name"], w, d, h - 2.3, cx, cy, 2.3, MAT["stone"])
    glass_facade("大会堂·" + m["name"], d, h, m["x1"], "y", 1)
    if m["kind"] == "chamber":
        hip_roof("大会堂·中厅顶", w, d, 7.0, cx, cy, h + 0.15, MAT["roof_tile"], overhang=4)
    else:
        flat_roof("大会堂·" + m["name"] + "顶", w, d, cx, cy, h + 0.15)
for m in D.MASSES:
    if m["parent"] == "hall" and m["kind"] == "portico":
        portico("大会堂·" + m["name"], (m["x0"], m["x1"], m["y0"], m["y1"]), 20)
        steps("大会堂·" + m["name"], m["x1"], (m["y0"] + m["y1"]) / 2, m["y1"] - m["y0"], "E")

# 议事大楼：同大外框，一整块基座 + 中央高体量
CX, CY = 425.0, -1035.5
plinth("议事大楼", 238, 608, CX, CY)
box("议事大楼·基座", 230, 600, 23.7, CX, CY, 2.3, MAT["stone"])
glass_facade("议事大楼·基座", 600, 26, 310, "y", -1)
flat_roof("议事大楼·基座顶", 230, 600, CX, CY, 26.15)
box("议事大楼·议事厅", 160, 160, 31.7, CX, CY, 2.3, MAT["stone"])
for i in range(10):
    box(f"议事大楼·议事厅竖窗{i}", 0.4, 150, 27, 344.6, CY, 4.5, MAT["glass"])
hip_roof("议事大楼·议事厅顶", 160, 160, 8.0, CX, CY, 34.15, MAT["roof_tile"], overhang=4)
for m in D.MASSES:
    if m["parent"] == "council" and m["kind"] == "portico":
        portico("议事大楼·" + m["name"], (m["x0"], m["x1"], m["y0"], m["y1"]), 20)
        steps("议事大楼·" + m["name"], m["x0"], (m["y0"] + m["y1"]) / 2, m["y1"] - m["y0"], "W")

# 博物馆：560 × 170
MX, MY = 0.0, -1535.5
plinth("博物馆", 568, 178, MX, MY)
box("博物馆·主体", 560, 170, 21.7, MX, MY, 2.3, MAT["stone"])
glass_facade("博物馆·主体", 560, 24, -1450.5, "x", -1)
flat_roof("博物馆·主体顶", 560, 170, MX, MY, 24.15)
hip_roof("博物馆·中段顶", 240, 170, 6.0, MX, MY, 24.15, MAT["roof_tile"], overhang=4)
m = next(x for x in D.MASSES if x["key"] == "museum-portico")
portico("博物馆·门廊", (m["x0"], m["x1"], m["y0"], m["y1"]), 18)
steps("博物馆·门廊", 0, m["y0"], m["x1"] - m["x0"], "N")

# ------------------------------------------------------------------ 绿化树
def tree_mesh():
    verts, faces, mids = [], [], []

    def add_cyl(r, h, z, n=8):
        base = len(verts)
        for i in range(n):
            a = 2 * math.pi * i / n
            verts.append((r * math.cos(a), r * math.sin(a), z))
        for i in range(n):
            a = 2 * math.pi * i / n
            verts.append((r * math.cos(a), r * math.sin(a), z + h))
        faces.append(tuple(base + i for i in range(n - 1, -1, -1)))
        faces.append(tuple(base + n + i for i in range(n)))
        for i in range(n):
            j = (i + 1) % n
            faces.append((base + i, base + j, base + n + j, base + n + i))
            mids.append(0)

    add_cyl(0.55, 3.0, 0.0)

    def add_sphere(r, z, rings=5, segs=8):
        base = len(verts)
        verts.append((0, 0, z + r))
        for ri in range(1, rings):
            phi = math.pi * ri / rings
            zz = z + r * math.cos(phi)
            rr = r * math.sin(phi)
            for si in range(segs):
                a = 2 * math.pi * si / segs
                verts.append((rr * math.cos(a), rr * math.sin(a), zz))
        verts.append((0, 0, z - r))
        top, bot = base, base + 1 + (rings - 1) * segs
        for si in range(segs):
            faces.append((top, base + 1 + si, base + 1 + (si + 1) % segs))
            mids.append(1)
        for ri in range(rings - 2):
            for si in range(segs):
                a0 = base + 1 + ri * segs + si
                a1 = base + 1 + ri * segs + (si + 1) % segs
                b0 = a0 + segs
                b1 = a1 + segs
                faces.append((a0, b0, b1, a1))
                mids.append(1)
        for si in range(segs):
            faces.append((bot, base + 1 + (rings - 2) * segs + (si + 1) % segs,
                          base + 1 + (rings - 2) * segs + si))
            mids.append(1)

    add_sphere(3.6, 5.2)
    add_sphere(2.6, 8.2)
    me = bpy.data.meshes.new("Tree")
    me.from_pydata(verts, [], faces)
    me.validate()
    me.update()
    ob = bpy.data.objects.new("Tree", me)
    ob.data.materials.append(MAT["trunk"])
    ob.data.materials.append(MAT["tree"])
    for i, p in enumerate(me.polygons):
        p.material_index = mids[i] if i < len(mids) else 1
    return ob


tree_base = tree_mesh()
TREE_COUNT = 0
for s in D.SITES:
    gates = D.GATES.get(s["key"], [])
    x0, x1, y0, y1 = s["x0"] + 6, s["x1"] - 6, s["y0"] + 6, s["y1"] - 6

    def skip(pos, side):
        for sd, c, w in gates:
            if sd == side and abs(pos - c) < w / 2 + 2:
                return True
        return False

    positions = []
    y = y0
    while y <= y1:
        if not skip(y, "E"):
            positions.append((x1, y))
        if not skip(y, "W"):
            positions.append((x0, y))
        y += 24
    x = x0 + 12
    while x <= x1 - 12:
        if not skip(x, "N"):
            positions.append((x, y1))
        if not skip(x, "S"):
            positions.append((x, y0))
        x += 24
    for i, (px, py) in enumerate(positions):
        ob = bpy.data.objects.new(f"树·{s['key']}·{i}", tree_base.data)
        ob.location = (px, py, 0.15)
        sc_ = random.uniform(0.85, 1.15)
        ob.scale = (sc_, sc_, sc_)
        ob.rotation_euler[2] = random.uniform(0, math.pi * 2)
        link(ob)
        TREE_COUNT += 1

# ------------------------------------------------------------------ 灯光 / 相机
sun_d = bpy.data.lights.new("Sun", type="SUN")
sun_d.energy = 3.2
sun_d.angle = math.radians(3)
sun = bpy.data.objects.new("Sun", sun_d)
link(sun)
sun.rotation_euler = (math.radians(35), 0, math.radians(232))

sc.world = bpy.data.worlds.new("World")
sc.world.use_nodes = True
bg = sc.world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.56, 0.68, 0.86, 1.0)
bg.inputs[1].default_value = 0.55

cam_data = bpy.data.cameras.new("Cam")
cam_data.clip_start = 1.0
cam_data.clip_end = 40000.0
cam = bpy.data.objects.new("Cam", cam_data)
link(cam)
sc.camera = cam


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


sc.render.engine = "CYCLES"
sc.cycles.device = "GPU"
sc.cycles.samples = args.samples
sc.cycles.use_denoising = True
sc.cycles.max_bounces = 4
sc.render.image_settings.file_format = "PNG"
sc.view_settings.view_transform = "Standard"
sc.view_settings.exposure = -0.10

# ------------------------------------------------------------------ 出图
AR = 16 / 9
shots = [
    ("鸟瞰东南", dict(loc=(980, -2280, 880), target=(0, -980, 0), lens=50)),
    ("中轴", dict(loc=(0, -1920, 105), target=(0, -760, 30), lens=34)),
    ("西望大会堂", dict(loc=(360, -1035, 78), target=(-430, -1035, 30), lens=45)),
    ("东望议事楼", dict(loc=(-360, -1035, 78), target=(430, -1035, 30), lens=45)),
    ("南望博物馆", dict(loc=(0, -820, 68), target=(0, -1560, 26), lens=45)),
    ("人视承天门", dict(loc=(0, -770, 1.7), target=(0, -480, 20), lens=38)),
]

results = {}
for name, s in shots:
    if args.only and args.only not in name:
        continue
    cam.location = s["loc"]
    cam_data.type = "PERSP"
    cam_data.lens = s["lens"]
    look_at(cam, s["target"])
    sc.render.resolution_x = args.res
    sc.render.resolution_y = int(args.res / AR)
    path = os.path.join(args.out, f"国家广场(2026)·体量白模·{name}.png")
    sc.render.filepath = path
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    results[name] = round(time.time() - t0, 1)
    print("RENDER", name, results[name], flush=True)

# ------------------------------------------------------------------ 保存 / 导出
blend = os.path.join(WORK, "plaza_massing.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend)
glb = os.path.join(args.out, "国家广场(2026)·体量白模.glb")
if not args.no_glb:
    bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", export_apply=True)

tris = 0
for o in col.objects:
    if o.type == "MESH":
        o.data.calc_loop_triangles()
        tris += len(o.data.loop_triangles)

print("RESULT " + json.dumps({
    "renders": results, "objects": len(col.objects), "triangles": tris,
    "trees": TREE_COUNT, "blend": blend, "glb": glb,
    "glb_mb": round(os.path.getsize(glb) / 1e6, 2) if os.path.exists(glb) else None,
}, ensure_ascii=False))
