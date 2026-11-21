"""宫城（皇宫）3D 体量白模 —— Blender 5.x 无头脚本，数据全部取自 palace_data.py。

用法：
    blender -b --factory-startup -P build_massing.py -- --out <输出目录> [--samples 160] [--res 1920]

排布与 2D 同一套数据：外朝三殿同台、内廷后三宫、六宫各成院落、值房沿墙、内金水河五桥、四隅角楼。
产物：palace_massing.blend / palace_massing.glb / *.png
"""

import argparse
import json
import math
import os
import sys
import time

import bmesh
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import palace_data as D  # noqa: E402
import precise_lib as PL  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default=os.path.join(HERE, "..", "..", "docs", "assets"))
ap.add_argument("--samples", type=int, default=160)
ap.add_argument("--res", type=int, default=1920)
ap.add_argument("--only", default="", help="只渲染名字含该串的机位（其余跳过）")
ap.add_argument("--precise", action="store_true", help="用明官式构件库出精模（慢）")
args = ap.parse_args(argv)
WORK = os.path.join(os.environ.get("TEMP", HERE), "palace_massing")
os.makedirs(WORK, exist_ok=True)
os.makedirs(args.out, exist_ok=True)

P = D.PALACE
HW, HD = P["width"] / 2, P["depth"] / 2
T, H = P["wall_t"], P["wall_h"]
WH, WT = P["inner_wall_h"], P["inner_wall_t"]

# ------------------------------------------------------------------ 场景
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.unit_settings.system = "METRIC"
sc.unit_settings.scale_length = 1.0
col = sc.collection
if args.precise:
    PL.set_collection(col)
    PL.make_materials()


def material(name, rgb, rough=0.75, metal=0.0):
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
    "roof": material("琉璃黄", (0.70, 0.42, 0.045), 0.45),
    "roof2": material("琉璃黄·庑", (0.60, 0.37, 0.05), 0.5),
    "tile": material("青瓦", (0.26, 0.26, 0.25), 0.8),
    "wall": material("宫墙红", (0.42, 0.075, 0.06), 0.85),
    "citywall": material("城墙红", (0.38, 0.095, 0.075), 0.9),
    "stone": material("台基白", (0.66, 0.63, 0.55), 0.85),
    "platform": material("三台石", (0.62, 0.59, 0.51), 0.9),
    "ground": material("城外地面", (0.31, 0.30, 0.27), 0.95),
    "plaza": material("宫城地坪", (0.50, 0.47, 0.41), 0.95),
    "water": material("水面", (0.025, 0.09, 0.15), 0.06, 0.2),
    "green": material("绿地", (0.17, 0.27, 0.12), 0.95),
    "tree": material("树冠", (0.18, 0.30, 0.14), 0.9),
    "trunk": material("树干", (0.20, 0.14, 0.10), 0.9),
    "service": material("值房灰", (0.68, 0.66, 0.60), 0.9),
    "path": material("御道", (0.76, 0.73, 0.66), 0.9),
    "glass": material("现代玻璃", (0.16, 0.30, 0.40), 0.25, 0.15),
    "ridge": material("屋脊压顶", (0.32, 0.22, 0.09), 0.5),
    "rock": material("假山石", (0.45, 0.43, 0.39), 0.95),
}


