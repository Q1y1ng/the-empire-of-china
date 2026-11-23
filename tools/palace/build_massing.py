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
ap.add_argument("--no-glb", action="store_true", help="只出图，不导 glb（迭代用）")
ap.add_argument("--glb-textures", action="store_true",
                help="导出前给 glb 补 UV 并换贴图材质（慢，交付时开）")
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
    try:
        import lg_look as _LK
        PL.MAT.update(_LK.make_materials())
        print("MATERIALS: lg_look", len(_LK.MAT), flush=True)
    except Exception as _e:
        print("MATERIALS: precise_lib only (%s)" % _e, flush=True)


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
    "tree": material("树冠", (0.105, 0.170, 0.085), 0.92),
    "trunk": material("树干", (0.20, 0.14, 0.10), 0.9),
    "service": material("值房灰", (0.68, 0.66, 0.60), 0.9),
    "path": material("御道", (0.76, 0.73, 0.66), 0.9),
    "glass": material("现代玻璃", (0.16, 0.30, 0.40), 0.25, 0.15),
    "ridge": material("屋脊压顶", (0.32, 0.22, 0.09), 0.5),
    "rock": material("假山石", (0.45, 0.43, 0.39), 0.95),
}


def paving_mat(name, rgb, bw=0.48, rh=0.24, mortar=(0.085, 0.078, 0.070),
               rough=0.88, mortar_w=0.012):
    """地面铺装：Brick 纹理按米制铺 480×240 青砖（Object 坐标，平面直接可用）。"""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    for n in list(N):
        N.remove(n)
    out = N.new("ShaderNodeOutputMaterial")
    bsdf = N.new("ShaderNodeBsdfPrincipled")
    L.new(bsdf.outputs[0], out.inputs[0])
    tc = N.new("ShaderNodeTexCoord")
    br = N.new("ShaderNodeTexBrick")
    br.offset = 0.5
    br.squash = 1.0
    br.inputs["Scale"].default_value = 1.0
    br.inputs["Brick Width"].default_value = bw
    br.inputs["Row Height"].default_value = rh
    br.inputs["Mortar Size"].default_value = mortar_w
    br.inputs["Mortar Smooth"].default_value = 0.25
    br.inputs["Bias"].default_value = 0.0
    br.inputs["Color1"].default_value = (*rgb, 1.0)
    br.inputs["Color2"].default_value = (rgb[0] * 0.84, rgb[1] * 0.84, rgb[2] * 0.84, 1.0)
    br.inputs["Mortar"].default_value = (*mortar, 1.0)
    L.new(tc.outputs["Object"], br.inputs["Vector"])
    # 大尺度色差：二十来米一档。几百米的铺装在 480 mm 砖尺度上会平均成一块死灰，
    # 必须靠低频噪声把明暗块做出来，否则鸟瞰里广场就是一张灰纸。
    nb = N.new("ShaderNodeTexNoise")
    nb.inputs["Scale"].default_value = 0.042
    nb.inputs["Detail"].default_value = 4.0
    nb.inputs["Roughness"].default_value = 0.55
    L.new(tc.outputs["Object"], nb.inputs["Vector"])
    mr2 = N.new("ShaderNodeMapRange")
    mr2.inputs[1].default_value = 0.32
    mr2.inputs[2].default_value = 0.68
    mr2.inputs[3].default_value = 0.87
    mr2.inputs[4].default_value = 1.11
    L.new(nb.outputs["Fac"], mr2.inputs[0])
    cc = N.new("ShaderNodeCombineColor")
    for _i in range(3):
        L.new(mr2.outputs[0], cc.inputs[_i])
    mx = N.new("ShaderNodeMix")
    mx.data_type = "RGBA"
    mx.blend_type = "MULTIPLY"
    mx.inputs[0].default_value = 1.0
    L.new(br.outputs["Color"], mx.inputs[6])
    L.new(cc.outputs[0], mx.inputs[7])
    L.new(mx.outputs[2], bsdf.inputs["Base Color"])
    n = N.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = 0.35
    n.inputs["Detail"].default_value = 6.0
    L.new(tc.outputs["Object"], n.inputs["Vector"])
    mr = N.new("ShaderNodeMapRange")
    L.new(n.outputs["Fac"], mr.inputs[0])
    mr.inputs[3].default_value = rough - 0.10
    mr.inputs[4].default_value = min(0.98, rough + 0.06)
    L.new(mr.outputs[0], bsdf.inputs["Roughness"])
    bp = N.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.45
    bp.inputs["Distance"].default_value = 0.012
    L.new(br.outputs["Fac"], bp.inputs["Height"])
    L.new(bp.outputs[0], bsdf.inputs["Normal"])
    return m


# 广场是 1.2×0.6 m 的大石条（照片里一眼能数出缝），不是 480 mm 青砖
MAT["plaza"] = paving_mat("宫城地坪·石板", (0.165, 0.157, 0.138),
                          bw=1.20, rh=0.60, mortar=(0.058, 0.052, 0.045),
                          mortar_w=0.018, rough=0.86)
