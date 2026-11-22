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
ap.add_argument("--precise", action="store_true", help="精模：加石材分缝、柱头、竖梃、门、瓦面与戗脊")
args = ap.parse_args(argv)
P = args.precise

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
    "stone": mat("石·暖灰", (0.44, 0.42, 0.37), 0.85),
    "stone_light": mat("石·浅", (0.68, 0.66, 0.60), 0.85),
    "stone_dark": mat("石·深", (0.26, 0.25, 0.23), 0.9),
    "marble": mat("汉白玉", (0.82, 0.80, 0.74), 0.7),
    "glass": mat("玻璃", (0.02, 0.035, 0.045), 0.25, 0.2),
    "roof_tile": mat("琉璃·青", (0.06, 0.10, 0.085), 0.45),
    "roof_gold": mat("琉璃·金", (0.52, 0.36, 0.08), 0.45),
    "roof_flat": mat("平屋面", (0.15, 0.15, 0.14), 0.95),
    "lawn": mat("草地", (0.22, 0.33, 0.14), 0.95),
    "tree": mat("树冠", (0.18, 0.28, 0.12), 0.9),
    "trunk": mat("树干", (0.20, 0.14, 0.09), 0.95),
    "road": mat("沥青", (0.10, 0.10, 0.10), 0.95),
    "sidewalk": mat("人行道", (0.52, 0.50, 0.45), 0.9),
    "paving": mat("广场铺装", (0.52, 0.50, 0.44), 0.9),
    "paving_axis": mat("御道石", (0.69, 0.66, 0.58), 0.85),
    "water": mat("水面", (0.03, 0.09, 0.12), 0.06, 0.2),
    "wall_red": mat("宫墙红", (0.34, 0.06, 0.05), 0.85),
    "ground": mat("场外地面", (0.22, 0.21, 0.19), 0.95),
    "white": mat("灯柱白", (0.85, 0.84, 0.80), 0.6),
    "metal": mat("深色金属", (0.055, 0.050, 0.045), 0.35, 0.75),
    "door": mat("入口门", (0.035, 0.030, 0.025), 0.4, 0.35),
}



def panel_texture(m, bw=1.2, bh=0.6, mortar=0.012, c1=(0.44, 0.42, 0.37),
                  c2=(0.40, 0.38, 0.34), mc=(0.20, 0.19, 0.17), bump=0.02):
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.inputs["Scale"].default_value = 1.0
    br.inputs["Brick Width"].default_value = bw
    br.inputs["Row Height"].default_value = bh
    br.inputs["Mortar Size"].default_value = mortar
    br.inputs["Color1"].default_value = (*c1, 1.0)
    br.inputs["Color2"].default_value = (*c2, 1.0)
    br.inputs["Mortar"].default_value = (*mc, 1.0)
    nt.links.new(tc.outputs["Object"], br.inputs["Vector"])
    nt.links.new(br.outputs["Color"], bsdf.inputs["Base Color"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = bump
    nt.links.new(br.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], bsdf.inputs["Normal"])



def tile_texture(m):
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    wv = nt.nodes.new("ShaderNodeTexWave")
    wv.wave_type = "BANDS"
    wv.bands_direction = "X"
    wv.inputs["Scale"].default_value = 2.9
    wv.inputs["Distortion"].default_value = 0.25
    wv.inputs["Detail"].default_value = 2.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.025, 0.05, 0.04, 1.0)
    ramp.color_ramp.elements[1].color = (0.10, 0.16, 0.13, 1.0)
    nt.links.new(tc.outputs["Object"], wv.inputs["Vector"])
    nt.links.new(wv.outputs["Fac"], ramp.inputs[0])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.10
    nt.links.new(wv.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], bsdf.inputs["Normal"])


def link(ob):
    col.objects.link(ob)
    return ob


if P:
    panel_texture(MAT["stone"], 2.4, 1.2, 0.025, (0.47, 0.45, 0.40), (0.37, 0.35, 0.31), (0.10, 0.09, 0.08), 0.03)
    panel_texture(MAT["marble"], 2.4, 1.2, 0.020, (0.82, 0.80, 0.74), (0.74, 0.72, 0.66), (0.30, 0.29, 0.27), 0.025)
    panel_texture(MAT["paving"], 2.4, 1.2, 0.020, (0.54, 0.52, 0.46), (0.46, 0.44, 0.39), (0.26, 0.25, 0.23), 0.02)
    tile_texture(MAT["roof_tile"])


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


def beam3d(name, p0, p1, w, h, material):
    a, b = Vector(p0), Vector(p1)
    d = b - a
    ob = box(name, d.length, w, h, (a.x + b.x) / 2, (a.y + b.y) / 2, (a.z + b.z) / 2, material)
    ob.rotation_euler = d.to_track_quat("X", "Z").to_euler()
    return ob