def box(name, w, d, h, x, y, z0=0.0, mat=None):
    hx, hy, hz = w / 2, d / 2, h / 2
    cz = z0 + hz
    verts = [(x - hx, y - hy, cz - hz), (x + hx, y - hy, cz - hz),
             (x + hx, y + hy, cz - hz), (x - hx, y + hy, cz - hz),
             (x - hx, y - hy, cz + hz), (x + hx, y - hy, cz + hz),
             (x + hx, y + hy, cz + hz), (x - hx, y + hy, cz + hz)]
    faces = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1),
             (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    return mesh_from(name, verts, faces, mat)


def mesh_from(name, verts, faces, mat=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    if mat:
        ob.data.materials.append(mat)
    return ob


def hip_roof(name, w, d, h, x, y, z0, mat=None, overhang=3.0):
    mat = mat or MAT["roof"]
    w2, d2 = w + 2 * overhang, d + 2 * overhang
    v = [(-w2 / 2, -d2 / 2, 0), (w2 / 2, -d2 / 2, 0), (w2 / 2, d2 / 2, 0), (-w2 / 2, d2 / 2, 0)]
    if w2 >= d2:
        rl = max(w2 - d2, 0.16 * w2)
        v += [(-rl / 2, 0, h), (rl / 2, 0, h)]
        f = [(0, 1, 5, 4), (2, 3, 4, 5), (1, 2, 5), (3, 0, 4)]
        cap = [(x - rl / 2, y - 1.1, z0 + h), (x + rl / 2, y - 1.1, z0 + h),
               (x + rl / 2, y + 1.1, z0 + h), (x - rl / 2, y + 1.1, z0 + h)]
    else:
        rl = max(d2 - w2, 0.16 * d2)
        v += [(0, -rl / 2, h), (0, rl / 2, h)]
        f = [(1, 2, 5, 4), (3, 0, 4, 5), (0, 1, 4), (2, 3, 5)]
        cap = [(x - 1.1, y - rl / 2, z0 + h), (x + 1.1, y - rl / 2, z0 + h),
               (x + 1.1, y + rl / 2, z0 + h), (x - 1.1, y + rl / 2, z0 + h)]
    ob = mesh_from(name, [(x + a, y + b, z0 + c) for a, b, c in v], f, mat)
    if w2 >= d2 and w2 > 30:      # 正脊（小建筑不画）
        mesh_from(name + "_脊", cap + [(px, py, pz + 1.2) for px, py, pz in cap],
                  [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)],
                  MAT["ridge"])
    return ob


def gable_roof(name, w, d, h, x, y, z0, mat=None, overhang=2.2):
    mat = mat or MAT["roof"]
    w2, d2 = w + 2 * overhang, d + 2 * overhang
    swap = d2 > w2
    if swap:
        w2, d2 = d2, w2
    v = [(-w2 / 2, -d2 / 2, 0), (w2 / 2, -d2 / 2, 0), (w2 / 2, d2 / 2, 0), (-w2 / 2, d2 / 2, 0),
         (-w2 / 2, 0, h), (w2 / 2, 0, h)]
    f = [(0, 1, 5, 4), (3, 2, 5, 4), (0, 4, 3), (1, 2, 5)]
    if swap:
        v = [(b, a, c) for a, b, c in v]
    return mesh_from(name, [(x + a, y + b, z0 + c) for a, b, c in v], f, mat)


def pyramid_roof(name, w, d, h, x, y, z0, mat=None, overhang=2.6):
    mat = mat or MAT["roof"]
    w2, d2 = w + 2 * overhang, d + 2 * overhang
    v = [(-w2 / 2, -d2 / 2, 0), (w2 / 2, -d2 / 2, 0), (w2 / 2, d2 / 2, 0), (-w2 / 2, d2 / 2, 0),
         (0, 0, h)]
    f = [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)]
    return mesh_from(name, [(x + a, y + b, z0 + c) for a, b, c in v], f, mat)


def add_struct(s):
    z = s.get("z", 0.0)
    w, d, h = s["w"], s["d"], s["h"]
    x, y = s["cx"], s["cy"]
    kind = s["kind"]

    if s.get("base"):
        b = s["base"]
        box(s["name"] + "_台基", b["w"], b["d"], b["h"], x, y, z, MAT["stone"])
        z += b["h"]
    if s.get("terrace"):
        t = s["terrace"]
        box(s["name"] + "_月台", t["w"], t["d"], t["h"], x, t["cy"], s.get("z", 0.0), MAT["stone"])

    if kind == "gate":
        body = MAT["citywall"]
    elif kind == "modern":
        body = MAT["glass"]
    elif kind == "corridor":
        body = MAT["wall"]
    else:
        body = MAT["wall"]
    box(s["name"], w, d, h, x, y, z, body)

    top = z + h
    roof = s.get("roof", "hip")
    rmat = MAT[D.roof_mat_for(kind, w, d)]
    if roof == "hip":
        hip_roof(s["name"] + "_顶", w, d, max(0.22 * min(w, d) + 1.2, 3.2), x, y, top, rmat)
    elif roof == "gable":
        gable_roof(s["name"] + "_顶", w, d, max(0.26 * min(w, d) + 1.0, 2.4), x, y, top, rmat,
                   overhang=1.6 if kind == "corridor" else 2.2)
    elif roof == "pyramid":
        pyramid_roof(s["name"] + "_顶", w, d, max(0.30 * min(w, d) + 1.0, 3.0), x, y, top)
    elif roof == "flat":
        box(s["name"] + "_顶", w, d, 0.9, x, y, top, MAT["ridge"])

    if s.get("tower"):
        t = s["tower"]
        box(s["name"] + "_门楼", t["w"], t["d"], t["h"], x, y, top, MAT["wall"])
        tt = top + t["h"]
        rh = max(0.24 * min(t["w"], t["d"]) + 0.8, 2.4)
        if s.get("tower_roof") == "gable":
            gable_roof(s["name"] + "_门楼顶", t["w"], t["d"], rh, x, y, tt, overhang=1.8)
        else:
            hip_roof(s["name"] + "_门楼顶", t["w"], t["d"], rh, x, y, tt, overhang=1.8)
        top = tt