MAT["path"] = paving_mat("御道·石板", (0.168, 0.160, 0.142), bw=1.55, rh=0.78,
                         mortar=(0.15, 0.14, 0.12), mortar_w=0.014, rough=0.78)
MAT["ground"] = paving_mat("城外地面·土路", (0.120, 0.113, 0.098), bw=1.6, rh=0.8,
                           mortar=(0.16, 0.15, 0.13), mortar_w=0.02, rough=0.95)


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
    """院墙：朱红墙身 + **两坡瓦帽**（出檐 0.4 m、脊高 0.55 m）。"""
    mat = mat or MAT["wall"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    Lx, Ly = x1 - x0, y1 - y0
    box(name, Lx, Ly, h, cx, cy, 0.0, mat)
    H = 0.55
    if Lx >= Ly:
        a, b = Lx + 0.45, Ly + 0.45
        v = [(-a / 2, -b / 2, 0), (a / 2, -b / 2, 0), (a / 2, b / 2, 0),
             (-a / 2, b / 2, 0), (-a / 2, 0, H), (a / 2, 0, H)]
    else:
        a, b = Ly + 0.45, Lx + 0.45
        v = [(-a / 2, -b / 2, 0), (a / 2, -b / 2, 0), (a / 2, b / 2, 0),
             (-a / 2, b / 2, 0), (-a / 2, 0, H), (a / 2, 0, H)]
        v = [(y, x, z) for (x, y, z) in v]
    f = [(0, 1, 5, 4), (3, 2, 5, 4), (0, 4, 3), (1, 2, 5)]
    mesh_from(name + "_瓦", [(cx + a, cy + b, h + c) for (a, b, c) in v], f,
              MAT.get("glaze_plain_dark") or MAT["ridge"])


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
    box(name + "_顶", w + 0.6, d + 0.6, 0.7, x, y, H, MAT["ridge"])
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


def prism_profile(name, poly, prof, mat):
    """沿多边形挤出一个带线脚的截面（须弥座）：prof = [(内收米数, 绝对 z)]。

    三台原来只有 `prism()` —— 一个直上直下的方盒子，8 m 高的台帮在「人视·金瓯殿」
    里就是一片白墙，束腰的如意头（件件都做出来了）根本没有凹进去的束腰可坐。
    """
    n = len(poly)
    area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1]
               for i in range(n))
    sgn = 1.0 if area > 0 else -1.0
    nrm = []
    for i in range(n):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % n]
        ex, ey = bx - ax, by - ay
        L = math.hypot(ex, ey) or 1.0
        nrm.append((-ey * sgn / L, ex * sgn / L))     # 逆时针时内法向
    rings = []
    for (ins, z) in prof:
        ring = []
        for i in range(n):
            n0, n1 = nrm[i - 1], nrm[i]
            mx, my = n0[0] + n1[0], n0[1] + n1[1]
            ml = math.hypot(mx, my) or 1.0
            mx, my = mx / ml, my / ml
            c = max(0.35, mx * n1[0] + my * n1[1])     # miter 补偿（直角处 1.41）
            px, py = poly[i]
            ring.append((px + mx * ins / c, py + my * ins / c, z))
        rings.append(ring)
    verts, faces = [], []
    for r in rings:
        verts.extend(r)
    for k in range(len(rings) - 1):
        a, b = k * n, (k + 1) * n
        for i in range(n):
            j = (i + 1) % n
            faces.append((a + i, a + j, b + j, b + i))
    faces.append(tuple(range(n - 1, -1, -1)))
    top = (len(rings) - 1) * n
    faces.append(tuple(top + i for i in range(n)))
    return mesh_from(name, verts, faces, mat)


PL.make_materials()
if args.precise:
    # 须弥座截面（与 1.06/3.10、2.08/3.10 那套束腰雕饰同一个口径）
    _k = D.PLATFORM_H / 3.10
    _prof = [(t * _k, z * _k) for (t, z) in
             ((0.00, 0.00), (0.00, 0.34), (0.30, 0.40), (0.30, 0.92),
              (0.54, 1.06), (0.54, 2.08), (0.30, 2.22), (0.30, 2.80),
              (0.10, 2.94), (0.00, 3.10))]
    prism_profile("三台", D.PLATFORM_POLY, _prof, PL.MAT["stone"])
else:
    prism("三台", D.PLATFORM_POLY, D.PLATFORM_H, 0.0, MAT["platform"])