def hip_roof(name, w, d, h, x, y, z, material, overhang=4.0, ridge_mat=None, front=None):
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
    if P:
        hw, hd = W / 2, D / 2
        z0, z1 = z, z + h
        if abs(W - D) < 1.0:
            apex = (x, y, z1)
            hips = [((x - hw, y - hd, z0), apex), ((x + hw, y - hd, z0), apex),
                    ((x + hw, y + hd, z0), apex), ((x - hw, y + hd, z0), apex)]
        elif W > D:
            L = (W - D) / 2
            hips = [((x - hw, y - hd, z0), (x - L, y, z1)), ((x + hw, y - hd, z0), (x + L, y, z1)),
                    ((x - hw, y + hd, z0), (x - L, y, z1)), ((x + hw, y + hd, z0), (x + L, y, z1))]
        else:
            L = (D - W) / 2
            hips = [((x - hw, y - hd, z0), (x, y - L, z1)), ((x + hw, y - hd, z0), (x, y - L, z1)),
                    ((x - hw, y + hd, z0), (x, y + L, z1)), ((x + hw, y + hd, z0), (x, y + L, z1))]
        for i, (p0, p1) in enumerate(hips):
            beam3d("戗脊·" + str(i), p0, p1, 0.9, 0.55, ridge_mat or MAT["roof_gold"])
        if abs(W - D) >= 1.0:
            if W > D:
                for sx in (-1, 1):
                    box("正脊端·" + str(sx), 1.6, 1.6, 2.2, x + sx * L, y, z1 - 0.6, MAT["roof_gold"])
            else:
                for sy in (-1, 1):
                    box("正脊端·" + str(sy), 1.6, 1.6, 2.2, x, y + sy * L, z1 - 0.6, MAT["roof_gold"])
        if front in ("E", "W"):
            xe = x + (W / 2 if front == "E" else -W / 2)
            sg = 1 if front == "E" else -1
            n = max(6, int(D / 0.45))
            for i in range(n):
                yy = y - D / 2 + (i + 0.5) * D / n
                box("檐椽", 0.55, 0.12, 0.14, xe + sg * 0.30, yy, z - 1.25, MAT["trunk"])
                box("瓦当", 0.18, 0.14, 0.22, xe + sg * 0.04, yy, z + 0.02, MAT["roof_tile"])
        elif front in ("N", "S"):
            ye = y + (D / 2 if front == "N" else -D / 2)
            sg = 1 if front == "N" else -1
            n = max(6, int(W / 0.45))
            for i in range(n):
                xx = x - W / 2 + (i + 0.5) * W / n
                box("檐椽", 0.12, 0.55, 0.14, xx, ye + sg * 0.30, z - 1.25, MAT["trunk"])
                box("瓦当", 0.14, 0.18, 0.22, xx, ye + sg * 0.04, z + 0.02, MAT["roof_tile"])
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
                box(f"院墙·{side}", b - a, t, h, (a + b) / 2, fixed, z, MAT["stone_dark"])
                box(f"院墙·{side}·压顶", b - a + 0.3, t + 0.5, 0.28,
                    (a + b) / 2, fixed, z + h, MAT["stone_dark"])
    for side, lo, hi, fixed in (("W", y0, y1, x0), ("E", y0, y1, x1)):
        for a, b in cuts(side, lo, hi):
            if b - a > 0.2:
                box(f"院墙·{side}", t, b - a, h, fixed, (a + b) / 2, z, MAT["stone_dark"])
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




def emblem(name, axis, fixed, center, z, side):
    if axis == "x":
        red = cyl(name + "·底盘", 6.0, 0.35, 0, 0, 0, MAT["wall_red"], n=24)
        red.rotation_euler = (0, math.pi / 2, 0)
        red.location = (fixed + side * 0.15, center, z)
        gold = cyl(name + "·金徽", 4.6, 0.45, 0, 0, 0, MAT["roof_gold"], n=24)
        gold.rotation_euler = (0, math.pi / 2, 0)
        gold.location = (fixed + side * 0.45, center, z)
    else:
        red = cyl(name + "·底盘", 6.0, 0.35, 0, 0, 0, MAT["wall_red"], n=24)
        red.rotation_euler = (math.pi / 2, 0, 0)
        red.location = (center, fixed + side * 0.15, z)
        gold = cyl(name + "·金徽", 4.6, 0.45, 0, 0, 0, MAT["roof_gold"], n=24)
        gold.rotation_euler = (math.pi / 2, 0, 0)
        gold.location = (center, fixed + side * 0.45, z)


