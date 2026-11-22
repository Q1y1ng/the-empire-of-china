"""万人大礼堂 —— 3D 白模与精模（Blender 5.x 无头）。

数据全部来自 hall_data.py；坐标与宫城/广场模型一致（宫城平面中心为原点）。

用法：
    blender -b --factory-startup -P build_hall.py -- \\
        --out <输出目录> [--samples 64] [--res 1920] [--only 池座] [--cpu]
    ... -- --precise --draco        # 精模：材质贴图、座席、国徽、灯槽、铜门

产物：
    <out>/国家广场(2026)·万人大礼堂·白模·*.webp  + ·白模.glb
    <out>/国家广场(2026)·万人大礼堂·精模·*.webp  + ·精模.glb
"""

import argparse
import json
import math
import os
import sys
import time

import bpy
import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hall_data as D  # noqa: E402
import hall_tex as TX  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default=os.path.join(HERE, "..", "..", "docs", "assets"))
ap.add_argument("--samples", type=int, default=64)
ap.add_argument("--res", type=int, default=1920)
ap.add_argument("--only", default="", help="只渲染名字含该串的机位（逗号分隔可多个）")
ap.add_argument("--no-glb", action="store_true")
ap.add_argument("--cpu", action="store_true")
ap.add_argument("--draco", action="store_true")
ap.add_argument("--precise", action="store_true", help="精模")
ap.add_argument("--check", action="store_true", help="Workbench 几何校对")
ap.add_argument("--exposure", type=float, default=None)
ap.add_argument("--exposures", default="", help="曝光扫描，逗号分隔")
ap.add_argument("--cut", action="store_true", help="沿中轴切开（纵剖图）")
args = ap.parse_args(argv)
args.out = os.path.abspath(args.out)
P = args.precise

WORK = os.path.join(os.environ.get("TEMP", HERE), "grandhall")
os.makedirs(WORK, exist_ok=True)
os.makedirs(args.out, exist_ok=True)

FX, FY = D.FOCUS["x"], D.FOCUS["y"]
HX0, HX1 = D.HALL["x_front"], D.HALL["x_rear"]
AX = D.AXIS_Y

# ------------------------------------------------------------------ 场景
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.unit_settings.system = "METRIC"
sc.unit_settings.scale_length = 1.0
col = sc.collection

WHITE = P is False


def mat(name, rgb, rough=0.8, metal=0.0, emit=None, emit_str=1.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit is not None:
        b.inputs["Emission Color"].default_value = (*emit, 1.0)
        b.inputs["Emission Strength"].default_value = emit_str
    return m


L = D.srgb_lin
if WHITE:
    MAT = {
        "floor": mat("白模·地", (0.52, 0.51, 0.49), 0.9),
        "wall": mat("白模·墙", (0.74, 0.73, 0.70), 0.9),
        "ceil": mat("白模·顶", (0.80, 0.79, 0.76), 0.9,
                    emit=(0.95, 0.93, 0.88), emit_str=0.55),
        "seat": mat("白模·席", (0.62, 0.61, 0.58), 0.9),
        "stage": mat("白模·台", (0.68, 0.67, 0.64), 0.9),
        "gold": mat("白模·饰", (0.70, 0.69, 0.66), 0.85),
        "dark": mat("白模·暗", (0.30, 0.29, 0.28), 0.9),
        "lamp": mat("白模·灯", (0.9, 0.9, 0.88), 0.5, emit=(1.0, 0.97, 0.9),
                    emit_str=6.0),
        "dome": mat("白模·穹顶光", (0.86, 0.85, 0.82), 0.9,
                    emit=(1.0, 0.98, 0.94), emit_str=1.10),
        "soffit": mat("白模·楼座底", (0.82, 0.81, 0.78), 0.9,
                      emit=(1.0, 0.97, 0.92), emit_str=1.45),
    }
else:
    MAT = {
        "floor": mat("桃红大理石", L(D.SRGB["rose_marble"]), 0.22),
        "wall": mat("汉白玉", L(D.SRGB["white_marble"]), 0.32),
        "ceil": mat("顶棚石膏", L(D.SRGB["plaster"]), 0.65),
        "seat": mat("座椅织物", L(D.SRGB["imperial_red"]), 0.85),
        "stage": mat("台面木", L(D.SRGB["wood"]), 0.45),
        "gold": mat("金饰", L(D.SRGB["gold"]), 0.28, metal=0.95),
        "dark": mat("深色金属", (0.045, 0.042, 0.038), 0.4, metal=0.7),
        "lamp": mat("灯具", (1.0, 0.95, 0.85), 0.4, emit=(1.0, 0.93, 0.80),
                    emit_str=18.0),
        "red": mat("地毯·帝国红", L(D.SRGB["imperial_red"]), 0.95),
        "bronze": mat("铜门", L(D.SRGB["bronze"]), 0.35, metal=0.9),
        "marble_w": mat("汉白玉柱", L(D.SRGB["white_marble"]), 0.28),
    }


if not WHITE:
    MAT["dome"] = MAT["ceil"]
    MAT["soffit"] = MAT["ceil"]

# 精模：把程序化材质换成烘好的可平铺贴图（glTF 不认节点）
TEXTURE_TILES = TX.setup(MAT, os.path.join(HERE, "tex")) if P else {}


# ------------------------------------------------------------------ 网格累加器
class Mesh:
    """把成千上万个小块累进一个 bpy 网格，避免 1 万个物体拖垮导出。"""

    def __init__(self, name, material, group="hall"):
        self.name = name
        self.mat = material
        self.v = []
        self.f = []
        self.group = group

    def add(self, verts, faces):
        o = len(self.v)
        self.v.extend(verts)
        self.f.extend([tuple(i + o for i in fc) for fc in faces])

    # ---- 基本体
    def box(self, cx, cy, cz, w, d, h, rz=0.0):
        hw, hd = w / 2.0, d / 2.0
        pts = [(-hw, -hd, 0), (hw, -hd, 0), (hw, hd, 0), (-hw, hd, 0),
               (-hw, -hd, h), (hw, -hd, h), (hw, hd, h), (-hw, hd, h)]
        if rz:
            c, s = math.cos(rz), math.sin(rz)
            pts = [(x * c - y * s, x * s + y * c, z) for (x, y, z) in pts]
        self.add([(x + cx, y + cy, z + cz) for (x, y, z) in pts],
                 [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
                  (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])

    def quad(self, p0, p1, p2, p3):
        self.add([p0, p1, p2, p3], [(0, 1, 2, 3)])

    def cyl(self, cx, cy, z0, z1, r, n=16, r1=None):
        r1 = r if r1 is None else r1
        lo = [(cx + r * math.cos(2 * math.pi * i / n),
               cy + r * math.sin(2 * math.pi * i / n), z0) for i in range(n)]
        hi = [(cx + r1 * math.cos(2 * math.pi * i / n),
               cy + r1 * math.sin(2 * math.pi * i / n), z1) for i in range(n)]
        self.add(lo + hi, [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))] +
                 [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)])

    # ---- 生成物体
    def build(self, want=None):
        if not self.f:
            return None
        me = bpy.data.meshes.new(self.name)
        me.from_pydata(self.v, [], self.f)
        me.validate(clean_customdata=False)
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        if want is not None:
            tot = Vector((0.0, 0.0, 0.0))
            for f in bm.faces:
                tot += f.normal
            if tot.dot(Vector(want)) < 0:
                bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
        me.update()
        ob = bpy.data.objects.new(self.name, me)
        ob.data.materials.append(self.mat)
        col.objects.link(ob)
        ob["group"] = self.group
        print(f"  {self.name}: {len(me.vertices)} v / {len(me.polygons)} f", flush=True)
        return ob