if args.precise:
    _ys = [b for a, b in D.PLATFORM_POLY]
    _y_edge = min(_ys)
    # 栏板在南面前陛处留口，否则一圈栏杆会把台阶挡死
    PL.railing_poly("三台", D.PLATFORM_POLY, D.PLATFORM_H, step=2.4, h=1.02,
                    gap=((-24.5, 24.5), (_y_edge - 4.0, _y_edge + 4.0)))
    _n, _dep, _hw = 30, 22.0, 23.0
    _sd = _dep / _n
    # 垂带：两侧各一条通长斜面石带（逐级小方块会露出锯齿状侧面）
    _y_f = _y_edge - 0.5
    _y_b = _y_edge - 0.5 - _dep
    # 抱鼓石：踏跺脚下两侧各一座（汉白玉鼓状石，收住台阶的起头）
    for _sx in (-1, 1):
        _bx = _sx * (_hw + 0.85)
        _by = _y_edge - 0.5 - _dep - 0.9
        box("三台·抱鼓石%+d" % _sx, 1.3, 1.9, 0.95, _bx, _by, 0.0,
            PL.MAT.get("marble_carved") or PL.MAT["stone"])
        box("三台·鼓顶%+d" % _sx, 0.9, 1.3, 0.45, _bx, _by, 0.95,
            PL.MAT.get("marble_carved") or PL.MAT["stone"])
    for _sx in (-1, 1):
        _cx, _w, _t = _sx * (_hw + 0.85), 1.7, 0.42
        _zf, _zb = D.PLATFORM_H + 0.22, -0.30     # 靠台身高、外端落地（-0.3 埋进地坪）
        _v = [(_cx - _w / 2, _y_f, _zf), (_cx + _w / 2, _y_f, _zf),
              (_cx + _w / 2, _y_b, _zb), (_cx - _w / 2, _y_b, _zb)]
        _v += [(a, b, c - _t) for (a, b, c) in _v]
        _f = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2),
              (2, 6, 7, 3), (3, 7, 4, 0)]
        PL.mesh_from("三台·垂带%+d" % _sx, _v, _f, PL.MAT["stone"])
    # 三台束腰雕饰：沿束腰一圈排如意头（须弥座的束腰本来就是雕出来的，
    # 素面线脚在两百米外看着像一块整石头）
    _ms = PL.MAT.get("marble_carved") or PL.MAT["stone"]
    _zw = D.PLATFORM_H * (1.06 / 3.10)      # 束腰下沿
    _zh = D.PLATFORM_H * (2.08 / 3.10) - _zw
    for _i, _p in enumerate(D.PLATFORM_POLY):
        _q = D.PLATFORM_POLY[(_i + 1) % len(D.PLATFORM_POLY)]
        _L = math.hypot(_q[0] - _p[0], _q[1] - _p[1])
        if _L < 2.0:
            continue
        _n = max(1, int(_L / 1.15))
        _dx, _dy = (_q[0] - _p[0]) / _L, (_q[1] - _p[1]) / _L
        _nx, _ny = -_dy, _dx
        _side = 1.0 if (_nx * _p[0] + _ny * _p[1]) > 0 else -1.0
        for _k in range(_n):
            _t = (_k + 0.5) / _n
            # 束腰已凹进去 0.54 m，如意头要跟着往里挪，否则变成 0.9 m 高的鼓包
            _x = _p[0] + (_q[0] - _p[0]) * _t + _nx * _side * (-0.34)
            _y = _p[1] + (_q[1] - _p[1]) * _t + _ny * _side * (-0.34)
            # 如意头要**连续**排，留 5 cm 缝：每 1.6 m 一块 0.86 宽，
            # 中间露出 0.74 m 素面束腰，整圈读成一排白栅栏
            _b = box("三台·束腰%d_%d" % (_i, _k), _L / _n - 0.05, 0.34, _zh * 0.72,
                     _x, _y, _zw, _ms)
            _b.rotation_euler[2] = math.atan2(_q[1] - _p[1], _q[0] - _p[0])
    _ms_keep = _ms
    for _i in range(_n):
        _top = D.PLATFORM_H * (_n - _i) / _n
        _yy = _y_edge - 0.5 - _i * _sd
        box("三台·踏跺%02d" % _i, 2 * _hw, _sd + 0.02, _top, 0, _yy, 0.0,
            PL.MAT["stone"])
        # 御路石：每级顶面一条 5 m 宽石带（不是整块斜板）
        box("三台·御路%02d" % _i, 5.0, _sd * 0.86, 0.09, 0, _yy, _top - 0.09, _ms)

else:
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
# 廊庑占地：院墙遇到它要让开，否则墙会横穿屋顶（近景看就是"墙从屋顶里长出来"）
_CORR = [(s["cx"], s["cy"], s["w"] / 2 + 2.0, s["d"] / 2 + 2.0)
         for s in D.STRUCTS if s["kind"] == "corridor"]