def rail_edge(name, axis, fixed, lo, hi, gaps, z0=2.32):
    segs, cur = [], lo
    for a, b in sorted(gaps):
        if a > cur:
            segs.append((cur, min(a, hi)))
        cur = max(cur, b)
    if cur < hi:
        segs.append((cur, hi))
    for si, (a, b) in enumerate(segs):
        if b - a < 1.0:
            continue
        L = b - a
        if axis == "y":
            box(name + f"·栏板{si}", 0.35, L, 0.55, fixed, (a + b) / 2, z0 + 0.55, MAT["marble"])
            box(name + f"·寻杖{si}", 0.24, L, 0.18, fixed, (a + b) / 2, z0 + 1.03, MAT["marble"])
            n = max(2, int(L / 6.0) + 1)
            for i in range(n):
                yy = a + i * L / (n - 1)
                box(name + f"·望柱{si}-{i}", 0.45, 0.45, 1.15, fixed, yy, z0, MAT["marble"])
            for i in range(n - 1):
                yy = a + (i + 0.5) * L / (n - 1)
                cyl(name + f"·净瓶{si}-{i}", 0.15, 0.42, fixed, yy, z0 + 0.55, MAT["marble"], n=10)
            for k, yy in ((0, a), (1, b)):
                box(name + f"·螭首{si}-{k}", 0.55, 0.65, 0.42, fixed, yy, z0 + 0.95, MAT["marble"])
        else:
            box(name + f"·栏板{si}", L, 0.35, 0.55, (a + b) / 2, fixed, z0 + 0.55, MAT["marble"])
            box(name + f"·寻杖{si}", L, 0.24, 0.18, (a + b) / 2, fixed, z0 + 1.03, MAT["marble"])
            n = max(2, int(L / 6.0) + 1)
            for i in range(n):
                xx = a + i * L / (n - 1)
                box(name + f"·望柱{si}-{i}", 0.45, 0.45, 1.15, xx, fixed, z0, MAT["marble"])
            for i in range(n - 1):
                xx = a + (i + 0.5) * L / (n - 1)
                cyl(name + f"·净瓶{si}-{i}", 0.15, 0.42, xx, fixed, z0 + 0.55, MAT["marble"], n=10)
            for k, xx in ((0, a), (1, b)):
                box(name + f"·螭首{si}-{k}", 0.65, 0.55, 0.42, xx, fixed, z0 + 0.95, MAT["marble"])


def glass_facade(name, length, h, fixed, axis, side, center=0.0, z0=3.0, spacing=12.0):
    """现代民族形式的石材柱廊＋玻璃幕墙（只做广场面）。"""
    if axis == "y":
        box(name + "·玻璃", 0.6, length - 16, h - 6, fixed + side * 1.2, center, z0, MAT["glass"])
    else:
        box(name + "·玻璃", length - 16, 0.6, h - 6, center, fixed + side * 1.2, z0, MAT["glass"])
    n = max(3, int(length / spacing))
    for i in range(n + 1):
        p = -length / 2 + i * (length / n)
        if axis == "y":
            box(name + f"·柱{i}", 2.2, 2.2, h - 1.5, fixed + side * 2.6, center + p, 0.15, MAT["stone_light"])
            if P:
                box(name + f"·柱{i}·础", 2.9, 2.9, 0.9, fixed + side * 2.6, center + p, 0.15, MAT["marble"])
                box(name + f"·柱{i}·头", 2.9, 2.9, 0.7, fixed + side * 2.6, center + p, h - 1.2, MAT["stone_light"])
        else:
            box(name + f"·柱{i}", 2.2, 2.2, h - 1.5, center + p, fixed + side * 2.6, 0.15, MAT["stone_light"])
            if P:
                box(name + f"·柱{i}·础", 2.9, 2.9, 0.9, center + p, fixed + side * 2.6, 0.15, MAT["marble"])
                box(name + f"·柱{i}·头", 2.9, 2.9, 0.7, center + p, fixed + side * 2.6, h - 1.2, MAT["stone_light"])
    for k, frac in enumerate((0.42, 0.76)):
        zz = z0 + (h - z0) * frac
        if axis == "y":
            box(name + f"·腰线{k}", 1.1, length - 8, 1.4, fixed + side * 1.9, center, zz, MAT["stone_light"])
        else:
            box(name + f"·腰线{k}", length - 8, 1.1, 1.4, center, fixed + side * 1.9, zz, MAT["stone_light"])


def add_mullions(name, fixed, axis, side, center, length, h, glass_h=None):
    gh = glass_h if glass_h else h - 6
    z0 = 3.0
    span = length - 16
    n = max(1, int(span / 1.8))
    for i in range(n + 1):
        p = center - span / 2 + i * span / n
        if axis == "y":
            box(name + f"·竖梃{i}", 0.12, 0.16, gh, fixed + side * 1.55, p, z0, MAT["metal"])
        else:
            box(name + f"·竖梃{i}", 0.16, 0.12, gh, p, fixed + side * 1.55, z0, MAT["metal"])
    m = max(1, int(gh / 4.5))
    for j in range(m + 1):
        zz = z0 + j * gh / m
        if axis == "y":
            box(name + f"·横梃{j}", 0.14, span, 0.14, fixed + side * 1.55, center, zz, MAT["metal"])
        else:
            box(name + f"·横梃{j}", span, 0.14, 0.14, center, fixed + side * 1.55, zz, MAT["metal"])