OBJECTS = []


def emit(m: Mesh, want=None):
    ob = m.build(want)
    if ob:
        OBJECTS.append(ob)
    return ob


# ------------------------------------------------------------------ 通用几何
def hall_half_width(x):
    t = (x - HX0) / D.HALL["depth"]
    return D.HALL["w_front"] / 2 + t * (D.HALL["w_rear"] - D.HALL["w_front"]) / 2


def r_of(x, y):
    return math.hypot(x - FX, y - FY)


def theta_of(x, y):
    return math.atan2(y - FY, x - FX)


def in_hall(x, y, grow=0.0):
    """点是否在观众厅平面内；grow 为外扩量（补齐网格边缘锯齿缝）。"""
    if not (HX0 - grow <= x <= HX1 + grow):
        return False
    return abs(y - AX) <= hall_half_width(x) + grow


def hall_radius(th):
    """自扇心沿 th 方向到观众厅边界的距离（梯形四边求交）。"""
    dx, dy = math.cos(th), math.sin(th)
    poly = D.hall_plan()
    ts = []
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        ex, ey = x2 - x1, y2 - y1
        den = dx * ey - dy * ex
        if abs(den) < 1e-12:
            continue
        t = ((x1 - FX) * ey - (y1 - FY) * ex) / den
        u = ((x1 - FX) * dy - (y1 - FY) * dx) / den
        if t > 0 and -1e-9 <= u <= 1 + 1e-9:
            ts.append(t)
    # 扇心在观众厅之外（台口以西 30 m），一条射线先进后出，取**出射**那一点
    return max(ts) if ts else 0.0


def fan_surface(mesh, tier, zoff=0.0, up=True, n_th=260, n_s=10):
    """沿 (r, θ) 铺一层楼板：前缘取 U 形前缘曲线、外缘取厅墙，边线精确无锯齿。"""
    wrap = tier.get("wrap", 0.0)
    r0 = tier["r0"]
    tref = tier.get("theta_ref", 0.5)
    th_lo, th_hi = -0.95, 0.95
    r_first = D.tier_rows(tier)[0]["r"]          # 该层最前一排座席
    grid = []
    for i in range(n_th + 1):
        th = th_lo + (th_hi - th_lo) * i / n_th
        rf = r0 - wrap * (th / tref) ** 2 if wrap > 0 else r0
        rs = max(rf, r_first)
        re = hall_radius(th)
        if re <= rs + 0.2:
            grid.append(None)
            continue
        col = []
        for j in range(n_s + 1):
            r = rs + (re - rs) * j / n_s
            x, y = FX + r * math.cos(th), FY + r * math.sin(th)
            col.append((x, y, tier_z(tier, x, y) + zoff))
        grid.append(col)
    for i in range(n_th):
        a, b = grid[i], grid[i + 1]
        if not a or not b:
            continue
        for j in range(n_s):
            p00, p10 = a[j], b[j]
            p11, p01 = b[j + 1], a[j + 1]
            if up:
                mesh.add([p00, p10, p11, p01], [(0, 1, 2, 3)])
            else:
                mesh.add([p00, p01, p11, p10], [(0, 1, 2, 3)])


def tier_front_r(tier, th):
    """U 形挑台前缘半径。"""
    r0 = tier["r0"]
    wrap = tier.get("wrap", 0.0)
    if wrap <= 0:
        return 0.0
    return r0 - wrap * (th / tier.get("theta_ref", 0.5)) ** 2


def tier_has(tier, x, y):
    """该层楼板在 (x, y) 处是否存在：U 形前缘以外一直到后墙。"""
    r, th = r_of(x, y), theta_of(x, y)
    return r >= tier_front_r(tier, th) - 0.01


def tier_z(tier, x, y):
    r = r_of(x, y)
    z = tier["z0"] + max(0.0, r - tier["r0"]) * tier["slope"]
    rows = D.tier_rows(tier)
    zmax = rows[-1]["z"] if rows else tier["z0"]
    return min(z, zmax)