def _wall_pieces(name, x0, x1, y0, y1):
    """把一段轴对齐的墙按廊庑占地切开，返回若干可建段。"""
    along_x = (x1 - x0) >= (y1 - y0)
    a0, a1 = (x0, x1) if along_x else (y0, y1)
    b0, b1 = (y0, y1) if along_x else (x0, x1)
    cuts = []
    for (cx, cy, hw, hd) in _CORR:
        ca0, ca1 = (cx - hw, cx + hw) if along_x else (cy - hd, cy + hd)
        cb0, cb1 = (cy - hd, cy + hd) if along_x else (cx - hw, cx + hw)
        if cb1 < b0 or cb0 > b1:
            continue
        if ca1 <= a0 or ca0 >= a1:
            continue
        cuts.append((max(ca0, a0), min(ca1, a1)))
    if not cuts:
        return [(name, x0, x1, y0, y1)]
    cuts.sort()
    merged = []
    for a, b in cuts:
        if merged and a <= merged[-1][1] + 0.5:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    out, cur = [], a0
    for a, b in merged:
        if a > cur + 0.5:
            out.append((cur, a))
        cur = max(cur, b)
    if cur < a1 - 0.5:
        out.append((cur, a1))
    pieces = []
    for i, (a, b) in enumerate(out):
        nm = name if len(out) == 1 else "%s_%d" % (name, i)
        if along_x:
            pieces.append((nm, a, b, b0, b1))
        else:
            pieces.append((nm, b0, b1, a, b))
    return pieces


for c in D.COMPOUNDS:
    for w in D.compound_walls(c):
        for _pc in _wall_pieces(w["name"], w["x0"], w["x1"], w["y0"], w["y1"]):
            add_wall(_pc[0], _pc[1], _pc[2], _pc[3], _pc[4], h=WH)
if args.precise:
    # 院门必须建在数据给定的门洞位置：compound_walls() 是按 c["gates"] 把墙断开的，
    # 之前却在"南墙正中"另起一樘门——于是墙上留着 14 m 的断口没人填（作者看到的"城墙断开"）
    for c in D.COMPOUNDS:
        if c["name"] == "琼苑":
            continue
        for _i, (_side, _c0, _gw) in enumerate(c.get("gates") or []):
            if _side not in ("S", "N"):
                continue
            _y = c["y0"] if _side == "S" else c["y1"]
            PL.court_gate(f"{c['name']}·院门{_i}", _c0, _y, z=0.0,
                          w=max(3.4, _gw * 0.86), h=min(4.6, WH - 0.15),
                          face=(-1 if _side == "S" else 1))

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
    verts += [(x + nx, y + ny, 0.36), (x - nx, y - ny, 0.36)]
for i in range(len(pts) - 1):
    a = i * 2
    faces.append((a, a + 1, a + 3, a + 2))
mesh_from("内金水河", verts, faces, MAT["water"])

# 御道
box("御道", 18, 900, 0.22, 0, -20, 0.02, MAT["path"])

# ------------------------------------------------------------------ 琼苑 / 值房 / 树
g = next(c for c in D.COMPOUNDS if c["name"] == "琼苑")
_gx, _gy = (g["x0"] + g["x1"]) / 2, (g["y0"] + g["y1"]) / 2
_gw, _gd = g["x1"] - g["x0"] - 4, g["y1"] - g["y0"] - 4
box("琼苑地面", _gw, _gd, 0.5, _gx, _gy, 0.25, MAT["green"])
# 十字园路 + 一圈小径：卫星图里御花园是被路径切开的，不是一整块绿
box("琼苑·中路", 4.0, _gd - 6, 0.10, _gx, _gy, 0.68, MAT["path"])
box("琼苑·横路", _gw - 6, 4.0, 0.10, _gx, _gy, 0.68, MAT["path"])

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

_TT = (1.0 + 5 ** 0.5) / 2.0
_IN = (1.0 + _TT * _TT) ** 0.5
_ICO_V = [tuple(c / _IN for c in v) for v in (
    (-1, _TT, 0), (1, _TT, 0), (-1, -_TT, 0), (1, -_TT, 0),
    (0, -1, _TT), (0, 1, _TT), (0, -1, -_TT), (0, 1, -_TT),
    (_TT, 0, -1), (_TT, 0, 1), (-_TT, 0, -1), (-_TT, 0, 1))]