def portico(name, rect, h, facade_side="E"):
    x0, x1, y0, y1 = rect
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w, d = x1 - x0, y1 - y0
    box(name + "·台", w + 3, d + 3, 1.1, cx, cy, 0.15, MAT["marble"])
    if facade_side in ("E", "W"):
        n = max(4, int(d / 8) + 1)
        ox = x1 - 1.0 if facade_side == "E" else x0 + 1.0
        for i in range(n):
            yy = y0 + 2 + i * (d - 4) / (n - 1)
            cyl(name + f"·柱{i}", 1.20, h - 2.5, ox, yy, 1.25, MAT["marble"], n=16)
            if P:
                box(name + f"·柱{i}·础", 3.0, 3.0, 0.55, ox, yy, 1.25, MAT["marble"])
                cyl(name + f"·柱{i}·础弧", 1.60, 0.35, ox, yy, 1.8, MAT["marble"])
                cyl(name + f"·柱{i}·头", 1.60, 0.35, ox, yy, 1.25 + h - 3.4, MAT["marble"])
                for k in range(8):
                    ang = 2 * math.pi * k / 8
                    box(name + f"·卷草{i}-{k}", 0.32, 0.32, 0.32,
                        ox + 1.55 * math.cos(ang), yy + 1.55 * math.sin(ang),
                        1.25 + h - 3.55, MAT["stone_light"])
                box(name + f"·柱{i}·顶板", 3.0, 3.0, 0.45, ox, yy, 1.25 + h - 3.05, MAT["stone_light"])
        box(name + "·檐部下", w + 1, d + 1, 1.3, cx, cy, 1.25 + h - 3.0, MAT["stone_light"])
        box(name + "·檐部中", w + 1.7, d + 1.7, 1.2, cx, cy, 1.25 + h - 1.9, MAT["stone_light"])
        box(name + "·檐口", w + 2.4, d + 2.4, 0.8, cx, cy, 1.25 + h - 0.8, MAT["stone_light"])
        box(name + "·顶", w + 1.2, d + 1.2, 0.8, cx, cy, 1.25 + h - 0.1, MAT["roof_flat"])
    else:
        n = max(4, int(w / 8) + 1)
        oy = y1 - 1.0 if facade_side == "N" else y0 + 1.0
        for i in range(n):
            xx = x0 + 2 + i * (w - 4) / (n - 1)
            cyl(name + f"·柱{i}", 1.20, h - 2.5, xx, oy, 1.25, MAT["marble"], n=16)
            if P:
                box(name + f"·柱{i}·础", 3.0, 3.0, 0.55, xx, oy, 1.25, MAT["marble"])
                cyl(name + f"·柱{i}·础弧", 1.60, 0.35, xx, oy, 1.8, MAT["marble"])
                cyl(name + f"·柱{i}·头", 1.60, 0.35, xx, oy, 1.25 + h - 3.4, MAT["marble"])
                for k in range(8):
                    ang = 2 * math.pi * k / 8
                    box(name + f"·卷草{i}-{k}", 0.32, 0.32, 0.32,
                        xx + 1.55 * math.cos(ang), oy + 1.55 * math.sin(ang),
                        1.25 + h - 3.55, MAT["stone_light"])
                box(name + f"·柱{i}·顶板", 3.0, 3.0, 0.45, xx, oy, 1.25 + h - 3.05, MAT["stone_light"])
        box(name + "·檐部下", w + 1, d + 1, 1.3, cx, cy, 1.25 + h - 3.0, MAT["stone_light"])
        box(name + "·檐部中", w + 1.7, d + 1.7, 1.2, cx, cy, 1.25 + h - 1.9, MAT["stone_light"])
        box(name + "·檐口", w + 2.4, d + 2.4, 0.8, cx, cy, 1.25 + h - 0.8, MAT["stone_light"])
        box(name + "·顶", w + 1.2, d + 1.2, 0.8, cx, cy, 1.25 + h - 0.1, MAT["roof_flat"])
    if P:
        if facade_side == "E":
            dw = min(24.0, d * 0.4)
            box(name + "·门框", 1.0, dw + 3, 16, x0 + 1.00, cy, 1.25, MAT["stone_light"])
            box(name + "·门", 0.8, dw, 14, x0 + 1.35, cy, 1.25, MAT["door"])
        elif facade_side == "W":
            dw = min(24.0, d * 0.4)
            box(name + "·门框", 1.0, dw + 3, 16, x1 - 1.00, cy, 1.25, MAT["stone_light"])
            box(name + "·门", 0.8, dw, 14, x1 - 1.35, cy, 1.25, MAT["door"])
        elif facade_side == "N":
            dw = min(24.0, w * 0.4)
            box(name + "·门框", dw + 3, 1.0, 16, cx, y0 + 1.00, 1.25, MAT["stone_light"])
            box(name + "·门", dw, 0.8, 14, cx, y0 + 1.35, 1.25, MAT["door"])
        else:
            dw = min(24.0, w * 0.4)
            box(name + "·门框", dw + 3, 1.0, 16, cx, y1 - 1.00, 1.25, MAT["stone_light"])
            box(name + "·门", dw, 0.8, 14, cx, y1 - 1.35, 1.25, MAT["door"])
        # 门扇竖分格
        for k in range(-2, 3):
            if facade_side == "E":
                box(name + f"·门挺{k}", 0.12, 0.12, 14, x0 + 1.80, cy + k * 3.2, 1.5, MAT["roof_gold"])
            elif facade_side == "W":
                box(name + f"·门挺{k}", 0.12, 0.12, 14, x1 - 1.80, cy + k * 3.2, 1.5, MAT["roof_gold"])
            elif facade_side == "N":
                box(name + f"·门挺{k}", 0.12, 0.12, 14, cx + k * 3.2, y0 + 1.80, 1.5, MAT["roof_gold"])
            else:
                box(name + f"·门挺{k}", 0.12, 0.12, 14, cx + k * 3.2, y1 - 1.80, 1.5, MAT["roof_gold"])

        if facade_side in ("E", "W"):
            sx = 1 if facade_side == "E" else -1
            fx = (x0 + 2.6) if facade_side == "E" else (x1 - 2.6)
            box(name + "·门槛", 1.5, dw + 2, 0.55, (x0 + 2.0) if facade_side == "E" else (x1 - 2.0), cy, 1.25, MAT["stone_light"])
            box(name + "·匾框", 1.2, 12.0, 4.2, fx, cy, 15.7, MAT["stone_light"])
            box(name + "·匾", 1.0, 10.6, 3.4, fx + sx * 0.5, cy, 16.1, MAT["roof_flat"])
            for zz in (16.1, 19.3):
                box(name + "·匾金边", 0.16, 10.8, 0.18, fx + sx * 0.7, cy, zz, MAT["roof_gold"])
            for sy in (-1, 1):
                ring = cyl(name + f"·铺首{sy}", 0.32, 0.18, 0, 0, 0, MAT["roof_gold"], n=12)
                ring.rotation_euler = (0, math.pi / 2, 0)
                ring.location = (fx + sx * 0.9, cy + sy * 3.4, 8.0)
        else:
            sy = 1 if facade_side == "N" else -1
            fy = (y0 + 2.6) if facade_side == "N" else (y1 - 2.6)
            box(name + "·门槛", dw + 2, 1.5, 0.55, cx, (y0 + 2.0) if facade_side == "N" else (y1 - 2.0), 1.25, MAT["stone_light"])
            box(name + "·匾框", 12.0, 1.2, 4.2, cx, fy, 15.7, MAT["stone_light"])
            box(name + "·匾", 10.6, 1.0, 3.4, cx, fy + sy * 0.5, 16.1, MAT["roof_flat"])
            for zz in (16.1, 19.3):
                box(name + "·匾金边", 10.8, 0.16, 0.18, cx, fy + sy * 0.7, zz, MAT["roof_gold"])
            for sx in (-1, 1):
                ring = cyl(name + f"·铺首{sx}", 0.32, 0.18, 0, 0, 0, MAT["roof_gold"], n=12)
                ring.rotation_euler = (math.pi / 2, 0, 0)
                ring.location = (cx + sx * 3.4, fy + sy * 0.9, 8.0)


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
for i in range(1, 11):
    box("铺装缝·纵", 0.35, P["depth"], 0.03, P["x0"] + i * 50, (P["y_north"] + P["y_south"]) / 2,
        0.19, MAT["stone_dark"])