def grid_surface(mesh, predicate, zfn, step=0.9, x0=HX0, x1=HX1, zoff=0.0,
                 up=True):
    """在观众厅平面网格上按 predicate 取面，z 由 zfn 给。"""
    nx = max(1, int((x1 - x0) / step))
    for i in range(nx):
        xa = x0 + (x1 - x0) * i / nx
        xb = x0 + (x1 - x0) * (i + 1) / nx
        wa, wb = hall_half_width(xa), hall_half_width(xb)
        ny = max(1, int(2 * (wa + wb) / step))
        for j in range(ny):
            ya = AX - wa + 2 * wa * j / ny
            yb = AX - wa + 2 * wa * (j + 1) / ny
            yc = AX - wb + 2 * wb * j / ny
            yd = AX - wb + 2 * wb * (j + 1) / ny
            if not predicate((xa + xb) / 2, (ya + yc) / 2):
                continue
            p00 = (xa, ya, zfn(xa, ya) + zoff)
            p10 = (xb, yc, zfn(xb, yc) + zoff)
            p11 = (xb, yd, zfn(xb, yd) + zoff)
            p01 = (xa, yb, zfn(xa, yb) + zoff)
            if up:
                mesh.add([p00, p10, p11, p01], [(0, 1, 2, 3)])
            else:
                mesh.add([p00, p01, p11, p10], [(0, 1, 2, 3)])


# ------------------------------------------------------------------ 1 壳体
def build_shell():
    # 侧墙（斜展）：自台口角到后墙角，底 0、顶随穹顶边缘
    for sgn, gname in ((1, "wall_n"), (-1, "wall_s")):
        M = Mesh(f"壳体·墙{'北' if sgn > 0 else '南'}", MAT["wall"], gname)
        xs = [HX0 + (HX1 - HX0) * i / 24.0 for i in range(25)]
        for i in range(24):
            xa, xb = xs[i], xs[i + 1]
            ya = AX + sgn * hall_half_width(xa)
            yb = AX + sgn * hall_half_width(xb)
            M.add([(xa, ya, 0.0), (xb, yb, 0.0), (xb, yb, D.dome_edge_z(xb)),
                   (xa, ya, D.dome_edge_z(xa))], [(0, 1, 2, 3)])
        emit(M)
    # 后墙
    hw = D.HALL["w_rear"] / 2
    R = Mesh("壳体·后墙", MAT["wall"], "wall_rear")
    ztop = D.dome_edge_z(HX1)
    R.add([(HX1, AX - hw, 0.0), (HX1, AX + hw, 0.0),
           (HX1, AX + hw, ztop), (HX1, AX - hw, ztop)], [(0, 1, 2, 3)])
    emit(R)

    # 地坪（池座放坡 + 后厅平段）
    Z = Mesh("地坪", MAT["floor"], "floor")
    pit = D.TIERS[0]

    def zf(x, y):
        r = r_of(x, y)
        z = pit["z0"] + max(0.0, r - pit["r0"]) * pit["slope"]
        return min(z, D.tier_rows(pit)[-1]["z"])

    grid_surface(Z, lambda x, y: in_hall(x, y, 1.2), zf, step=1.0)
    emit(Z, (0, 0, 1))

    # 台口墙：两侧墩 + 上过梁
    W = Mesh("台口墙", MAT["wall"], "shell")
    px = D.PROSCENIUM["x"]
    pw = D.PROSCENIUM["w"] / 2
    h = D.PROSCENIUM["h"]
    top = D.dome_edge_z(px)
    for s in (1, -1):
        y0 = AX + s * pw
        y1 = AX + s * hall_half_width(px + 0.1)
        W.add([(px - 1.2, y0, 0), (px - 1.2, y1, 0), (px - 1.2, y1, top),
               (px - 1.2, y0, top)], [(0, 1, 2, 3)])
        W.add([(px + 0.6, y0, 0), (px + 0.6, y1, 0), (px + 0.6, y1, top),
               (px + 0.6, y0, top)], [(1, 0, 3, 2)])
        W.add([(px - 1.2, y0, 0), (px + 0.6, y0, 0), (px + 0.6, y0, top),
               (px - 1.2, y0, top)], [(0, 1, 2, 3)] if s < 0 else [(1, 0, 3, 2)])
    W.add([(px - 1.2, AX - pw, h), (px - 1.2, AX + pw, h),
           (px - 1.2, AX + pw, top), (px - 1.2, AX - pw, top)], [(0, 1, 2, 3)])
    W.add([(px + 0.6, AX - pw, h), (px + 0.6, AX + pw, h),
           (px + 0.6, AX + pw, top), (px + 0.6, AX - pw, top)], [(1, 0, 3, 2)])
    W.add([(px - 1.2, AX - pw, h), (px + 0.6, AX - pw, h),
           (px + 0.6, AX + pw, h), (px - 1.2, AX + pw, h)], [(0, 1, 2, 3)])
    emit(W)

    # 台口金线脚（精模）
    if P:
        G = Mesh("台口金线", MAT["gold"], "shell")
        for (y0, y1) in ((AX - pw - 1.6, AX - pw), (AX + pw, AX + pw + 1.6)):
            G.box(px + 0.7, (y0 + y1) / 2, 0, 0.36, 1.6, h, 0)
        G.box(px + 0.7, AX, h, 0.36, 2 * pw + 3.2, 1.6)
        emit(G)