def add_wall(name, x0, x1, y0, y1, h=WH, mat=None):
    mat = mat or MAT["wall"]
    box(name, x1 - x0, y1 - y0, h, (x0 + x1) / 2, (y0 + y1) / 2, 0.0, mat)
    box(name + "_瓦", (x1 - x0) + 0.6, (y1 - y0) + 0.6, 0.5,
        (x0 + x1) / 2, (y0 + y1) / 2, h, MAT["ridge"])


# ------------------------------------------------------------------ 地面 / 护城河
box("城外地面", 3000, 3000, 0.4, 0, 0, -0.4, MAT["ground"])
box("宫城地坪", P["width"] + T, P["depth"] + T, 0.6, 0, 0, -0.3, MAT["plaza"])

mw = P["moat_w"]
for nm, (w_, d_, x_, y_) in {
    "南": (2 * (HW + T / 2 + mw), mw, 0, -HD - T / 2 - mw / 2),
    "北": (2 * (HW + T / 2 + mw), mw, 0, HD + T / 2 + mw / 2),
    "东": (mw, 2 * (HD + T / 2), HW + T / 2 + mw / 2, 0),
    "西": (mw, 2 * (HD + T / 2), -HW - T / 2 - mw / 2, 0),
}.items():
    box("护城河" + nm, w_, d_, 1.6, x_, y_, -1.2, MAT["water"])
    box("河岸" + nm, w_ + 3, d_ + 3, 0.35, x_, y_, -0.35, MAT["stone"])

# ------------------------------------------------------------------ 城墙
openings = {g["side"]: g["opening"] for g in D.GATES}


def wall_bar(name, w, d, x, y, along_x=True):
    box(name, w, d, H, x, y, 0.0, MAT["citywall"])
    box(name + "_顶", w + 1.2, d + 1.2, 0.7, x, y, H, MAT["ridge"])
    if args.precise:
        if along_x:
            PL.crenel_band(name + "_垛", x - w / 2, x + w / 2, y - d / 2 + 0.55, H + 0.7, along_x=True)
        else:
            PL.crenel_band(name + "_垛", y - d / 2, y + d / 2, x - w / 2 + 0.55, H + 0.7,
                           along_x=False)


for side, y in (("S", -HD), ("N", HD)):
    gw = openings[side]
    seg = HW + T / 2 - gw / 2
    wall_bar(f"城墙{side}1", seg, T, -(gw / 2 + seg / 2), y, along_x=True)
    wall_bar(f"城墙{side}2", seg, T, gw / 2 + seg / 2, y, along_x=True)
for side, x in (("E", HW), ("W", -HW)):
    gw = openings[side]
    seg = HD + T / 2 - gw / 2
    wall_bar(f"城墙{side}1", T, seg, x, -(gw / 2 + seg / 2), along_x=False)
    wall_bar(f"城墙{side}2", T, seg, x, gw / 2 + seg / 2, along_x=False)

ct = D.CORNER_TOWER
for sx in (-1, 1):
    for sy in (-1, 1):
        if args.precise:
            before = set(col.objects)
            PL.wall_tower("角楼", ct["w"], ct["d"], z=0.0, body_h=ct["h"])
            for ob in set(col.objects) - before:
                ob.location.x += sx * HW
                ob.location.y += sy * HD
        else:
            box("角楼", ct["w"], ct["d"], ct["h"], sx * HW, sy * HD, 0.0, MAT["citywall"])
            pyramid_roof("角楼顶", ct["w"], ct["d"], 5.0, sx * HW, sy * HD, ct["h"],
                         overhang=2.0)