for i in range(1, 16):
    box("铺装缝·横", P["width"], 0.35, 0.03, 0, P["y_north"] - i * 50,
        0.19, MAT["stone_dark"])
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
for yy in (b["y0"] + 1.2, b["y1"] - 1.2):
    box("承天门桥·栏板", b["x1"] - b["x0"] - 2.4, 0.4, 0.9, 0, yy, 0.25 + b["h"], MAT["marble"])
    for i in range(15):
        xx = -47 + i * 94 / 14
        box("承天门桥·望柱", 0.4, 0.4, 1.1, xx, yy, 0.25 + b["h"], MAT["marble"])
g = PW["gate"]
_wall_w = 2 * (hw + 3)
_seg = (_wall_w - g["w"]) / 2
for _sx in (-1, 1):
    _cx = _sx * (g["w"] / 2 + _seg / 2)
    box("宫城南墙", _seg, PW["wall_t"], 10.0, _cx, PW["south_wall_face"], 0.1, MAT["wall_red"])
    box("宫城南墙·压顶", _seg + 0.4, PW["wall_t"] + 0.6, 0.5, _cx,
        PW["south_wall_face"], 10.1, MAT["stone_dark"])
x = -370
while x <= 370:
    if abs(x) > 54:
        box("宫城·垛口", 2.8, 0.9, 1.2, x, PW["south_wall_face"] - 2.2, 10.4, MAT["wall_red"])
    x += 8.0
def arch_ring(name, cx, y, r, spring, z0=0.1, thick=0.55, depth=0.36,
              seg=32, material=None):
    verts, faces = [], []
    for i in range(seg + 1):
        a = math.pi * i / seg
        for rr in (r, r + thick):
            for yy in (y - depth / 2, y + depth / 2):
                verts.append((cx + rr * math.cos(a), yy, z0 + spring + rr * math.sin(a)))
    for i in range(seg):
        b, c = i * 4, (i + 1) * 4
        faces += [(b, b + 1, c + 1, c), (b + 2, b + 3, c + 3, c + 2),
                  (b, b + 2, c + 2, c), (b + 1, b + 3, c + 3, c + 1)]
    return mesh_object(name, verts, faces, material)