# ------------------------------------------------------------------ 2 主席台与后台
def build_stage():
    S = D.STAGE
    M = Mesh("主席台", MAT["stage"], "stage")
    M.box((S["x0"] + S["x1"]) / 2, AX, 0, S["x1"] - S["x0"], 2 * S["half_w"], S["z"])
    # 三级踏步
    for i in range(3):
        hh = S["z"] * (i + 1) / 3.0
        M.box(S["x1"] + 0.5 + (3 - i) * 0.45 - 0.45, AX, 0, 0.9, 2 * S["half_w"] - 2 * i,
              hh)
    emit(M)

    # 台口两侧矮墙（遮后台）
    W = Mesh("主席台侧墙", MAT["wall"], "stage")
    for s in (1, -1):
        W.add([(S["x0"], AX + s * S["half_w"], 0), (S["x1"] + 2.5, AX + s * S["half_w"], 0),
               (S["x1"] + 2.5, AX + s * S["half_w"], 22.5),
               (S["x0"], AX + s * S["half_w"], 22.5)], [(0, 1, 2, 3)])
    # 台后墙
    W.add([(S["x0"], AX - S["half_w"], 0), (S["x0"], AX + S["half_w"], 0),
           (S["x0"], AX + S["half_w"], 22.5), (S["x0"], AX - S["half_w"], 22.5)],
          [(0, 1, 2, 3)])
    emit(W)

    # 舞台与后台上方的顶板（否则从池座透过台口会看到"天空"）
    RF = Mesh("舞台顶板", MAT["soffit"], "stage")
    RF.box(-513.0, AX, D.PROSCENIUM["h"], 60.0, 130.0, 0.9)
    emit(RF, (0, 0, -1))

    # 后台体块
    BG = Mesh("后台", MAT["wall"], "stage")
    B = D.ZONES["backstage"]
    BG.box((B["x0"] + B["x1"]) / 2, AX, 0, B["x1"] - B["x0"], 120, 22.0)
    emit(BG)

    # 国徽与十面旗（精模）
    if P:
        # 国徽：先在局部 XY 平面画（u=x 横向、v=y 竖向、w=z 出挑），
        # 建完整体绕 Y 转 −90° 立起来朝东——Mesh 没有轴变换，只能靠对象旋转。
        E = Mesh("国徽", MAT["gold"], "stage")
        R = D.EMBLEM["d"] / 2.0
        E.cyl(0, 0, -0.10, 0.14, R, n=56)
        Z0, ZD = -0.36, 0.24

        ww = 0.21 * D.EMBLEM["d"]                      # 城墙半宽 0.21D
        E.box(0, -R * 0.54, Z0, 2 * ww, 0.86, ZD)      # 墙身
        for dy in (-ww, -ww * 0.33, ww * 0.33, ww):
            E.box(dy, -R * 0.54 + 0.55, Z0, 0.30, 0.28, ZD)   # 垛口
        gr = 0.62 * R
        for i in range(8):                             # 齿轮八齿
            a = 2 * math.pi * i / 8
            E.box(gr * math.cos(a), -R * 0.70 + 0.30 * math.sin(a), Z0, 0.26, 0.26, ZD)
        for sgn in (-1, 1):                            # 稻穗各五粒
            for i in range(5):
                E.box(sgn * (R * 0.68 - 0.05 * i), -R * 0.24 + i * 0.40, Z0,
                      0.17, 0.26, ZD)
        for i in range(22):                            # 金蟠龙 S 形盘绕
            t = i / 21.0
            E.box(1.02 * math.sin(t * 2.2 * math.pi - 0.6), -R * 0.34 + 3.10 * t,
                  Z0, 0.30, 0.32, ZD)
        E.box(0, -R * 0.92, Z0, 2.05, 0.30, ZD)        # 绶带
        ob = emit(E, (0, 0, 1))
        if ob:
            ob.rotation_euler = (0, math.radians(-90), 0)
            ob.location = (S["x0"] + 1.0, AX, 12.0)
        if D.FLAGS_AT_PROSCENIUM:
            F = Mesh("红底金龙旗", MAT["red"], "stage")
            for dy in (-16.5, -11.0, -5.5, 5.5, 11.0, 16.5,
                       -22.0, 22.0, -27.5, 27.5):
                x = S["x0"] + 1.4 + (0.35 if abs(dy) > 17 else 0.0)
                F.box(x, AX + dy, 6.2 + (0.6 if abs(dy) > 20 else 0.0), 0.16, 3.0, 6.2)
            emit(F)


# ------------------------------------------------------------------ 3 挑台
def build_balcony(tier, idx):
    g = f"bal{idx}"
    top = Mesh(f"挑台{idx}·面", MAT["floor"], g)
    bot = Mesh(f"挑台{idx}·底", MAT["soffit"], g)

    fan_surface(top, tier)
    fan_surface(bot, tier, zoff=-1.55, up=False)
    top.want = (0, 0, 1)
    bot.want = (0, 0, -1)
    emit(top, (0, 0, 1))
    emit(bot, (0, 0, -1))

    # 前缘板 + 栏板
    F = Mesh(f"挑台{idx}·前缘", MAT["wall"], g)
    rows = D.tier_rows(tier)
    r_first = rows[0]["r"]
    n = 260
    th_lo = -1.05
    prev = None
    for i in range(n + 1):
        th = th_lo + 2 * -th_lo * i / n
        r = max(tier_front_r(tier, th), r_first)
        x = FX + r * math.cos(th)
        y = FY + r * math.sin(th)
        if not in_hall(x, y, 0.6):
            prev = None
            continue
        z = tier["z0"]
        cur = (x, y, z)
        if prev:
            F.quad((prev[0], prev[1], prev[2] - 1.9), (cur[0], cur[1], cur[2] - 1.9),
                   (cur[0], cur[1], cur[2] + 0.95), (prev[0], prev[1], prev[2] + 0.95))
        prev = cur
    emit(F)

    if P:
        R = Mesh(f"挑台{idx}·栏板", MAT["gold"], g)
        prev = None
        for i in range(n + 1):
            th = th_lo + 2 * -th_lo * i / n
            r = max(tier_front_r(tier, th), r_first)
            x = FX + r * math.cos(th)
            y = FY + r * math.sin(th)
            if not in_hall(x, y, 0.6):
                prev = None
                continue
            cur = (x, y, tier["z0"])
            if prev:
                R.quad((prev[0], prev[1], prev[2] + 0.95), (cur[0], cur[1], cur[2] + 0.95),
                       (cur[0], cur[1], cur[2] + 1.10), (prev[0], prev[1], prev[2] + 1.10))
            prev = cur
        emit(R)