# ------------------------------------------------------------------ 三台 / 院墙 / 河
def prism(name, poly, h, z0, mat):
    n = len(poly)
    verts = [(x, y, z0) for x, y in poly] + [(x, y, z0 + h) for x, y in poly]
    faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, j + n, i + n))
    return mesh_from(name, verts, faces, mat)


PL.make_materials()
prism("三台", D.PLATFORM_POLY, D.PLATFORM_H, 0.0, PL.MAT["stone2"])
PL.balustrade_line(-118, 118, -215.5, D.PLATFORM_H)
PL.balustrade_line(-60, 60, 11.5, D.PLATFORM_H)
PL.balustrade_line(-215, -110, 117.5, D.PLATFORM_H, along_x=False)
PL.balustrade_line(-215, -110, -117.5, D.PLATFORM_H, along_x=False)
PL.balustrade_line(-50, 10, 103.5, D.PLATFORM_H, along_x=False)
PL.balustrade_line(-50, 10, -103.5, D.PLATFORM_H, along_x=False)
for p in D.PLATFORMS:
    box(p["name"], p["w"], p["d"], p["h"], p["cx"], p["cy"], 0.0, MAT["platform"])

for w in D.inner_line_walls():
    add_wall(w["name"], w["x0"], w["x1"], w["y0"], w["y1"])
for c in D.COMPOUNDS:
    for w in D.compound_walls(c):
        add_wall(w["name"], w["x0"], w["x1"], w["y0"], w["y1"], h=WH)

R = D.RIVER
pts = R["points"]
half = R["width"] / 2
verts, faces = [], []
for i, (x, y) in enumerate(pts):
    if i == 0:
        dx, dy = pts[1][0] - x, pts[1][1] - y
    elif i == len(pts) - 1:
        dx, dy = x - pts[-2][0], y - pts[-2][1]
    else:
        dx, dy = pts[i + 1][0] - pts[i - 1][0], pts[i + 1][1] - pts[i - 1][1]
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L * half, dx / L * half
    verts += [(x + nx, y + ny, 0.12), (x - nx, y - ny, 0.12)]
for i in range(len(pts) - 1):
    a = i * 2
    faces.append((a, a + 1, a + 3, a + 2))
mesh_from("内金水河", verts, faces, MAT["water"])

# 御道
box("御道", 18, 900, 0.22, 0, -20, 0.02, MAT["path"])

# ------------------------------------------------------------------ 琼苑 / 值房 / 树
g = next(c for c in D.COMPOUNDS if c["name"] == "琼苑")
box("琼苑地面", g["x1"] - g["x0"] - 4, g["y1"] - g["y0"] - 4, 0.5,
    (g["x0"] + g["x1"]) / 2, (g["y0"] + g["y1"]) / 2, 0.25, MAT["green"])

for i, (cx, cy, w, d, hh) in enumerate(D.service_blocks()):
    if args.precise:
        before = set(col.objects)
        PL.small_house(f"值房{i:02d}", w, d, z=0.0, h=hh)
        for ob in set(col.objects) - before:
            ob.location.x += cx
            ob.location.y += cy
    else:
        box(f"值房{i:02d}", w, d, hh, cx, cy, 0.0, MAT["service"])
        gable_roof(f"值房{i:02d}_顶", w, d, 1.7, cx, cy, hh, MAT["tile"], overhang=0.9)

for i, (x, y) in enumerate(D.trees()):
    bpy.ops.mesh.primitive_cylinder_add(radius=0.45, depth=2.2, location=(x, y, 1.35))
    tr = bpy.context.object
    tr.data.materials.append(MAT["trunk"])
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=3.4, location=(x, y, 4.6))
    cr = bpy.context.object
    cr.scale = (1.0, 1.0, 0.85)
    cr.data.materials.append(MAT["tree"])