def arch_prism(name, cx, y, r, spring, z0=0.1, depth=0.6, material=None, seg=24):
    prof = [(-r, 0.0), (r, 0.0)]
    for i in range(1, seg):
        a = math.pi * i / seg
        prof.append((r * math.cos(a), spring + r * math.sin(a)))
    prof.append((-r, spring))
    n = len(prof)
    verts = [(cx + px, y - depth / 2, z0 + pz) for px, pz in prof]
    verts += [(cx + px, y + depth / 2, z0 + pz) for px, pz in prof]
    faces = [tuple(range(n))[::-1], tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    return mesh_object(name, verts, faces, material)


def five_arch_gate(g):
    """承天门五券门城台：六墩、中央 16 m、两侧 9.5 m，真券洞。"""
    CY, Z0, H, DEP = g["cy"], 0.1, 16.0, g["d"]
    TOP = Z0 + H
    Y0, Y1 = CY - DEP / 2, CY + DEP / 2
    piers = [(-48, -37.6), (-31.2, -20.8), (-14.4, -4.0),
             (4.0, 14.4), (20.8, 31.2), (37.6, 48)]
    for i, (a, b) in enumerate(piers):
        box(f"承天门·墩台{i}", b - a, DEP, H, (a + b) / 2, CY, Z0, MAT["wall_red"])
    ops = [(-34.4, 6.4, 8.0), (-17.6, 6.4, 8.0), (0.0, 8.0, 8.5),
           (17.6, 6.4, 8.0), (34.4, 6.4, 8.0)]
    for k, (cx, ow, spring) in enumerate(ops):
        r = ow / 2.0
        n = 36
        for i in range(n):
            xm = cx - r + (i + 0.5) * ow / n
            zb = spring + math.sqrt(max(0.0, r * r - (xm - cx) ** 2))
            if TOP - zb > 0.05:
                box(f"承天门·拱腹{k}-{i}", ow / n + 0.02, DEP, TOP - zb, xm, CY, zb, MAT["wall_red"])
        arch_prism(f"承天门·门洞{k}", cx, CY, r, spring, Z0, 0.6, MAT["stone_dark"])
        for tag, yy in (("南", Y0), ("北", Y1)):
            arch_ring(f"承天门·券脸{k}{tag}", cx, yy, r, spring, Z0, 0.55, 0.36,
                      material=MAT["stone_light"])
            for sx in (-1, 1):
                box(f"承天门·券脚{k}{tag}{sx}", 0.55, 0.36, spring,
                    cx + sx * (r + 0.275), yy, Z0, MAT["stone_light"])
    box("承天门·城台地栿", 96.6, DEP + 0.6, 0.7, 0, CY, Z0, MAT["stone_light"])
    box("承天门·城台压顶", 96.8, DEP + 0.8, 0.5, 0, CY, TOP - 0.5, MAT["stone_light"])


if not P:
    box("承天门·城台", g["w"], g["d"], 12.0, 0, g["cy"], 0.1, MAT["wall_red"])
    r = D.FEATURES["review"]
    box("承天门·阅兵台", r["x1"] - r["x0"], r["y1"] - r["y0"], r["h"],
        0, (r["y0"] + r["y1"]) / 2, 12.1, MAT["stone_light"])
    box("承天门·门洞", 26, 1.2, 10.0, 0, g["cy"] - g["d"] / 2 - 0.4, 0.1, MAT["stone_dark"])
    for (ww, dd, xx, yy) in ((g["w"], 0.5, 0, g["cy"] - g["d"] / 2 + 0.3),
                              (g["w"], 0.5, 0, g["cy"] + g["d"] / 2 - 0.3),
                              (0.5, g["d"], -g["w"] / 2 + 0.3, g["cy"]),
                              (0.5, g["d"], g["w"] / 2 - 0.3, g["cy"])):
        box("承天门·城台栏板", ww, dd, 1.2, xx, yy, 12.1, MAT["marble"])
    box("承天门·城楼", 62, 26, 13.0, 0, g["cy"], 12.1, MAT["wall_red"])
    box("承天门·城楼窗", 50, 0.5, 3.6, 0, g["cy"] - 13.0, 16.8, MAT["glass"])
    hip_roof("承天门·城楼顶", 62, 26, 6.0, 0, g["cy"], 25.1, MAT["roof_gold"], overhang=5)
    for sx in (-1, 1):
        box("承天门·雁翅楼", 38, 20, 11.0, sx * 62, -497, 0.1, MAT["wall_red"])
        hip_roof("承天门·雁翅楼顶", 38, 20, 4.2, sx * 62, -497, 11.1, MAT["roof_gold"], overhang=3)
if P:
    try:
        sys.path.insert(0, os.path.join(HERE, "..", "palace"))
        import precise_lib as PL
        PL.set_collection(col)
        PL.make_materials()
        before = set(bpy.data.objects)
        PL.gate_house("承天门·精模", g["w"], g["d"], z=0.1, h=16.0)
        new = [o for o in bpy.data.objects if o not in before]
        keep = []
        for o in new:
            if any(k in o.name for k in ("城台", "门洞", "券脚", "券脸", "翼墙", "门楼")):
                bpy.data.objects.remove(o, do_unlink=True)
            else:
                o.location.y += g["cy"]
                keep.append(o)
        five_arch_gate(g)
        b3 = set(bpy.data.objects)
        PL.hall("承天门·门楼", 64.0, 28.0, bays=[64.0 / 9.0] * 9,
                dbays=[28.0 / 5.0] * 5, z=16.1, storeys=2,
                base_h=0.65, col_h=5.8, plaque=None, lod=2,
                stairs=False, balustrade=False)
        hnew = [x for x in bpy.data.objects if x not in b3]
        for o in hnew:
            o.location.y += g["cy"]
        emp2 = bpy.data.objects.new("承天门·门楼压低", None)
        col.objects.link(emp2)
        emp2.location = (0.0, g["cy"], 16.1)
        emp2.hide_render = True
        emp2.matrix_parent_inverse = Matrix.Translation((0.0, -g["cy"], -16.1))
        for o in hnew:
            o.parent = emp2
            o.matrix_parent_inverse = emp2.matrix_parent_inverse
        emp2.scale = (1.0, 1.0, 0.85)
        for sx in (-1, 1):
            b2 = set(bpy.data.objects)
            PL.wall_tower("承天门·雁翅楼" + ("东" if sx > 0 else "西"), 32, 17, z=0.1, body_h=9.5)
            for o in [x for x in bpy.data.objects if x not in b2]:
                o.location.x += sx * 62
                o.location.y += -497
        print("PRECISE_GATE", len(new), flush=True)
    except Exception as e:
        print("PRECISE_GATE_FAIL", e, flush=True)

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
    box("大会堂·" + m["name"] + "·基座线", w + 1.2, d + 1.2, 1.4, cx, cy, 2.3, MAT["stone_light"])
    glass_facade("大会堂·" + m["name"], d, h, m["x1"], "y", 1, (m["y0"] + m["y1"]) / 2)
    box("大会堂·" + m["name"] + "·檐口", w + 3, d + 3, 2.2, cx, cy, h - 2.2, MAT["stone_light"])
    if m["kind"] == "chamber":
        hip_roof("大会堂·中厅顶", w, d, 14.0, cx, cy, h + 0.15, MAT["roof_tile"], overhang=6, front="E")
    else:
        flat_roof("大会堂·" + m["name"] + "顶", w, d, cx, cy, h + 0.15)
for yy in (-925.5, -1155.5):
    box("大会堂·分界柱", 7.0, 5.0, 48.0, -307.0, yy, 2.3, MAT["stone_light"])
for m in D.MASSES:
    if m["parent"] == "hall" and m["kind"] == "portico":
        portico("大会堂·" + m["name"], (m["x0"], m["x1"], m["y0"], m["y1"]), 30, "E")
        steps("大会堂·" + m["name"], m["x1"], (m["y0"] + m["y1"]) / 2, m["y1"] - m["y0"], "E")

# 议事大楼：同大外框，一整块基座 + 中央高体量
CX, CY = 425.0, -1035.5
plinth("议事大楼", 238, 608, CX, CY)
box("议事大楼·基座", 230, 600, 33.7, CX, CY, 2.3, MAT["stone"])
box("议事大楼·基座线", 231.2, 601.2, 1.4, CX, CY, 2.3, MAT["stone_light"])
glass_facade("议事大楼·基座", 600, 36, 310, "y", -1, CY)
box("议事大楼·基座檐口", 233, 603, 2.2, CX, CY, 33.8, MAT["stone_light"])
flat_roof("议事大楼·基座顶", 230, 600, CX, CY, 36.15)
box("议事大楼·议事厅", 160, 160, 41.7, CX, CY, 2.3, MAT["stone"])
box("议事大楼·议事厅基座线", 161.2, 161.2, 1.4, CX, CY, 34.3, MAT["stone_light"])
box("议事大楼·议事厅幕墙", 0.4, 150, 37, 344.6, CY, 4.5, MAT["glass"])
box("议事大楼·议事厅檐口", 163, 163, 2.2, CX, CY, 41.8, MAT["stone_light"])
hip_roof("议事大楼·议事厅顶", 160, 160, 14.0, CX, CY, 44.15, MAT["roof_tile"], overhang=5, front="W")
box("议事大楼·中央门楼", 16.0, 100.0, 8.0, 302.0, CY, 30.2, MAT["stone_light"])
hip_roof("议事大楼·中央门楼顶", 16.0, 100.0, 3.0, 302.0, CY, 38.2, MAT["roof_tile"], overhang=3)
for m in D.MASSES:
    if m["parent"] == "council" and m["kind"] == "portico":
        portico("议事大楼·" + m["name"], (m["x0"], m["x1"], m["y0"], m["y1"]), 30, "W")
        steps("议事大楼·" + m["name"], m["x0"], (m["y0"] + m["y1"]) / 2, m["y1"] - m["y0"], "W")

# 博物馆：560 × 170
MX, MY = 0.0, -1535.5
plinth("博物馆", 568, 178, MX, MY)
box("博物馆·主体", 560, 170, 27.7, MX, MY, 2.3, MAT["stone"])
box("博物馆·主体基座线", 561.2, 171.2, 1.4, MX, MY, 2.3, MAT["stone_light"])
glass_facade("博物馆·主体", 560, 30, -1450.5, "x", 1, 0.0)
box("博物馆·主体檐口", 563, 173, 2.2, MX, MY, 27.8, MAT["stone_light"])
flat_roof("博物馆·主体顶", 560, 170, MX, MY, 30.15)
box("博物馆·中央陈列厅", 240, 140, 12.0, MX, MY, 30.15, MAT["stone"])
box("博物馆·陈列厅基座线", 241.2, 141.2, 1.2, MX, MY, 30.15, MAT["stone_light"])
box("博物馆·陈列厅幕墙", 220, 0.5, 9.0, MX, -1465.3, 31.0, MAT["glass"])
box("博物馆·陈列厅檐口", 243, 143, 2.0, MX, MY, 40.2, MAT["stone_light"])
hip_roof("博物馆·中央顶", 240, 140, 10.0, MX, MY, 42.15, MAT["roof_tile"], overhang=5, front="N")
m = next(x for x in D.MASSES if x["key"] == "museum-portico")
portico("博物馆·门廊", (m["x0"], m["x1"], m["y0"], m["y1"]), 26, "N")
steps("博物馆·门廊", 0, m["y1"], m["x1"] - m["x0"], "N")

if P:
    rail_edge("大会堂·台基栏板", "y", -306.0, -1339.5, -731.5,
              [(-865.5, -785.5), (-1075.5, -995.5), (-1285.5, -1205.5)])
    rail_edge("议事大楼·台基栏板", "y", 306.0, -1339.5, -731.5,
              [(-895.5, -855.5), (-1085.5, -985.5), (-1215.5, -1175.5)])
    rail_edge("博物馆·台基栏板", "x", -1446.5, -284.0, 284.0, [(-70.0, 70.0)])
    emblem("大会堂·国徽", "x", -308.2, -1035.5, 24.6, 1)
    emblem("议事大楼·国徽", "x", 308.2, -1035.5, 24.6, -1)
    emblem("博物馆·国徽", "y", -1449.2, 0.0, 22.2, 1)
    for m in D.MASSES:
        if m["parent"] == "hall" and m["kind"] != "portico":
            add_mullions("大会堂·" + m["name"], m["x1"], "y", 1,
                         (m["y0"] + m["y1"]) / 2, m["y1"] - m["y0"], m["h"])
    add_mullions("议事大楼·基座", 310, "y", -1, CY, 600, 36)
    add_mullions("议事大楼·议事厅", 344.6, "y", -1, CY, 150, 50, 37)
    add_mullions("博物馆·主体", -1450.5, "x", 1, 0.0, 560, 30)

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
        mids.append(0)
        faces.append(tuple(base + n + i for i in range(n)))
        mids.append(0)
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
sun_d.energy = 2.6
sun_d.angle = math.radians(3)
sun = bpy.data.objects.new("Sun", sun_d)
link(sun)
sun.rotation_euler = (math.radians(35), 0, math.radians(232))

sc.world = bpy.data.worlds.new("World")
sc.world.use_nodes = True
bg = sc.world.node_tree.nodes["Background"]
nt = sc.world.node_tree
tex = nt.nodes.new("ShaderNodeTexCoord")
sep = nt.nodes.new("ShaderNodeSeparateXYZ")
ramp = nt.nodes.new("ShaderNodeValToRGB")
nt.links.new(tex.outputs["Normal"], sep.inputs[0])
nt.links.new(sep.outputs["Z"], ramp.inputs[0])
e0 = ramp.color_ramp.elements[0]; e0.position = 0.00; e0.color = (0.72, 0.75, 0.80, 1.0)
e1 = ramp.color_ramp.elements[1]; e1.position = 0.45; e1.color = (0.26, 0.40, 0.62, 1.0)
nt.links.new(ramp.outputs["Color"], bg.inputs[0])
bg.inputs[1].default_value = 0.45

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
sc.view_settings.exposure = -0.25

# ------------------------------------------------------------------ 出图
AR = 16 / 9
shots = [
    ("鸟瞰东南", dict(loc=(900, -2400, 820), target=(0, -1100, 0), lens=38)),
    ("中轴", dict(loc=(0, -950, 35), target=(0, -480, 16), lens=40)),
    ("西望大会堂", dict(loc=(60, -900, 45), target=(-430, -1040, 32), lens=45)),
    ("东望议事楼", dict(loc=(-60, -900, 45), target=(430, -1040, 32), lens=45)),
    ("南望博物馆", dict(loc=(0, -1120, 45), target=(0, -1560, 30), lens=55)),
    ("人视承天门", dict(loc=(90, -655, 2.2), target=(0, -480, 18), lens=40)),
]
prefix = "精模" if P else "体量白模"
if P:
    shots = [
        ("鸟瞰东南", dict(loc=(900, -2400, 820), target=(0, -1100, 0), lens=38)),
        ("大会堂正立面", dict(loc=(-80, -1035, 30), target=(-420, -1035, 26), lens=45)),
        ("大会堂檐下", dict(loc=(-270, -940, 52), target=(-430, -1035, 42), lens=55)),
        ("议事楼入口", dict(loc=(120, -1035, 26), target=(400, -1035, 28), lens=55)),
        ("博物馆入口", dict(loc=(0, -1370, 22), target=(0, -1480, 24), lens=50)),
        ("承天门人视", dict(loc=(0, -650, 3.5), target=(0, -468, 15), lens=34)),
        ("中轴", dict(loc=(0, -950, 35), target=(0, -480, 16), lens=40)),
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
    path = os.path.join(args.out, f"国家广场(2026)·{prefix}·{name}.png")
    sc.render.filepath = path
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    results[name] = round(time.time() - t0, 1)
    print("RENDER", name, results[name], flush=True)

# ------------------------------------------------------------------ 保存 / 导出
blend = os.path.join(WORK, "plaza_massing.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend)
glb = os.path.join(args.out, f"国家广场(2026)·{prefix}.glb")
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