# ------------------------------------------------------------------ 4 座席
def build_seats(tier, idx, desks=True):
    g = f"seat{idx}"
    S = Mesh(f"座席{idx}", MAT["seat"], g)
    DD = Mesh(f"桌板{idx}", MAT["stage"] if P else MAT["seat"], g) if desks else None
    for row in D.tier_rows(tier):
        r, z = row["r"], row["z"]
        for (t0, t1, n) in row["blocks"]:
            if n <= 0:
                continue
            step = (t1 - t0) / n
            for k in range(n):
                th = t0 + step * (k + 0.5)
                x = FX + (r + 0.12) * math.cos(th)
                y = FY + (r + 0.12) * math.sin(th)
                # 椅座 + 靠背（靠背在座席后方，即 +r 一侧）
                S.box(x, y, z + 0.40, 0.52, 0.50, 0.09, rz=th + math.pi / 2)
                S.box(x + 0.26 * math.cos(th), y + 0.26 * math.sin(th), z + 0.44,
                      0.52, 0.10, 0.52, rz=th + math.pi / 2)
                if P:
                    for sgn in (1, -1):
                        S.box(x + sgn * 0.27 * math.cos(th + math.pi / 2),
                              y + sgn * 0.27 * math.sin(th + math.pi / 2),
                              z + 0.42, 0.05, 0.5, 0.05, rz=th + math.pi / 2)
            if DD:
                # 桌板按弧分段，避免大块用弦直连、中段凹进舞台
                rr_out, rr_in = r - 0.28, r - 0.62
                if rr_in > 36.4:
                    seg = max(1, int((t1 - t0) * r / 1.2))
                    for q in range(seg):
                        a0 = t0 + (t1 - t0) * q / seg
                        a1 = t0 + (t1 - t0) * (q + 1) / seg
                        p0 = (FX + rr_out * math.cos(a0), FY + rr_out * math.sin(a0), z + 0.70)
                        p1 = (FX + rr_out * math.cos(a1), FY + rr_out * math.sin(a1), z + 0.70)
                        p2 = (FX + rr_in * math.cos(a1), FY + rr_in * math.sin(a1), z + 0.70)
                        p3 = (FX + rr_in * math.cos(a0), FY + rr_in * math.sin(a0), z + 0.70)
                        DD.add([p0, p1, p2, p3,
                                (p0[0], p0[1], z + 0.62), (p1[0], p1[1], z + 0.62),
                                (p2[0], p2[1], z + 0.62), (p3[0], p3[1], z + 0.62)],
                               [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2),
                                (2, 6, 7, 3), (3, 7, 4, 0)])
    emit(S)
    if DD:
        emit(DD)


# ------------------------------------------------------------------ 5 穹顶
def build_dome():
    C = Mesh("穹顶", MAT["dome"], "dome")
    grid_surface(C, lambda x, y: in_hall(x, y, 2.6), D.dome_height, step=1.1,
                 up=False)
    emit(C, (0, 0, -1))

    # 三环水波灯槽
    c = D.hall_centroid()
    top = D.HALL["z_apex"]
    for k, rho in enumerate((0.86, 0.62, 0.40) if P else ()):
        ring = Mesh(f"灯槽{k}", MAT["lamp"] if P else MAT["ceil"], "dome")
        trim = Mesh(f"灯槽压边{k}", MAT["gold"], "dome")
        n = 96
        for i in range(n):
            a0 = -math.pi + 2 * math.pi * i / n
            a1 = -math.pi + 2 * math.pi * (i + 1) / n
            p0 = ring_pt(c, rho, a0)
            p1 = ring_pt(c, rho, a1)
            q0 = ring_pt(c, rho * 0.985, a0)
            q1 = ring_pt(c, rho * 0.985, a1)
            if not (p0 and p1 and q0 and q1):
                continue
            ring.quad(q0, q1, p1, p0)
            z = p0[2]
            trim.quad((p0[0], p0[1], z), (p1[0], p1[1], z),
                      (p1[0], p1[1], z - 0.35), (p0[0], p0[1], z - 0.35))
        emit(ring)
        if P:
            emit(trim)

    # 中央圆盘 + 72 道光芒 + 满天星
    disc = Mesh("中央圆盘", MAT["gold"] if P else MAT["ceil"], "dome")
    zc = D.dome_height(c[0], c[1]) - 1.4
    R = 7.0
    n = 72
    for i in range(n):
        a0 = 2 * math.pi * i / n
        a1 = 2 * math.pi * (i + 1) / n
        disc.add([(c[0], c[1], zc), (c[0] + R * math.cos(a1), c[1] + R * math.sin(a1), zc),
                  (c[0] + R * math.cos(a0), c[1] + R * math.sin(a0), zc)], [(0, 1, 2)])
    emit(disc)

    if P:
        rays = Mesh("镏金72道光芒", MAT["gold"], "dome")
        for i in range(72):
            a = 2 * math.pi * i / 72
            r0, r1 = 7.1, 13.2
            p0 = (c[0] + r0 * math.cos(a - 0.012), c[1] + r0 * math.sin(a - 0.012),
                  D.dome_height(c[0] + r0 * math.cos(a), c[1] + r0 * math.sin(a)) - 0.22)
            p1 = (c[0] + r0 * math.cos(a + 0.012), c[1] + r0 * math.sin(a + 0.012),
                  D.dome_height(c[0] + r0 * math.cos(a), c[1] + r0 * math.sin(a)) - 0.22)
            p2 = (c[0] + r1 * math.cos(a + 0.02), c[1] + r1 * math.sin(a + 0.02),
                  D.dome_height(c[0] + r1 * math.cos(a), c[1] + r1 * math.sin(a)) - 0.22)
            p3 = (c[0] + r1 * math.cos(a - 0.02), c[1] + r1 * math.sin(a - 0.02),
                  D.dome_height(c[0] + r1 * math.cos(a), c[1] + r1 * math.sin(a)) - 0.22)
            rays.quad(p0, p1, p2, p3)
        emit(rays)

        stars = Mesh("满天星灯", MAT["lamp"], "dome")
        import random
        rnd = random.Random(20261123)
        cnt = 0
        while cnt < 500:
            x = HX0 + (HX1 - HX0) * rnd.random()
            y = AX + (hall_half_width(x)) * (rnd.random() * 2 - 1)
            if r_of(x, y) < 14:
                continue
            stars.cyl(x, y, D.dome_height(x, y) - 0.30, D.dome_height(x, y) - 0.12, 0.22, n=6)
            cnt += 1
        emit(stars)

        # 40 组宝相花灯
        petals = Mesh("宝相花灯", MAT["lamp"], "dome")
        for i in range(40):
            a = 0.28 + 2 * math.pi * i / 40
            rr = 0.80
            bx = c[0] + rr * (HX1 - c[0]) * math.cos(a) * 0.55
            by = c[1] + 74 * math.sin(a) * 0.72
            if not in_hall(bx, by, 3):
                continue
            z = D.dome_height(bx, by) - 0.25
            petals.cyl(bx, by, z - 0.55, z, 0.9, n=8, r1=0.5)
        emit(petals)