_ICO_F = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11),
          (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
          (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
          (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
_TV, _TF, _LV, _LF = [], [], [], []


def _plant(i, x, y):
    """种一棵树：把几何塞进两个大数组，最后只建 2 个网格。

    原来每棵树用 bpy.ops 建 1 柱 + 3 球 = 4 个对象，700 多棵就是 2,800 次算子
    调用，构建时间全耗在这上面（构建从 3 分钟涨到 10 分钟的主因）。
    """
    sv = 0.78 + 0.50 * ((i * 37) % 11) / 10.0
    r, h = 0.34 * sv, 2.8 * sv
    b0 = len(_TV)
    for z in (0.0, h):
        for k in range(8):
            a = 2 * math.pi * k / 8
            _TV.append((x + r * math.cos(a), y + r * math.sin(a), z))
    for k in range(8):
        k2 = (k + 1) % 8
        _TF.append((b0 + k, b0 + k2, b0 + 8 + k2, b0 + 8 + k))
    _TF.append(tuple(b0 + k for k in range(7, -1, -1)))
    _TF.append(tuple(b0 + 8 + k for k in range(8)))
    for (dx, dy, dz, rr) in ((0.0, 0.0, 0.0, 3.1), (1.5, -1.0, 0.8, 2.1),
                             (-1.3, 1.2, 0.5, 1.9)):
        cz = 4.3 * sv + dz * sv
        b = len(_LV)
        for (vx, vy, vz) in _ICO_V:
            _LV.append((x + dx * sv + vx * rr * sv,
                        y + dy * sv + vy * rr * sv * 0.95,
                        cz + vz * rr * sv * 0.80))
        for (a_, b_, c_) in _ICO_F:
            _LF.append((b + a_, b + b_, b + c_))


_planted = 0
for x, y in D.trees():
    _plant(_planted, x, y)
    _planted += 1
# 沿宫墙内侧一圈行道树（卫星照片里最明显的那圈绿）
_yin, _xin = HD - 15.0, HW - 15.0
for _x in range(int(-HW + 46), int(HW - 45), 15):
    for _yy in (_yin, -_yin):
        if abs(_x) < 74:                    # 让开南北宫门
            continue
        _plant(_planted, _x, _yy)
        _planted += 1
for _y in range(int(-HD + 46), int(HD - 45), 15):
    for _xx in (_xin, -_xin):
        if abs(_y) < 70:                    # 让开东西宫门
            continue
        _plant(_planted, _xx, _y)
        _planted += 1

# 各院落沿墙内一圈行道树（卫星图里六宫/五所的院子里都有）
for _c in D.COMPOUNDS:
    if _c["name"] == "琼苑":
        continue
    _x0, _x1, _y0, _y1 = _c["x0"] + 3.5, _c["x1"] - 3.5, _c["y0"] + 3.5, _c["y1"] - 3.5
    if (_x1 - _x0) < 12 or (_y1 - _y0) < 12:
        continue
    for _x in range(int(_x0), int(_x1) + 1, 13):
        _plant(_planted, _x, _y1)
        _planted += 1
    for _y in range(int(_y0) + 13, int(_y1), 13):
        _plant(_planted, _x0, _y)
        _planted += 1
        _plant(_planted, _x1, _y)
        _planted += 1

mesh_from("树·干", _TV, _TF, MAT["trunk"])
mesh_from("树·冠", _LV, _LF, MAT["tree"])
print("TREES", _planted, "trunk_tris", len(_TF), "leaf_tris", len(_LF))

# ------------------------------------------------------------------ 单体
def add_struct_precise(st):
    w, d, h = st["w"], st["d"], st["h"]
    z = st.get("z", 0.0)
    base_h = st["base"]["h"] if st.get("base") else max(0.9, min(2.4, h * 0.16))
    k = st["kind"]
    x, y = st["cx"], st["cy"]
    if k == "gate":
        before = set(col.objects)
        _na = 5 if w >= 78 else (3 if w >= 40 else 1)
        PL.gate_house(st["name"], w, d, z=z, h=h, n_arch=_na)
        new = set(col.objects) - before
        if d > w:            # 东西宫门：整体绕自身原点转 90°，让券洞朝东西
            for ob in new:
                ob.rotation_euler[2] = math.pi / 2
        for ob in new:       # 构件按原点建，整体挪到城门实位
            ob.location.x += x
            ob.location.y += y
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
    lod = 2 if w >= 64 else (1 if w >= 30 else 0)
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
            PL.rockery(s["name"], s["w"], s["d"], s["h"], z=0.0,
                        mat=PL.MAT.get("rock") or MAT["rock"])
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
            # 桥面要浮在水面之上（水面 z=0.36）：原来 z=-0.4 只有 0.19 露在水上，
            # 看着像"横在水里"；抬到 0.40，桥底离水 0.04，再从两端各加一段桥台接地面
            PL.bridge(s["name"], s["w"], s["d"], z=0.40)
            new = set(col.objects) - before
            # 桥面要垂直于河道：取离桥心最近的河段，按其法向旋转
            # 桥要落在河心上：取河道折线上离桥最近的点，投影过去（原来只用数据坐标，
            # 桥就摆在了河边的空地上——作者看到的"桥没在水面上"）
            _pts = D.RIVER["points"]
            _best, _bd = None, 1e18
            for _i in range(len(_pts) - 1):
                (_x0, _y0), (_x1, _y1) = _pts[_i], _pts[_i + 1]
                _vx, _vy = _x1 - _x0, _y1 - _y0
                _L2 = _vx * _vx + _vy * _vy or 1.0
                _t = max(0.0, min(1.0, ((s["cx"] - _x0) * _vx
                                        + (s["cy"] - _y0) * _vy) / _L2))
                _px, _py = _x0 + _vx * _t, _y0 + _vy * _t
                _dd = (_px - s["cx"]) ** 2 + (_py - s["cy"]) ** 2
                if _dd < _bd:
                    _bd, _best = _dd, (_px, _py, _vx, _vy)
            _px, _py, _vx, _vy = _best
            # 桥的长向（局部 +Y，length=d）要**横跨**河道，即对齐河道的法向：
            # R(θ)(0,1)=(-sinθ,cosθ)=(-vy,vx)/L  →  θ=atan2(vy, vx)。
            # 原来写 atan2(vx,-vy)，对东西向的内金水河正好转成 90°，
            # 五座金水桥就并排躺在河心里像五块踏石。
            _ang = math.atan2(_vy, _vx)
            # 只在**法向**上把桥挪到河心，沿河方向保留数据里的 cx/cy：
            # 否则五座金水桥各自吸到折线最近点，成一串斜错位的桥。
            _nl = math.hypot(_vx, _vy) or 1.0
            _nxb, _nyb = -_vy / _nl, _vx / _nl
            _tb = (_px - s["cx"]) * _nxb + (_py - s["cy"]) * _nyb
            _px = s["cx"] + _nxb * _tb
            _py = s["cy"] + _nyb * _tb
            for ob in new:
                ob.rotation_euler[2] = _ang
                ob.location.x += _px
                ob.location.y += _py
            # 两端桥台（把 0.40 的桥面接回地面）
            _nx2, _ny2 = -_vy, _vx
            _nl2 = math.hypot(_nx2, _ny2) or 1.0
            _nx2, _ny2 = _nx2 / _nl2, _ny2 / _nl2
            for _s2 in (-1, 1):
                _bx = _px + _nx2 * _s2 * (s["d"] / 2 + 1.6)
                _by = _py + _ny2 * _s2 * (s["d"] / 2 + 1.6)
                _b2 = box(s["name"] + "·桥台%d" % _s2, s["w"] + 1.2, 3.2, 0.40,
                          _bx, _by, 0.0, PL.MAT.get("stone2") or PL.MAT["stone"])
                _b2.rotation_euler[2] = _ang
        else:
            box(s["name"], s["w"], s["d"], s["h"], s["cx"], s["cy"], -0.4, MAT["stone"])
        continue
    add_struct(s)

# ------------------------------------------------------------------ 现代化改造（架空混合·推定）
if args.precise:
    glass = PL.MAT["glass"]
    metal = PL.MAT["metal"]
    # 金瓯殿南侧玻璃门厅 + 金属雨棚（三台前陛之下）
    # （金瓯殿前玻璃门厅已按作者意见删除）
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

if args.precise:
    try:
        import lg_look as _LK2
        # 光比：太阳与环境光从 3.0:1.0 调到 2.6:1.3。原来深色墙身进了阴影就"消失"，
        # 远看像墙缺了一段；提环境光、压一点太阳，阴影里的墙面才留得住信息。
        _LK2.setup_world(sc, "hdri_sky_sunny_2k.hdr", strength=1.30, az=228, elev=36,
                         fallback_sky=True)
        _LK2.setup_sun(sc, energy=2.60, az=228, elev=36)
        sun = bpy.data.objects.get("LG_Sun") or sun
        _LK2.setup_render(sc, res=args.res, samples=args.samples, exposure=-0.50)
        sc.view_settings.exposure = -0.50
    except Exception as _e2:
        print("LOOK setup failed:", _e2, flush=True)

sc.render.engine = "CYCLES"
sc.cycles.device = "GPU"
sc.cycles.samples = args.samples
sc.cycles.use_denoising = True
sc.cycles.max_bounces = 6
sc.render.image_settings.file_format = "PNG"
sc.view_settings.view_transform = "Standard"
if not args.precise:
    sc.view_settings.exposure = -0.2

# ------------------------------------------------------------------ 出图
AR = 16 / 9
shots = [
    ("鸟瞰·东南", dict(loc=(620, -760, 380), target=(0, -60, 0), lens=48)),
    ("鸟瞰·中轴", dict(loc=(90, -820, 175), target=(0, -70, 0), lens=58)),
    ("鸟瞰·内廷", dict(loc=(-520, -200, 380), target=(0, 120, 0), lens=50)),
    ("人视·金瓯殿", dict(loc=(178, -338, 24), target=(0, -150, 14), lens=42)),
    ("细部·外朝", dict(loc=(86, -320, 62), target=(0, -120, 20), lens=52)),
    ("正立面·正射", dict(loc=(0, -305, 26), target=(0, -60, 24), lens=72)),
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
def _join_by_material(target, max_verts=None):
    """按材质把对象合并成一个网格（导出用）。

    三次失败的教训：
      1. `bpy.ops.object.join()` 合 2.8 万对象要 15 分钟——每次调用都重算 depsgraph；
      2. 合并时逐个 `bpy.data.objects.remove()` 同样慢（8 分钟），
      3. 逐个 `bpy.data.meshes.remove()` 也是同样的问题。
    所以这里**先把所有组的数据读出来（纯 numpy，不碰场景）**，全部读完再一次性
    建对象、一次性 batch_remove 旧对象与旧网格——把 depsgraph 更新次数压到常数级。
    """
    import numpy as np
    groups = {}
    for ob in list(target.objects):
        if ob.type != "MESH" or len(ob.data.materials) != 1:
            continue
        if max_verts and len(ob.data.vertices) > max_verts:
            continue
        groups.setdefault(ob.data.materials[0].name, []).append(ob)
    jobs = []                       # (mat_name, verts, faces, mat, old_objects)
    for mat_name, obs in groups.items():
        if len(obs) < 2:
            continue
        vs, fs, off = [], [], 0
        for ob in obs:
            me = ob.data
            n = len(me.vertices)
            co = np.empty(n * 3, dtype=np.float64)
            me.vertices.foreach_get("co", co)
            co = co.reshape(-1, 3)
            mw = np.array(ob.matrix_world)
            vs.append(co @ mw[:3, :3].T + mw[:3, 3])
            lv = np.empty(len(me.loops), dtype=np.int32)
            me.loops.foreach_get("vertex_index", lv)
            lt = np.empty(len(me.polygons), dtype=np.int32)
            me.polygons.foreach_get("loop_total", lt)
            idx = (lv + off).tolist()
            p_ = 0
            for c in lt.tolist():
                fs.append(tuple(idx[p_:p_ + c]))
                p_ += c
            off += n
        jobs.append((mat_name, np.concatenate(vs, axis=0), fs,
                     obs[0].data.materials[0], obs))
    merged = 0
    old_obs, old_me = [], []
    for mat_name, allv, fs, mat, obs in jobs:
        new_me = bpy.data.meshes.new("M·" + mat_name)
        new_me.from_pydata(allv.tolist(), [], fs)
        new_me.materials.append(mat)
        target.objects.link(bpy.data.objects.new("M·" + mat_name, new_me))
        old_obs.extend(obs)
        old_me.extend(ob.data for ob in obs)
        merged += len(obs) - 1
    bpy.data.batch_remove(ids=old_obs)
    bpy.data.batch_remove(ids=[m for m in old_me if m.users == 0])
    return merged


def _glb_textured(src_name):
    """把程序化材质换成贴图版（glTF 不认 Brick/Wave/Noise，纯色交付等于丢材质）。

    返回 (材质, 立方投影边长)。没配到的返回 None，保持原样。
    """
    A = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    table = {
        "琉璃黄": ("tex_glazedtile_2k_diff.jpg", "tex_glazedtile_2k_rough.jpg", 3.2),
        "琉璃黄·暗": ("tex_glazedtile_2k_diff.jpg", "tex_glazedtile_2k_rough.jpg", 3.2),
        "琉璃黄·素面": ("tex_glazedtile_2k_diff.jpg", "tex_glazedtile_2k_rough.jpg", 3.2),
        "琉璃黄·素面暗": ("tex_glazedtile_2k_diff.jpg", "tex_glazedtile_2k_rough.jpg", 3.2),
        "汉白玉": ("tex_whitemarble_2k_diff.jpg", "tex_whitemarble_2k_rough.jpg", 2.4),
        "汉白玉·雕花": ("tex_whitemarble_2k_diff.jpg", "tex_whitemarble_2k_rough.jpg", 2.4),
        "石阶": ("tex_whitemarble_2k_diff.jpg", "tex_whitemarble_2k_rough.jpg", 2.0),
        "深色木": ("tex_wood_2k_diff.jpg", "tex_wood_2k_rough.jpg", 1.8),
        "隔扇": ("tex_wood_2k_diff.jpg", "tex_wood_2k_rough.jpg", 1.8),
        "朱红柱": ("tex_wood_2k_diff.jpg", "tex_wood_2k_rough.jpg", 2.2),
        "朱红墙": ("tex_greybrick_2k_diff.jpg", "tex_greybrick_2k_rough.jpg", 2.6),
        "城墙": ("tex_greybrick_2k_diff.jpg", "tex_greybrick_2k_rough.jpg", 2.6),
        "宫城地坪·石板": ("tex_greybrick_2k_diff.jpg", "tex_greybrick_2k_rough.jpg", 2.4),
        "御道·石板": ("tex_greybrick_2k_diff.jpg", "tex_greybrick_2k_rough.jpg", 2.4),
    }
    if src_name not in table:
        return None
    diff, rough, cube = table[src_name]
    if not os.path.exists(os.path.join(A, diff)):
        return None
    key = "GLBTEX·" + src_name
    m = bpy.data.materials.get(key)
    if m is None:
        m = bpy.data.materials.new(key)
        m.use_nodes = True
        nt = m.node_tree
        bsdf = nt.nodes.get("Principled BSDF")
        t1 = nt.nodes.new("ShaderNodeTexImage")
        t1.image = bpy.data.images.load(os.path.join(A, diff), check_existing=True)
        nt.links.new(t1.outputs["Color"], bsdf.inputs["Base Color"])
        t2 = nt.nodes.new("ShaderNodeTexImage")
        t2.image = bpy.data.images.load(os.path.join(A, rough), check_existing=True)
        t2.image.colorspace_settings.name = "Non-Color"
        nt.links.new(t2.outputs["Color"], bsdf.inputs["Roughness"])
        uv = nt.nodes.new("ShaderNodeUVMap")
        nt.links.new(uv.outputs["UV"], t1.inputs["Vector"])
        nt.links.new(uv.outputs["UV"], t2.inputs["Vector"])
    return (m, cube)


def _box_uv(ob, cube):
    """按面法线选投影轴生成米制立方投影 UV（numpy 向量化）。

    纯 Python 逐 loop 写 460 万个 UV 要几十分钟，`uv.cube_project` 算子更慢；
    这里全部用 foreach_get/foreach_set + numpy，秒级完成。
    """
    import numpy as np
    me = ob.data
    nv, ln, nf = len(me.vertices), len(me.loops), len(me.polygons)
    co = np.empty(nv * 3, dtype=np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    mw = np.array(ob.matrix_world)
    co = co @ mw[:3, :3].T + mw[:3, 3]
    lv = np.empty(ln, dtype=np.int32)
    me.loops.foreach_get("vertex_index", lv)
    pn = np.empty(nf * 3, dtype=np.float32)
    me.polygons.foreach_get("normal", pn)
    axis = np.argmax(np.abs(pn.reshape(-1, 3)), axis=1)
    lt = np.empty(nf, dtype=np.int32)
    me.polygons.foreach_get("loop_total", lt)
    fax = np.repeat(axis, lt)[:ln]
    c = co[lv]
    u = np.where(fax == 0, c[:, 1], c[:, 0])
    v = np.where(fax == 2, c[:, 1], c[:, 2])
    uv = np.stack([u / cube, v / cube], axis=1).astype(np.float32)
    lay = me.uv_layers.new(name="BoxUV")
    lay.data.foreach_set("uv", uv.ravel())


def _texturize(target):
    """给每个对象补立方投影 UV，并把大面材质换成贴图版。"""
    n_uv = n_mat = 0
    for ob in list(target.objects):
        if ob.type != "MESH" or not ob.data.materials:
            continue
        got = _glb_textured(ob.data.materials[0].name)
        if got is None:
            continue
        mat, cube = got
        if not ob.data.uv_layers:
            _box_uv(ob, cube)      # 纯 Python 立方投影：edit-mode 算子对百万面太慢
            n_uv += 1
        ob.data.materials[0] = mat
        n_mat += 1
    return n_uv, n_mat


glb = os.path.join(WORK, "palace_massing.glb")
if not args.no_glb:
    import time as _tm
    _t0 = _tm.time()
    _n_merged = _join_by_material(col)
    print("JOINED", _n_merged, "objects ->", len(col.objects),
          "in %.1fs" % (_tm.time() - _t0))
    if args.glb_textures:
        _u, _m = _texturize(col)
        print("TEXTURIZED uv_added=%d mats=%d" % (_u, _m))
    bpy.ops.export_scene.gltf(
        filepath=glb, export_format="GLB", export_apply=True,
        export_draco_mesh_compression_enable=True,
        export_draco_mesh_compression_level=4)
glb_lite = None
if args.precise and not args.no_glb:      # 轻量 glb：剔掉斗拱/值房/树/城墙等重复件，便于网页加载
    for ob in list(col.objects):
        if ob.name.split("·")[0].startswith(("斗拱", "值房", "树", "城墙", "角楼", "三台·望柱")):
            bpy.data.objects.remove(ob, do_unlink=True)
    for ob in col.objects:
        if ob.type == "MESH":
            dm = ob.modifiers.new("dec", "DECIMATE")
            dm.ratio = 0.28
    glb_lite = os.path.join(WORK, "palace_precise_lite.glb")
    _join_by_material(col)
    bpy.ops.export_scene.gltf(
        filepath=glb_lite, export_format="GLB", export_apply=True,
        export_draco_mesh_compression_enable=True,
        export_draco_mesh_compression_level=4)

tris = 0
for o in col.objects:
    if o.type == "MESH":
        o.data.calc_loop_triangles()
        tris += len(o.data.loop_triangles)

print("RESULT " + json.dumps({
    "renders": results, "objects": len(col.objects), "triangles": tris,
    "blend": blend, "glb": glb, "glb_mb": round(os.path.getsize(glb) / 1e6, 2) if os.path.exists(glb) else None,
}, ensure_ascii=False))
