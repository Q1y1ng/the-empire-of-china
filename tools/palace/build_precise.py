"""金瓯殿 · 明官式精模（单殿、构件级）—— Blender 5.x 无头脚本

与体量白模（build_massing.py）分开：白模看格局，精模看做法。
按明官式（清式做法简化）生成：须弥座台基、踏跺、栏杆、柱网、额枋、平板枋、斗拱带、
重檐庑殿顶（下檐环屋面 + 上檐举折曲面 + 瓦垄 + 正脊垂脊吻）、隔扇门窗、彩画额枋、匾额。

用法：
    blender -b --factory-startup -P build_precise.py -- --out OUT [--samples 160] [--res 2000] [--only 正立面]

尺寸（与 palace_data 的金瓯殿一致）：面阔 11 间 90 m，进深 5 间 50 m；台基 3.2 m、檐柱 12 m、
下檐口 17.4 m、围脊 21.0 m、上檐口 25.9 m、正脊 33.5 m（总高约 33.5 m，太和殿 35.05 m 量级）。
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

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default=os.path.join(HERE, "..", "..", "docs", "assets"))
ap.add_argument("--samples", type=int, default=160)
ap.add_argument("--res", type=int, default=2000)
ap.add_argument("--only", default="")
args = ap.parse_args(argv)
WORK = os.path.join(os.environ.get("TEMP", HERE), "palace_precise")
os.makedirs(WORK, exist_ok=True)
os.makedirs(args.out, exist_ok=True)

# ------------------------------------------------------------------ 尺寸
BAYS = [7.0, 7.5, 8.0, 8.5, 9.0, 10.0, 9.0, 8.5, 8.0, 7.5, 7.0]   # 11 间
DBAYS = [9.0, 12.0, 18.0, 12.0, 9.0]                               # 5 进
W, D = sum(BAYS), sum(DBAYS)          # 90 × 60? DBAYS 合计 60，但殿身 50 → 用 50 取中三间
D = 50.0
DBAYS = [8.0, 9.5, 15.0, 9.5, 8.0]    # 50 m

BASE_H = 3.2
COL_H = 12.0
PLATE = 0.95
PING = 0.30
DG_H = 0.62
EAVE_LO = BASE_H + COL_H + PLATE + PING + DG_H + 0.35      # ≈ 17.42
RING_Z = 23.0                                              # 围脊 / 上檐柱脚
UP_COL_TOP = 26.0
EAVE_HI = 28.2
RIDGE_Z = 37.4
UP_W, UP_D = 70.0, 40.0                                    # 上檐身

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.unit_settings.system = "METRIC"
sc.unit_settings.scale_length = 1.0
col = sc.collection


def material(name, rgb, rough=0.8, metal=0.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


MAT = dict(
    tile=material("琉璃黄", (0.66, 0.38, 0.05), 0.40),
    tile2=material("琉璃黄·暗", (0.50, 0.28, 0.04), 0.45),
    column=material("朱红柱", (0.44, 0.08, 0.06), 0.6),
    wall=material("朱红墙", (0.40, 0.07, 0.06), 0.9),
    stone=material("汉白玉", (0.82, 0.80, 0.74), 0.65),
    stone2=material("石阶", (0.74, 0.72, 0.66), 0.8),
    cai_blue=material("彩画青", (0.05, 0.20, 0.32), 0.6),
    cai_green=material("彩画绿", (0.05, 0.22, 0.16), 0.6),
    gold=material("金", (0.74, 0.56, 0.16), 0.32, 0.9),
    dou=material("斗拱", (0.26, 0.30, 0.27), 0.7),
    door=material("隔扇", (0.19, 0.08, 0.05), 0.7),
    lattice=material("格心", (0.26, 0.13, 0.07), 0.7),
    plaque=material("匾", (0.10, 0.12, 0.18), 0.5),
)


def box(name, w, d, h, x, y, z0=0.0, mat=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, z0 + h / 2))
    ob = bpy.context.object
    ob.name = name
    ob.scale = (w, d, h)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        ob.data.materials.append(mat)
    return ob


def mesh_from(name, verts, faces, mat=None, smooth=False):
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
    if smooth:
        for p in ob.data.polygons:
            p.use_smooth = True
    return ob


# ------------------------------------------------------------------ 台基 / 栏杆 / 踏跺
def build_base():
    tiers = [("圭角", W + 8.4, D + 8.4, 0.55, 0.0, MAT["stone"]),
             ("下枋", W + 7.2, D + 7.2, 0.45, 0.55, MAT["stone"]),
             ("束腰", W + 5.4, D + 5.4, 1.15, 1.00, MAT["stone2"]),
             ("上枋", W + 7.2, D + 7.2, 0.55, 2.15, MAT["stone"]),
             ("台面", W + 7.8, D + 7.8, 0.50, 2.70, MAT["stone"])]
    for nm, w, d, h, z, m in tiers:
        box("台基·" + nm, w, d, h, 0, 0, z, m)

    stair_w, n = 20.0, 9
    for i in range(n):
        top = BASE_H * (i + 1) / n
        box(f"踏跺{i}", stair_w, 0.95, top, 0, -D / 2 - 4.0 - i * 0.95, 0.0, MAT["stone2"])
    box("御路", 4.4, 4.6, 0.22, 0, -D / 2 - 4.2, BASE_H - 0.45, MAT["stone"])

    for side in ("S", "N", "E", "W"):
        if side in ("S", "N"):
            length, n_post = W + 7.8, 17
            y = (D + 7.8) / 2 * (1 if side == "N" else -1)
            for i in range(n_post + 1):
                x = -length / 2 + i * length / n_post
                if side == "S" and abs(x) < stair_w / 2 + 1.2:
                    continue
                box(f"望柱{side}{i}", 0.34, 0.34, 1.18, x, y, BASE_H, MAT["stone"])
                if i < n_post:
                    x2 = -length / 2 + (i + 1) * length / n_post
                    if side == "S" and abs(x2) < stair_w / 2 + 1.2:
                        continue
                    box(f"栏板{side}{i}", length / n_post - 0.34, 0.16, 0.86,
                        (x + x2) / 2, y, BASE_H + 0.18, MAT["stone"])
        else:
            length, n_post = D + 7.8, 11
            x = (W + 7.8) / 2 * (1 if side == "E" else -1)
            for i in range(n_post + 1):
                y = -length / 2 + i * length / n_post
                box(f"望柱{side}{i}", 0.34, 0.34, 1.18, x, y, BASE_H, MAT["stone"])
                if i < n_post:
                    y2 = -length / 2 + (i + 1) * length / n_post
                    box(f"栏板{side}{i}", 0.16, length / n_post - 0.34, 0.86,
                        x, (y + y2) / 2, BASE_H + 0.18, MAT["stone"])


# ------------------------------------------------------------------ 柱 / 额枋 / 斗拱
def edges(bays):
    out = [-sum(bays) / 2]
    for b in bays:
        out.append(out[-1] + b)
    return out


def column(name, x, y, z0, z1, r=0.46):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=z1 - z0, vertices=16,
                                        location=(x, y, (z0 + z1) / 2))
    ob = bpy.context.object
    ob.name = name
    ob.data.materials.append(MAT["column"])
    return ob


def build_columns():
    xs, ys = edges(BAYS), edges(DBAYS)
    z0, z1 = BASE_H, BASE_H + COL_H
    for x in xs:
        for y in (ys[0], ys[-1]):
            column("檐柱", x, y, z0, z1)
    for y in ys[1:-1]:
        for x in (xs[0], xs[-1]):
            column("檐柱", x, y, z0, z1)


def ring_beam(name, w, d, z, h, t, mat):
    box(name + "_S", w, t, h, 0, -d / 2, z, mat)
    box(name + "_N", w, t, h, 0, d / 2, z, mat)
    box(name + "_E", t, d, h, w / 2, 0, z, mat)
    box(name + "_W", t, d, h, -w / 2, 0, z, mat)


def build_beams():
    z = BASE_H + COL_H
    xs, ys = edges(BAYS), edges(DBAYS)
    for i in range(len(xs) - 1):
        x, bw = (xs[i] + xs[i + 1]) / 2, xs[i + 1] - xs[i] - 0.92
        m = MAT["cai_blue"] if i % 2 == 0 else MAT["cai_green"]
        box(f"额枋S{i}", bw, 0.55, PLATE, x, -D / 2, z, m)
        box(f"额枋N{i}", bw, 0.55, PLATE, x, D / 2, z, m)
    for i in range(len(ys) - 1):
        y, bw = (ys[i] + ys[i + 1]) / 2, ys[i + 1] - ys[i] - 0.92
        m = MAT["cai_blue"] if i % 2 == 0 else MAT["cai_green"]
        box(f"额枋E{i}", 0.55, bw, PLATE, W / 2, y, z, m)
        box(f"额枋W{i}", 0.55, bw, PLATE, -W / 2, y, z, m)
    ring_beam("平板枋", W + 1.0, D + 1.0, z + PLATE, PING, 0.72, MAT["wall"])


def dougong_data():
    verts, faces = [], []

    def bx(x0, x1, y0, y1, z0, z1):
        b = len(verts)
        for zz in (z0, z1):
            for (xx, yy) in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
                verts.append((xx, yy, zz))
        faces.extend([(b, b + 1, b + 5, b + 4), (b + 1, b + 2, b + 6, b + 5),
                      (b + 2, b + 3, b + 7, b + 6), (b + 3, b, b + 4, b + 7),
                      (b + 4, b + 5, b + 6, b + 7)])

    bx(-0.22, 0.22, -0.22, 0.22, 0.0, 0.22)
    bx(-0.78, 0.78, -0.11, 0.11, 0.22, 0.40)
    bx(-0.11, 0.11, -0.78, 0.78, 0.24, 0.42)
    bx(-0.98, 0.98, -0.10, 0.10, 0.42, 0.56)
    bx(-0.16, 0.16, -0.70, 0.10, 0.38, 0.62)
    me = bpy.data.meshes.new("dougong")
    me.from_pydata(verts, [], faces)
    me.validate()
    me.materials.append(MAT["dou"])
    return me


def build_dougong(w, d, z, spacing=1.85):
    me = dougong_data()
    nx, ny = max(int(w // spacing), 4), max(int(d // spacing), 3)

    def put(x, y, rot):
        ob = bpy.data.objects.new("斗拱", me)
        col.objects.link(ob)
        ob.location = (x, y, z)
        ob.rotation_euler[2] = rot

    for i in range(nx + 1):
        x = -w / 2 + i * w / nx
        put(x, -d / 2, 0)
        put(x, d / 2, 0)
    for i in range(1, ny):
        y = -d / 2 + i * d / ny
        put(-w / 2, y, math.pi / 2)
        put(w / 2, y, math.pi / 2)


# ------------------------------------------------------------------ 屋顶
def corr(x, amp):
    return amp * math.cos(2 * math.pi * x / 0.62)


def solidify(ob, thickness=0.55):
    """给屋顶加厚度：外面琉璃、里面暗色椽望。"""
    ob.data.materials.append(material("椽望", (0.10, 0.075, 0.07), 0.9))
    m = ob.modifiers.new("solid", "SOLIDIFY")
    m.thickness = thickness
    m.offset = -1.0
    m.material_offset = 1
    m.material_offset_rim = 1
    clear_ctx = {"object": ob}
    return ob


def hip_roof(name, w, d, z_eave, h, step=0.55, mat=None):
    """上檐：整片庑殿曲面（举折 + 瓦垄 + 翼角起翘）。"""
    mat = mat or MAT["tile"]
    L = max(w - d, 0.18 * w)

    def f(x, y):
        t = min(max(max(abs(y), max(abs(x) - L / 2, 0.0)) / (d / 2), 0.0), 1.0)
        z = h * (1.0 - t) ** 1.32
        amp = 0.115 * (0.30 + 0.70 * t)
        z += corr(x if abs(x) <= L / 2 else y, amp)
        z += 0.5 * max(0.0, (abs(x) / (w / 2)) * (abs(y) / (d / 2))) ** 6
        return z_eave + z

    nx = int(w / step)
    ny = int(d / step)
    verts, faces = [], []
    for j in range(ny + 1):
        y = -d / 2 + j * d / ny
        for i in range(nx + 1):
            x = -w / 2 + i * w / nx
            verts.append((x, y, f(x, y)))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    ob = mesh_from(name, verts, faces, mat, smooth=True)
    solidify(ob)
    return ob


def ring_roof(name, ow, od, iw, id_, z0, h, mat=None, nu=44, nv=8):
    """下檐：环屋面（外檐口→内围脊），四坡拼合。"""
    mat = mat or MAT["tile"]
    patches = [
        ((-ow / 2, -od / 2), (ow / 2, -od / 2), (iw / 2, -id_ / 2), (-iw / 2, -id_ / 2)),
        ((ow / 2, od / 2), (-ow / 2, od / 2), (-iw / 2, id_ / 2), (iw / 2, id_ / 2)),
        ((ow / 2, -od / 2), (ow / 2, od / 2), (iw / 2, id_ / 2), (iw / 2, -id_ / 2)),
        ((-ow / 2, od / 2), (-ow / 2, -od / 2), (-iw / 2, -id_ / 2), (-iw / 2, id_ / 2)),
    ]
    verts, faces = [], []
    for (a, b, c, dd) in patches:
        base = len(verts)
        for j in range(nv + 1):
            v = j / nv
            z = z0 + h * v ** 1.35
            for i in range(nu + 1):
                u = i / nu
                ax, ay = a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u
                dx, dy = dd[0] + (c[0] - dd[0]) * u, dd[1] + (c[1] - dd[1]) * u
                x, y = ax + (dx - ax) * v, ay + (dy - ay) * v
                amp = 0.115 * (0.35 + 0.65 * v)
                verts.append((x, y, z + corr(u * math.hypot(b[0] - a[0], b[1] - a[1]) * 0.62, amp)))
        for j in range(nv):
            for i in range(nu):
                p = base + j * (nu + 1) + i
                faces.append((p, p + 1, p + nu + 2, p + nu + 1))
    ob = mesh_from(name, verts, faces, mat, smooth=True)
    solidify(ob)
    return ob


def ridges(ow, od, z_eave, h, ridge_len):
    box("正脊", ridge_len + 1.6, 1.0, 1.3, 0, 0, z_eave + h - 0.15, MAT["tile2"])
    for s in (-1, 1):
        box(f"鸱吻{s}", 1.2, 0.95, 2.0, s * (ridge_len / 2 + 0.85), 0, z_eave + h - 0.05, MAT["gold"])
    hw, hd = ow / 2, od / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            x0, y0 = sx * ridge_len / 2, 0.0
            x1, y1 = sx * hw, sy * hd
            seg_n = 8
            for i in range(seg_n):
                t0, t1 = i / seg_n, (i + 1) / seg_n
                xa, ya = x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0
                xb, yb = x0 + (x1 - x0) * t1, y0 + (y1 - y0) * t1
                za = z_eave + h * (1 - t0) ** 1.32 - 0.9
                zb = z_eave + h * (1 - t1) ** 1.32 - 0.9
                seg = math.hypot(xb - xa, yb - ya)
                ob = box(f"垂脊{sx}{sy}{i}", seg + 0.25, 0.5, 0.7,
                         (xa + xb) / 2, (ya + yb) / 2, (za + zb) / 2, MAT["tile2"])
                ob.rotation_euler[2] = math.atan2(yb - ya, xb - xa)


# ------------------------------------------------------------------ 门窗 / 匾额
def lattice_bay(name, w, h, x, y, z0, rot=0.0):
    verts, faces = [], []

    def bx(x0, x1, z0_, z1_, y0, y1):
        b = len(verts)
        for yy in (y0, y1):
            for (xx, zz) in ((x0, z0_), (x1, z0_), (x1, z1_), (x0, z1_)):
                verts.append((xx, yy, zz))
        faces.extend([(b, b + 1, b + 5, b + 4), (b + 1, b + 2, b + 6, b + 5),
                      (b + 2, b + 3, b + 7, b + 6), (b + 3, b, b + 4, b + 7),
                      (b + 4, b + 5, b + 6, b + 7)])

    hw, y0, y1 = w / 2, -0.06, 0.06
    bx(-hw, hw, 0.0, h, y0, y1)                      # 门芯板
    for i in range(6):                                # 竖向棂条
        xx = -hw + (i + 1) * w / 7
        bx(xx - 0.05, xx + 0.05, h * 0.36, h * 0.96, y0 - 0.035, y1 + 0.035)
    for j in range(7):                                # 横向棂条
        zz = h * 0.36 + (j + 1) * h * 0.60 / 8
        bx(-hw, hw, zz - 0.05, zz + 0.05, y0 - 0.035, y1 + 0.035)
    bx(-hw, hw, h * 0.16, h * 0.34, y0 - 0.02, y1 + 0.02)   # 裙板
    ob = mesh_from(name, verts, faces, MAT["door"])
    ob.location = (x, y, z0)
    ob.rotation_euler[2] = rot
    return ob


def build_doors():
    xs, ys = edges(BAYS), edges(DBAYS)
    z0, h = BASE_H, 8.2
    for i in range(len(xs) - 1):
        bw = xs[i + 1] - xs[i] - 1.05
        cx = (xs[i] + xs[i + 1]) / 2
        lattice_bay(f"隔扇S{i}", bw, h, cx, -D / 2 + 0.16, z0)
        lattice_bay(f"隔扇N{i}", bw, h, cx, D / 2 - 0.16, z0)
        box(f"横披S{i}", bw, 0.14, 3.2, cx, -D / 2 + 0.16, z0 + h, MAT["lattice"])
        box(f"横披N{i}", bw, 0.14, 3.2, cx, D / 2 - 0.16, z0 + h, MAT["lattice"])
    for i in range(len(ys) - 1):
        bw = ys[i + 1] - ys[i] - 1.05
        cy = (ys[i] + ys[i + 1]) / 2
        lattice_bay(f"隔扇E{i}", bw, h, W / 2 - 0.16, cy, z0, rot=math.pi / 2)
        lattice_bay(f"隔扇W{i}", bw, h, -W / 2 + 0.16, cy, z0, rot=math.pi / 2)


def build_plaque():
    z = BASE_H + COL_H - 3.4
    box("匾框", 5.2, 0.30, 2.1, 0, -D / 2 - 0.10, z - 0.2, MAT["gold"])
    box("匾额", 4.7, 0.34, 1.72, 0, -D / 2 - 0.14, z, MAT["plaque"])
    cu = bpy.data.curves.new("匾文", type="FONT")
    cu.body = "金瓯殿"
    cu.size = 1.06
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.extrude = 0.035
    for p in (r"C:\Windows\Fonts\simhei.ttf", r"C:\Windows\Fonts\msyh.ttc"):
        if os.path.exists(p):
            try:
                cu.font = bpy.data.fonts.load(p)
                break
            except Exception:
                pass
    ob = bpy.data.objects.new("匾文", cu)
    col.objects.link(ob)
    ob.location = (0, -D / 2 - 0.36, z)
    ob.rotation_euler = (math.pi / 2, 0, 0)
    ob.data.materials.append(MAT["gold"])
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.convert(target="MESH")


# ------------------------------------------------------------------ 组装
build_base()
build_columns()
build_beams()
build_dougong(W + 1.0, D + 1.0, BASE_H + COL_H + PLATE + PING)
build_doors()
build_plaque()

# 下檐环屋面：外檐口 (W+8, D+8) @ EAVE_LO → 内围脊 @ RING_Z
ring_roof("下檐", W + 8, D + 8, UP_W + 1.2, UP_D + 1.2, EAVE_LO, RING_Z - EAVE_LO)
box("围脊S", UP_W + 3.4, 0.85, 0.85, 0, -(UP_D / 2 + 0.6), RING_Z, MAT["tile2"])
box("围脊N", UP_W + 3.4, 0.85, 0.85, 0, (UP_D / 2 + 0.6), RING_Z, MAT["tile2"])
box("围脊E", 0.85, UP_D + 1.2, 0.85, UP_W / 2 + 0.6, 0, RING_Z, MAT["tile2"])
box("围脊W", 0.85, UP_D + 1.2, 0.85, -(UP_W / 2 + 0.6), 0, RING_Z, MAT["tile2"])

# 上檐身：从下檐额枋顶一直到 26.0 m（23.4—25.8 为槛窗带）
box("上檐身", UP_W - 2, UP_D - 2, 26.0 - (BASE_H + COL_H + PLATE), 0, 0,
    BASE_H + COL_H + PLATE, MAT["wall"])
for sgn, nm in ((1, "S"), (-1, "N")):
    box(f"上檐窗{nm}", UP_W - 6, 0.16, 2.4, 0, sgn * (UP_D / 2 - 1.0), 23.4, MAT["lattice"])
for sgn, nm in ((1, "E"), (-1, "W")):
    box(f"上檐窗{nm}", 0.16, UP_D - 6, 2.4, sgn * (UP_W / 2 - 1.0), 0, 23.4, MAT["lattice"])

# 上檐额枋、平板枋、斗拱
ring_beam("上檐额枋", UP_W - 2, UP_D - 2, 26.0, 0.9, 0.85, MAT["cai_blue"])
ring_beam("上檐平板枋", UP_W - 1.1, UP_D - 1.1, 26.9, 0.26, 0.7, MAT["wall"])
build_dougong(UP_W - 1.1, UP_D - 1.1, 27.16)

# 上檐庑殿顶
hip_roof("上檐", UP_W + 6, UP_D + 6, EAVE_HI, RIDGE_Z - EAVE_HI)
ridges(UP_W + 6, UP_D + 6, EAVE_HI, RIDGE_Z - EAVE_HI, (UP_W + 6) - (UP_D + 6))

# 地面
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
g = bpy.context.object
g.name = "ground"
g.scale = (400, 400, 1)
g.data.materials.append(material("广场砖", (0.52, 0.50, 0.45), 0.95))

# ------------------------------------------------------------------ 相机 / 灯光
cam_data = bpy.data.cameras.new("Cam")
cam_data.clip_start = 0.5
cam_data.clip_end = 6000
cam = bpy.data.objects.new("Cam", cam_data)
col.objects.link(cam)
sc.camera = cam


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


sun_d = bpy.data.lights.new("Sun", type="SUN")
sun_d.energy = 3.1
sun_d.angle = math.radians(3)
sun = bpy.data.objects.new("Sun", sun_d)
col.objects.link(sun)
sun.rotation_euler = (math.radians(40), 0, math.radians(220))

sc.world = bpy.data.worlds.new("World")
sc.world.use_nodes = True
bg = sc.world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.58, 0.70, 0.88, 1.0)
bg.inputs[1].default_value = 0.55

sc.render.engine = "CYCLES"
sc.cycles.device = "GPU"
sc.cycles.samples = args.samples
sc.cycles.use_denoising = True
sc.cycles.max_bounces = 6
sc.render.image_settings.file_format = "PNG"
sc.view_settings.view_transform = "Standard"
sc.view_settings.exposure = -0.15

shots = [
    ("正立面", dict(loc=(0, -250, 14), target=(0, 0, 20), lens=50)),
    ("鸟瞰", dict(loc=(150, -195, 112), target=(0, 0, 18), lens=45)),
    ("细部·檐下", dict(loc=(16, -48, 7), target=(16, -28, 17), lens=55)),
    ("细部·屋顶", dict(loc=(58, -62, 46), target=(8, 0, 33), lens=70)),
]

results = {}
for name, s in shots:
    if args.only and args.only not in name:
        continue
    cam.location = s["loc"]
    cam_data.lens = s["lens"]
    look_at(cam, s["target"])
    sc.render.resolution_x = args.res
    sc.render.resolution_y = int(args.res * 9 / 16)
    path = os.path.join(WORK, f"jinol_{name}.png")
    sc.render.filepath = path
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    results[name] = {"s": round(time.time() - t0, 1), "bytes": os.path.getsize(path)}
    print("RENDER", name, results[name])

blend = os.path.join(WORK, "jinol_hall.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend)
glb = os.path.join(WORK, "jinol_hall.glb")
bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", export_apply=True)

tri = 0
for o in col.objects:
    if o.type == "MESH":
        o.data.calc_loop_triangles()
        tri += len(o.data.loop_triangles)
print("RESULT " + json.dumps({"renders": results, "objects": len(col.objects),
                              "triangles": tri, "blend": blend, "glb": glb,
                              "glb_mb": round(os.path.getsize(glb) / 1e6, 2)},
                             ensure_ascii=False))