def ring_pt(c, rho, ang):
    """穹顶上的一点（按形心径向参数）。"""
    poly = D.hall_plan()
    rb = D._ray_to_polygon(c, ang, poly)
    if not rb:
        return None
    x = c[0] + math.cos(ang) * rb * rho
    y = c[1] + math.sin(ang) * rb * rho
    if not in_hall(x, y, 2.0):
        return None
    return (x, y, D.dome_height(x, y))


# ------------------------------------------------------------------ 6 中央前厅
def build_foyer():
    F = D.FOYER
    g = "foyer"
    W = Mesh("前厅·墙", MAT["wall"], "foyer_wall")
    x0, x1 = F["x0"], F["x1"]
    y0, y1 = F["y0"], F["y1"]
    # 两侧墙
    for y in (y0, y1):
        W.quad((x0, y, 0), (x1, y, 0), (x1, y, F["h"]), (x0, y, F["h"]))
    # 东墙（留五樘门洞）
    segs = []
    ys = sorted([AX - 48 - 3.2, AX + 48 + 3.2] + [dd[1] - 3.2 for dd in D.DOORS["foyer"]]
                + [dd[1] + 3.2 for dd in D.DOORS["foyer"]])
    prev = y0
    for yy in sorted(set(ys)):
        if yy > prev:
            segs.append((prev, yy))
        prev = max(prev, yy)
    if prev < y1:
        segs.append((prev, y1))
    for a, b in segs:
        W.quad((x1, a, 0), (x1, b, 0), (x1, b, F["h"]), (x1, a, F["h"]))
    # 门洞上口
    for (dx, dy, w, hh) in D.DOORS["foyer"]:
        W.quad((x1, dy - w / 2, hh), (x1, dy + w / 2, hh),
               (x1, dy + w / 2, F["h"]), (x1, dy - w / 2, F["h"]))
    emit(W)

    # 地坪
    FLO = Mesh("前厅·地", MAT["floor"], "foyer_floor")
    nx, ny = 40, 120
    for i in range(nx):
        for j in range(ny):
            xa = x0 + (x1 - x0) * i / nx
            xb = x0 + (x1 - x0) * (i + 1) / nx
            ya = y0 + (y1 - y0) * j / ny
            yb = y0 + (y1 - y0) * (j + 1) / ny
            FLO.quad((xa, ya, 0), (xb, ya, 0), (xb, yb, 0), (xa, yb, 0))
    emit(FLO)

    # 井字梁顶棚
    C = Mesh("前厅·顶", MAT["dome"] if WHITE else MAT["ceil"], "foyer_ceil")
    nx, ny = 40, 120
    for i in range(nx):
        for j in range(ny):
            xa = x0 + (x1 - x0) * i / nx
            xb = x0 + (x1 - x0) * (i + 1) / nx
            ya = y0 + (y1 - y0) * j / ny
            yb = y0 + (y1 - y0) * (j + 1) / ny
            C.quad((xa, ya, F["h"]), (xa, yb, F["h"]), (xb, yb, F["h"]), (xb, ya, F["h"]))
    # 梁
    for gx in range(int(x0) + 6, int(x1), 12):
        C.box(gx, (y0 + y1) / 2, F["h"], 1.1, y1 - y0, 1.3)
    for gy in range(int(y0) + 12, int(y1), 12):
        C.box((x0 + x1) / 2, gy, F["h"], x1 - x0, 1.1, 1.3)
    emit(C, (0, 0, -1))

    # 20 根明柱
    CO = Mesh("前厅·明柱", MAT["marble_w"] if P else MAT["wall"], "foyer_col")
    for (cx, cy) in D.foyer_columns():
        CO.cyl(cx, cy, 0, F["beam_z"], 0.95, n=20)
        if P:
            CO.cyl(cx, cy, 0, 0.5, 1.25, n=20)
            CO.cyl(cx, cy, F["beam_z"] - 0.6, F["beam_z"], 1.2, n=20)
    emit(CO)

    # 5 组水晶吊灯
    if P:
        CH = Mesh("水晶吊灯", MAT["lamp"], "foyer_lamp")
        for i, dy in enumerate((-48, -24, 0, 24, 48)):
            cx = (x0 + x1) / 2
            z = F["beam_z"] - 3.0
            CH.cyl(cx, AX + dy, z, z + 0.6, 1.9, n=16, r1=0.7)
            CH.cyl(cx, AX + dy, z - 2.6, z, 0.9, n=12, r1=1.5)
        emit(CH)
    else:
        CH = Mesh("吊灯", MAT["lamp"], "foyer_lamp")
        for dy in (-48, -24, 0, 24, 48):
            CH.cyl((x0 + x1) / 2, AX + dy, F["beam_z"] - 3.4, F["beam_z"] - 2.4, 1.6, n=12)
        emit(CH)

    # 铜门
    DM = Mesh("铜门", MAT["bronze"] if P else MAT["wall"], "foyer_door")
    for (dx, dy, w, hh) in D.DOORS["foyer"]:
        DM.box(dx - 0.15, dy, 0, 0.3, w, hh)
    for (dx, dy, w, hh) in D.DOORS["hall"]:
        DM.box(dx - 0.15, dy, 0, 0.3, w, hh)
    emit(DM)