# ------------------------------------------------------------------ 单体
def add_struct_precise(st):
    w, d, h = st["w"], st["d"], st["h"]
    z = st.get("z", 0.0)
    base_h = st["base"]["h"] if st.get("base") else max(0.9, min(2.4, h * 0.16))
    k = st["kind"]
    x, y = st["cx"], st["cy"]
    if k == "gate":
        PL.gate_house(st["name"], w, d, z=z, h=h)
        return
    if k == "pavilion":
        for sx in (-1, 1):
            for sy in (-1, 1):
                PL.column(x + sx * (w / 2 - 0.7), y + sy * (d / 2 - 0.7), z, z + h, 0.20)
        PL.hip_roof(st["name"] + "·顶", w + 2.6, d + 2.6, z + h, max(2.4, h * 0.55), step=0.5)
        PL.ridges(w + 2.6, d + 2.6, z + h, max(2.4, h * 0.55), (w + 2.6) - (d + 2.6),
                 with_kiss=False)
        return
    storeys = 2 if (w >= 64 and h >= 11 and k in ("hall", "tower")) else 1
    lod = 2 if w >= 60 else (1 if w >= 34 else 0)
    n = max(3, int(round(w / 7)))
    m = max(3, int(round(d / 9)))
    before = set(col.objects)
    PL.hall(st["name"], w, d, bays=[w / n] * n, dbays=[d / m] * m, z=z, storeys=storeys,
            base_h=base_h, col_h=h * 0.92, plaque=("金瓯殿" if st["name"] == "金瓯殿" else None), lod=lod,
            stairs=(w >= 30), balustrade=(w >= 34))
    for ob in set(col.objects) - before:      # 构件库按原点建，整体挪到院落实位
        ob.location.x += x
        ob.location.y += y


print("BUILD structs", len(D.STRUCTS), flush=True)
for _i, s in enumerate(D.STRUCTS):
    if _i % 20 == 0:
        print("  struct", _i, s["name"], flush=True)
    if args.precise and s["kind"] in ("hall", "gate", "pavilion", "tower", "corridor"):
        if s["kind"] == "corridor":
            before = set(col.objects)
            PL.colonnade(s["name"], s["w"], s["d"], z=s.get("z", 0.0), h=min(4.8, s["h"] + 0.4))
            for ob in set(col.objects) - before:
                ob.location.x += s["cx"]
                ob.location.y += s["cy"]
        else:
            add_struct_precise(s)
        continue
    if s["kind"] == "rock":
        if args.precise:
            before = set(col.objects)
            PL.rockery(s["name"], s["w"], s["d"], s["h"], z=0.0)
            for ob in set(col.objects) - before:
                ob.location.x += s["cx"]
                ob.location.y += s["cy"]
        else:
            for k, (dx, dy, dz, sc_) in enumerate(((0, 0, 0, 1.0), (7, -4, 0.2, 0.62), (-6, 3, 0.1, 0.55))):
                b = box(f'{s["name"]}_{k}', s["w"] * sc_ * 0.8, s["d"] * sc_ * 0.9,
                        s["h"] * sc_, s["cx"] + dx, s["cy"] + dy, dz, MAT["rock"])
                b.rotation_euler[2] = math.radians(12 * k)
        continue
    if s["kind"] == "bridge":
        if args.precise:
            before = set(col.objects)
            PL.bridge(s["name"], s["w"], s["d"], z=-0.4)
            for ob in set(col.objects) - before:
                ob.location.x += s["cx"]
                ob.location.y += s["cy"]
        else:
            box(s["name"], s["w"], s["d"], s["h"], s["cx"], s["cy"], -0.4, MAT["stone"])
        continue
    add_struct(s)

# ------------------------------------------------------------------ 现代化改造（架空混合·推定）
if args.precise:
    glass = PL.MAT["glass"]
    metal = PL.MAT["metal"]
    # 金瓯殿南侧玻璃门厅 + 金属雨棚（三台前陛之下）
    box("改造·金瓯殿门厅", 26, 9, 4.2, 0, -236, 0.0, glass)
    box("改造·金瓯殿雨棚", 30, 11, 0.5, 0, -236, 4.2, metal)
    # 承天门内安检棚
    box("改造·安检棚", 14, 7, 3.4, 26, -448, 0.0, glass)
    box("改造·安检棚顶", 16, 9, 0.4, 26, -448, 3.4, metal)
    # 紫光阁现代附楼檐口（已有体块，加金属檐）
    box("改造·紫光阁附楼檐", 38, 58, 0.5, 330, -150, 9.0, metal)