# ------------------------------------------------------------------ 7 后厅栏杆
def build_rear():
    R = Mesh("后厅栏板", MAT["wall"] if not P else MAT["gold"], "rear")
    for tier in (D.TIERS[1], D.TIERS[2]):
        rows = D.tier_rows(tier)
        rr = rows[-1]["r"]
        th = D.wall_half_angle(rr)
        z = rows[-1]["z"]
        n = 60
        for i in range(n):
            a0 = -th + 2 * th * i / n
            a1 = -th + 2 * th * (i + 1) / n
            p0 = (FX + rr * math.cos(a0), FY + rr * math.sin(a0))
            p1 = (FX + rr * math.cos(a1), FY + rr * math.sin(a1))
            R.quad((p0[0], p0[1], z), (p1[0], p1[1], z),
                   (p1[0], p1[1], z + 1.1), (p0[0], p0[1], z + 1.1))
    emit(R)


# ------------------------------------------------------------------ 剖切
def cut_at_axis():
    """沿 y = AXIS_Y 切开，保留南半（视点自北侧看剖面）。"""
    n = 0
    for ob in list(col.objects):
        if ob.type != "MESH":
            continue
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.bisect(plane_co=(0, AX, 0), plane_no=(0, 1, 0),
                            use_fill=True, clear_outer=True)
        bpy.ops.object.mode_set(mode="OBJECT")
        n += 1
    print("CUT", n, "objects", flush=True)


# ------------------------------------------------------------------ 灯光 / 世界
def setup_lights():
    sc.world = bpy.data.worlds.new("World")
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.05, 0.055, 0.07, 1.0)
    bg.inputs[1].default_value = 1.0

    def area(name, loc, rot, size, power, color=(1.0, 0.96, 0.90)):
        d = bpy.data.lights.new(name, type="AREA")
        d.size = size
        d.energy = power
        d.color = color
        o = bpy.data.objects.new(name, d)
        o.location = loc
        o.rotation_euler = rot
        col.objects.link(o)
        return o

    a = math.radians
    sd = bpy.data.lights.new("Sun", type="SUN")
    sd.energy = 3.2
    sd.angle = a(2.0)
    so = bpy.data.objects.new("Sun", sd)
    so.rotation_euler = (a(38), a(6), a(215))
    col.objects.link(so)
    # 观众厅：顶部三组大面光
    area("顶光A", (-462, AX, 36), (0, 0, 0), 56, 4200)
    area("顶光B", (-430, AX, 34), (0, 0, 0), 56, 4200)
    area("顶光C", (-404, AX, 30), (0, 0, 0), 46, 2600)
    # 侧向补光（贴侧墙，向内）
    area("侧光N", (-440, AX + 40, 20), (a(90), 0, 0), 40, 1200)
    area("侧光S", (-440, AX - 40, 20), (a(-90), 0, 0), 40, 1200)
    # 台口与主席台
    area("台口光", (-496, AX, 17), (0, a(-90), 0), 34, 1200)
    area("台面光", (-506, AX, 21), (0, 0, 0), 30, 700)
    if P:
        # 打亮主席台后墙与国徽
        area("台口面光", (-472, AX, 9), (0, a(90), 0), 30, 2600)
        area("台面补光", (-495, AX, 3.4), (0, 0, 0), 26, 900)
    if args.cut:
        for xx in (-500, -430, -360):
            area(f"剖面光{xx}", (xx, AX + 70, 20), (a(90), 0, 0), 60, 5200)
    if P:
        # 精模材质吃光，池座上补两盏低位面光
        area("池座补光N", (-462, AX + 26, 7.5), (0, 0, 0), 40, 3200)
        area("池座补光S", (-462, AX - 26, 7.5), (0, 0, 0), 40, 3200)
    # 前厅
    area("前厅光", (-350, AX, 19), (0, 0, 0), 70, 1400)
    area("前厅光N", (-350, AX + 70, 16), (a(35), 0, 0), 30, 380)
    area("前厅光S", (-350, AX - 70, 16), (a(-35), 0, 0), 30, 380)


# ------------------------------------------------------------------ 相机 / 渲染
def setup_render():
    cam_data = bpy.data.cameras.new("Cam")
    cam_data.clip_start = 0.5
    cam_data.clip_end = 20000.0
    cam = bpy.data.objects.new("Cam", cam_data)
    col.objects.link(cam)
    sc.camera = cam

    def pick_gpu():
        if args.cpu:
            print("DEVICE CPU", flush=True)
            return
        pre = bpy.context.preferences.addons["cycles"].preferences
        for backend in ("OPTIX", "CUDA"):
            try:
                pre.compute_device_type = backend
                pre.get_devices()
                if not any(d.type == backend for d in pre.devices):
                    continue
                for d in pre.devices:
                    d.use = (d.type == backend)
                sc.cycles.device = "GPU"
                sc.cycles.denoiser = "OPTIX" if backend == "OPTIX" else "OPENIMAGEDENOISE"
                print("DEVICE", backend, flush=True)
                return
            except Exception as exc:
                print("DEVICE", backend, exc, flush=True)
        sc.cycles.device = "CPU"
        print("DEVICE CPU fallback", flush=True)

    if args.check:
        sc.render.engine = "BLENDER_WORKBENCH"
        sc.display.shading.light = "STUDIO"
        sc.display.shading.color_type = "MATERIAL"
        sc.display.shading.show_shadows = True
        sc.display.shading.show_cavity = True
        sc.render.image_settings.file_format = "WEBP"
        sc.render.image_settings.quality = 88
        print("ENGINE WORKBENCH", flush=True)
        return cam
    sc.render.engine = "CYCLES"
    pick_gpu()
    sc.cycles.samples = args.samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 5
    sc.cycles.transparent_max_bounces = 4
    sc.render.image_settings.file_format = "WEBP"
    sc.render.image_settings.quality = 92
    sc.view_settings.view_transform = "AgX" if P else "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = (args.exposure if args.exposure is not None
                                 else (-1.0 if P else -2.4))
    return cam


AR = 16 / 9
SHOTS = [
    ("纵剖A—A", dict(loc=(-425, AX + 330, 23.5), target=(-425, AX, 23.5), lens=50,
                   ortho=246, ar=4.15, hide=(), exp=-0.6)),
    ("全景自台口", dict(loc=(-482, AX, 15.5), target=(-410, AX, 12.0), lens=17)),
    ("池座坐姿", dict(loc=(-459.0, AX, 2.50), target=(-500, AX + 2, 6.0), lens=26)),
    ("二层坐姿", dict(loc=(-447.5, AX, 13.62), target=(-500, AX + 2, 6.0), lens=26)),
    ("三层坐姿", dict(loc=(-439.2, AX, 22.13), target=(-500, AX + 2, 6.0), lens=26)),
    ("主席台立姿", dict(loc=(-488, AX, 3.15), target=(-420, AX, 11.0), lens=24)),
    ("主席台俯瞰", dict(loc=(-497, AX, 13.0), target=(-424, AX, 13.5), lens=21)),
    ("仰望穹顶", dict(loc=(-452, AX + 5, 4.3), target=(-427, AX + 1, 43.0), lens=19)),
    ("中央前厅", dict(loc=(-324, AX - 34, 7.0), target=(-389, AX + 8, 12.0), lens=26)),
    ("剖视鸟瞰", dict(loc=(-322, AX + 104, 74), target=(-462, AX - 8, 12), lens=34,
                   hide=("dome", "wall_n", "foyer_ceil"))),
]


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


# ------------------------------------------------------------------ 主流程
print("BUILD", "precise" if P else "massing", flush=True)
t0 = time.time()
build_shell()
build_stage()
build_balcony(D.TIERS[1], 1)
build_balcony(D.TIERS[2], 2)
build_rear()
build_dome()
build_foyer()
for i, t in enumerate(D.TIERS):
    build_seats(t, i, desks=D.REP_DESKS)
print("BUILD DONE", round(time.time() - t0, 1), "s", flush=True)

if args.cut:
    cut_at_axis()
setup_lights()
cam = setup_render()

prefix = "校对" if args.check else ("精模" if P else "白模")
results = {}
for name, s in SHOTS:
    if args.only and not any(k and k in name for k in args.only.split(",")):
        continue
    if ("纵剖" in name) != bool(args.cut):
        continue
    for o in col.objects:
        if o.type == "MESH" and o.get("group"):
            o.hide_render = o["group"] in s.get("hide", ())
    cam.location = s["loc"]
    if s.get("ortho"):
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = s["ortho"]
    else:
        cam.data.type = "PERSP"
        cam.data.lens = s["lens"]
    look_at(cam, s["target"])
    ar = s.get("ar", AR)
    sc.render.resolution_x = args.res
    sc.render.resolution_y = int(args.res / ar)
    base_exp = sc.view_settings.exposure
    if s.get("exp") is not None:
        sc.view_settings.exposure = s["exp"]
    exps = [float(x) for x in args.exposures.split(",")] if args.exposures else [None]
    for ex in exps:
        if ex is not None:
            sc.view_settings.exposure = ex
        suffix = f"_e{ex:+g}" if ex is not None else ""
        path = os.path.join(args.out,
                            f"国家广场(2026)·万人大礼堂·{prefix}·{name}{suffix}.webp")
        sc.render.filepath = path
        t1 = time.time()
        bpy.ops.render.render(write_still=True)
        results[name + suffix] = round(time.time() - t1, 1)
        print("RENDER", name + suffix, results[name + suffix], flush=True)
    sc.view_settings.exposure = base_exp
for o in col.objects:
    o.hide_render = False

blend = os.path.join(WORK, f"grandhall_{'precise' if P else 'massing'}.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend)

if TEXTURE_TILES:
    TX.apply_uv(col.objects, TEXTURE_TILES)

glb = os.path.join(args.out, f"国家广场(2026)·万人大礼堂·{prefix}.glb")
if not args.no_glb:
    kw = {}
    if args.draco:
        kw = dict(export_draco_mesh_compression_enable=True,
                  export_draco_mesh_compression_level=6,
                  export_draco_position_quantization=14,
                  export_draco_normal_quantization=10,
                  export_draco_texcoord_quantization=12)
    bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", export_apply=True, **kw)

tris = 0
for o in col.objects:
    if o.type == "MESH":
        o.data.calc_loop_triangles()
        tris += len(o.data.loop_triangles)

print("RESULT " + json.dumps({
    "renders": results, "objects": len(col.objects), "triangles": tris,
    "seats": D.total_seats(), "blend": blend, "glb": glb,
    "glb_mb": round(os.path.getsize(glb) / 1e6, 2) if os.path.exists(glb) else None,
}, ensure_ascii=False))