# ------------------------------------------------------------------ 相机 / 灯光
cam_data = bpy.data.cameras.new("Cam")
cam_data.clip_start = 1.0
cam_data.clip_end = 40000.0
cam = bpy.data.objects.new("Cam", cam_data)
col.objects.link(cam)
sc.camera = cam


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


sun_d = bpy.data.lights.new("Sun", type="SUN")
sun_d.energy = 3.0
sun_d.angle = math.radians(4)
sun = bpy.data.objects.new("Sun", sun_d)
col.objects.link(sun)
sun.rotation_euler = (math.radians(33), 0, math.radians(232))

sc.world = bpy.data.worlds.new("World")
sc.world.use_nodes = True
bg = sc.world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.60, 0.72, 0.90, 1.0)
bg.inputs[1].default_value = 0.32

sc.render.engine = "CYCLES"
sc.cycles.device = "GPU"
sc.cycles.samples = args.samples
sc.cycles.use_denoising = True
sc.cycles.max_bounces = 6
sc.render.image_settings.file_format = "PNG"
sc.view_settings.view_transform = "Standard"
sc.view_settings.exposure = -0.2

# ------------------------------------------------------------------ 出图
AR = 16 / 9
shots = [
    ("鸟瞰·东南", dict(loc=(620, -760, 380), target=(0, -60, 0), lens=48)),
    ("鸟瞰·中轴", dict(loc=(90, -820, 175), target=(0, -70, 0), lens=58)),
    ("鸟瞰·内廷", dict(loc=(-520, -200, 380), target=(0, 120, 0), lens=50)),
    ("人视·金瓯殿", dict(loc=(178, -338, 24), target=(0, -150, 14), lens=42)),
    ("细部·外朝", dict(loc=(86, -320, 62), target=(0, -120, 20), lens=52)),
    ("正立面·正射", dict(loc=(0, -420, 34), target=(0, 0, 30), lens=0, ortho=108)),
]

results = {}
for name, s in shots:
    if args.only and args.only not in name:
        continue
    cam.location = s["loc"]
    if s.get("ortho"):
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = s["ortho"]
        cam.rotation_euler = (math.pi / 2, 0, 0)
    else:
        cam_data.type = "PERSP"
        cam_data.lens = s["lens"]
        look_at(cam, s["target"])
    sc.render.resolution_x = args.res
    sc.render.resolution_y = int(args.res / AR)
    path = os.path.join(WORK, f"massing_{name}.png")
    sc.render.filepath = path
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    results[name] = {"s": round(time.time() - t0, 1), "bytes": os.path.getsize(path)}
    print("RENDER", name, results[name])

if not args.only:
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = 1480
    cam.location = (0, 0, 4000)
    cam.rotation_euler = (0, 0, 0)
    sc.render.resolution_x, sc.render.resolution_y = (1400, 1780)
    path = os.path.join(WORK, "massing_正射总平面.png")
    sc.render.filepath = path
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    results["正射总平面"] = {"s": round(time.time() - t0, 1), "bytes": os.path.getsize(path)}
    cam_data.type = "PERSP"

# ------------------------------------------------------------------ 导出
blend = os.path.join(WORK, "palace_massing.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend)
glb = os.path.join(WORK, "palace_massing.glb")
bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", export_apply=True)
glb_lite = None
if args.precise:      # 轻量 glb：剔掉斗拱/值房/树/城墙等重复件，便于网页加载
    for ob in list(col.objects):
        if ob.name.split("·")[0].startswith(("斗拱", "值房", "树", "城墙", "角楼", "三台·望柱")):
            bpy.data.objects.remove(ob, do_unlink=True)
    for ob in col.objects:
        if ob.type == "MESH":
            dm = ob.modifiers.new("dec", "DECIMATE")
            dm.ratio = 0.28
    glb_lite = os.path.join(WORK, "palace_precise_lite.glb")
    bpy.ops.export_scene.gltf(filepath=glb_lite, export_format="GLB", export_apply=True)

tris = 0
for o in col.objects:
    if o.type == "MESH":
        o.data.calc_loop_triangles()
        tris += len(o.data.loop_triangles)

print("RESULT " + json.dumps({
    "renders": results, "objects": len(col.objects), "triangles": tris,
    "blend": blend, "glb": glb, "glb_mb": round(os.path.getsize(glb) / 1e6, 2),
}, ensure_ascii=False))
