"""明官式构件库 —— 台基、柱网、额枋、斗拱、椽、庑殿顶、隔扇、脊吻。

给 build_precise.py（单殿展示）与 build_palace_precise.py（整宫精模）共用。
所有函数在调用前须已有一个活动场景；材料由 make_materials() 一次性建好并返回字典。
尺寸单位：米。坐标为世界坐标（原点在建筑中心，+y 北、+z 上）。
"""

import math

import bmesh
import bpy

COL = None
MAT = {}


def _mat(name, rgb, rough=0.8, metal=0.0):
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


def make_materials():
    global MAT
    if MAT:
        return MAT
    MAT = dict(
        tile=_mat("琉璃黄", (0.66, 0.38, 0.05), 0.40),
        tile2=_mat("琉璃黄·暗", (0.50, 0.28, 0.04), 0.45),
        soffit=_mat("椽望", (0.10, 0.075, 0.07), 0.9),
        column=_mat("朱红柱", (0.44, 0.08, 0.06), 0.6),
        wall=_mat("朱红墙", (0.40, 0.07, 0.06), 0.9),
        stone=_mat("汉白玉", (0.72, 0.70, 0.64), 0.6),
        stone2=_mat("石阶", (0.60, 0.58, 0.52), 0.75),
        cai_blue=_mat("彩画青", (0.05, 0.20, 0.32), 0.6),
        cai_green=_mat("彩画绿", (0.05, 0.22, 0.16), 0.6),
        gold=_mat("金", (0.74, 0.56, 0.16), 0.32, 0.9),
        dou=_mat("斗拱", (0.30, 0.36, 0.33), 0.7),
        door=_mat("隔扇", (0.19, 0.08, 0.05), 0.7),
        lattice=_mat("格心", (0.26, 0.13, 0.07), 0.7),
        plaque=_mat("匾", (0.10, 0.12, 0.18), 0.5),
        tile_gray=_mat("青瓦", (0.24, 0.24, 0.23), 0.8),
        glass=_mat("玻璃", (0.12, 0.26, 0.34), 0.15, 0.2),
        metal=_mat("金属", (0.55, 0.56, 0.58), 0.35, 0.8),
        citywall=_mat("城墙红", (0.38, 0.095, 0.075), 0.9),
    )
    return MAT


def set_collection(c):
    global COL
    COL = c


def _col():
    return COL or bpy.context.scene.collection


def box(name, w, d, h, x, y, z0=0.0, mat=None):
    """直接建网格（不走 bpy.ops，快 20 倍以上）。"""
    hx, hy, hz = w / 2, d / 2, h / 2
    cz = z0 + hz
    verts = [(x - hx, y - hy, cz - hz), (x + hx, y - hy, cz - hz),
             (x + hx, y + hy, cz - hz), (x - hx, y + hy, cz - hz),
             (x - hx, y - hy, cz + hz), (x + hx, y - hy, cz + hz),
             (x + hx, y + hy, cz + hz), (x - hx, y + hy, cz + hz)]
    faces = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1),
             (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    return mesh_from(name, verts, faces, mat, merge=False)


def mesh_from(name, verts, faces, mat=None, smooth=False, merge=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate()
    if merge:
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
    me.update()
    ob = bpy.data.objects.new(name, me)
    _col().objects.link(ob)
    if mat:
        ob.data.materials.append(mat)
    if smooth:
        for p in ob.data.polygons:
            p.use_smooth = True
    return ob


def cuboid(verts, faces, cx, cy, cz, sx, sy, sz):
    b = len(verts)
    for dx in (-sx / 2, sx / 2):
        for dy in (-sy / 2, sy / 2):
            for dz in (-sz / 2, sz / 2):
                verts.append((cx + dx, cy + dy, cz + dz))
    idx = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1),
           (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    faces.extend(tuple(b + i for i in f) for f in idx)


def solidify(ob, thickness=0.5):
    ob.data.materials.append(MAT["soffit"])
    m = ob.modifiers.new("solid", "SOLIDIFY")
    m.thickness = thickness
    m.offset = -1.0
    m.material_offset = 1
    m.material_offset_rim = 1
    return ob


# ------------------------------------------------------------------ 台基
def base_platform(w, d, h=3.2, stairs=True, balustrade=True, name="台基"):
    tiers = [("圭角", w + 8.4, d + 8.4, h * 0.17, 0.0),
             ("下枋", w + 7.2, d + 7.2, h * 0.14, h * 0.17),
             ("束腰", w + 5.4, d + 5.4, h * 0.36, h * 0.31),
             ("上枋", w + 7.2, d + 7.2, h * 0.17, h * 0.67),
             ("台面", w + 7.8, d + 7.8, h * 0.16, h * 0.84)]
    for nm, ww, dd, hh, z in tiers:
        box(f"{name}·{nm}", ww, dd, hh, 0, 0, z,
            MAT["stone2"] if nm == "束腰" else MAT["stone"])
    if stairs:
        sw, n = min(20.0, w * 0.24), 9
        for i in range(n):
            top = h * (i + 1) / n
            box(f"{name}·踏跺{i}", sw, 0.95, top, 0, -d / 2 - 4.0 - i * 0.95, 0.0, MAT["stone2"])
        box(f"{name}·御路", sw * 0.22, 4.6, 0.22, 0, -d / 2 - 4.2, h - 0.45, MAT["stone"])
    if balustrade:
        for side in ("S", "N", "E", "W"):
            if side in ("S", "N"):
                length, n_post = w + 7.8, max(6, int(w / 5.5))
                y = (d + 7.8) / 2 * (1 if side == "N" else -1)
                for i in range(n_post + 1):
                    x = -length / 2 + i * length / n_post
                    if side == "S" and stairs and abs(x) < min(20.0, w * 0.24) / 2 + 1.2:
                        continue
                    box(f"{name}·望柱{side}{i}", 0.34, 0.34, 1.18, x, y, h, MAT["stone"])
            else:
                length, n_post = d + 7.8, max(4, int(d / 5.5))
                x = (w + 7.8) / 2 * (1 if side == "E" else -1)
                for i in range(n_post + 1):
                    y = -length / 2 + i * length / n_post
                    box(f"{name}·望柱{side}{i}", 0.34, 0.34, 1.18, x, y, h, MAT["stone"])


# ------------------------------------------------------------------ 柱 / 枋
def edges(bays):
    out = [-sum(bays) / 2]
    for b in bays:
        out.append(out[-1] + b)
    return out


def column(x, y, z0, z1, r=0.46, name="柱", n=12):
    verts, faces = [], []
    for z in (z0, z1):
        for i in range(n):
            a = 2 * math.pi * i / n
            verts.append((x + r * math.cos(a), y + r * math.sin(a), z))
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    faces.append(tuple(range(n - 1, -1, -1)))
    faces.append(tuple(range(n, 2 * n)))
    return mesh_from(name, verts, faces, MAT["column"], merge=False)


def columns_ring(xs, ys, z0, z1, r=0.46):
    for x in xs:
        for y in (ys[0], ys[-1]):
            column(x, y, z0, z1, r)
    for y in ys[1:-1]:
        for x in (xs[0], xs[-1]):
            column(x, y, z0, z1, r)


def ring_beam(name, w, d, z, h, t, mat):
    box(name + "_S", w, t, h, 0, -d / 2, z, mat)
    box(name + "_N", w, t, h, 0, d / 2, z, mat)
    box(name + "_E", t, d, h, w / 2, 0, z, mat)
    box(name + "_W", t, d, h, -w / 2, 0, z, mat)


def beams(xs, ys, z, h, t=0.55):
    for i in range(len(xs) - 1):
        x, bw = (xs[i] + xs[i + 1]) / 2, xs[i + 1] - xs[i] - t * 1.7
        m = MAT["cai_blue"] if i % 2 == 0 else MAT["cai_green"]
        box(f"额枋S{i}", bw, t, h, x, -sum(ys) / 2, z, m)
        box(f"额枋N{i}", bw, t, h, x, sum(ys) / 2, z, m)
    for i in range(len(ys) - 1):
        y, bw = (ys[i] + ys[i + 1]) / 2, ys[i + 1] - ys[i] - t * 1.7
        m = MAT["cai_blue"] if i % 2 == 0 else MAT["cai_green"]
        box(f"额枋E{i}", t, bw, h, sum(xs) / 2, y, z, m)
        box(f"额枋W{i}", t, bw, h, -sum(xs) / 2, y, z, m)


# ------------------------------------------------------------------ 斗拱
_DG = {}


def dougong_mesh(lod=1):
    key = ("dg", lod)
    if key in _DG:
        return _DG[key]
    verts, faces = [], []

    def bx(x0, x1, y0, y1, z0, z1):
        b = len(verts)
        for zz in (z0, z1):
            for (xx, yy) in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
                verts.append((xx, yy, zz))
        faces.extend([(b, b + 1, b + 5, b + 4), (b + 1, b + 2, b + 6, b + 5),
                      (b + 2, b + 3, b + 7, b + 6), (b + 3, b, b + 4, b + 7),
                      (b + 4, b + 5, b + 6, b + 7)])

    bx(-0.22, 0.22, -0.22, 0.22, 0.0, 0.22)          # 栌斗
    bx(-0.78, 0.78, -0.11, 0.11, 0.22, 0.40)          # 泥道拱
    bx(-0.11, 0.11, -0.78, 0.78, 0.24, 0.42)          # 华拱
    bx(-0.98, 0.98, -0.10, 0.10, 0.42, 0.56)          # 令拱
    bx(-0.16, 0.16, -0.70, 0.10, 0.38, 0.62)          # 昂
    if lod >= 2:
        bx(-0.62, 0.62, -0.09, 0.09, 0.56, 0.70)      # 二层拱
        bx(-0.09, 0.09, -0.52, 0.52, 0.58, 0.72)
        bx(-0.30, 0.30, -0.08, 0.08, 0.70, 0.80)      # 耍头
    me = bpy.data.meshes.new("dougong")
    me.from_pydata(verts, [], faces)
    me.validate()
    me.materials.append(MAT["dou"])
    _DG[key] = me
    return me


def dougong_ring(w, d, z, spacing=1.85, lod=1):
    me = dougong_mesh(lod)
    nx, ny = max(int(w // spacing), 4), max(int(d // spacing), 3)

    def put(x, y, rot):
        ob = bpy.data.objects.new("斗拱", me)
        _col().objects.link(ob)
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


# ------------------------------------------------------------------ 椽
def rafter_band(name, w, d, z, depth=3.6, spacing=0.62):
    verts, faces = [], []

    def run(n, fx):
        for i in range(n + 1):
            t = i / n
            x, y = fx(t)
            cuboid(verts, faces, x, y, z, 0.16, 0.18, 0.16)

    n_long = max(int(w / spacing), 6)
    n_short = max(int(d / spacing), 4)
    for i in range(n_long + 1):
        x = -w / 2 + i * w / n_long
        cuboid(verts, faces, x, -(d / 2 + depth / 2), z, 0.18, depth, 0.18)
        cuboid(verts, faces, x, (d / 2 + depth / 2), z, 0.18, depth, 0.18)
    for i in range(1, n_short):
        y = -d / 2 + i * d / n_short
        cuboid(verts, faces, -(w / 2 + depth / 2), y, z, depth, 0.18, 0.18)
        cuboid(verts, faces, (w / 2 + depth / 2), y, z, depth, 0.18, 0.18)
    return mesh_from(name, verts, faces, MAT["soffit"])


# ------------------------------------------------------------------ 屋顶
def corr(x, amp):
    return amp * math.cos(2 * math.pi * x / 0.62)


def hip_roof(name, w, d, z_eave, h, step=0.55, mat=None):
    mat = mat or MAT["tile"]
    L = max(w - d, 0.18 * w)

    def f(x, y):
        t = min(max(max(abs(y), max(abs(x) - L / 2, 0.0)) / (d / 2), 0.0), 1.0)
        z = h * (1.0 - t) ** 1.50
        amp = 0.115 * (0.30 + 0.70 * t)
        z += corr(x if abs(x) <= L / 2 else y, amp)
        z += 0.5 * max(0.0, (abs(x) / (w / 2)) * (abs(y) / (d / 2))) ** 6
        return z_eave + z

    nx, ny = max(int(w / step), 4), max(int(d / step), 4)
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
    solidify(ob, 0.5)
    return ob


def ring_roof(name, ow, od, iw, id_, z0, h, mat=None, nu=40, nv=7):
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
        elen = math.hypot(b[0] - a[0], b[1] - a[1])
        for j in range(nv + 1):
            v = j / nv
            z = z0 + h * v ** 1.35
            for i in range(nu + 1):
                u = i / nu
                ax, ay = a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u
                dx, dy = dd[0] + (c[0] - dd[0]) * u, dd[1] + (c[1] - dd[1]) * u
                x, y = ax + (dx - ax) * v, ay + (dy - ay) * v
                verts.append((x, y, z + corr(u * elen * 0.62, 0.115 * (0.35 + 0.65 * v))))
        for j in range(nv):
            for i in range(nu):
                p = base + j * (nu + 1) + i
                faces.append((p, p + 1, p + nu + 2, p + nu + 1))
    ob = mesh_from(name, verts, faces, mat, smooth=True)
    solidify(ob, 0.5)
    return ob


def ridges(w, d, z_eave, h, ridge_len, with_kiss=True):
    box("正脊", ridge_len + 1.6, 1.0, 1.3, 0, 0, z_eave + h - 0.15, MAT["tile2"])
    if with_kiss:
        for s in (-1, 1):
            box(f"鸱吻{s}", 1.2, 0.95, 2.0, s * (ridge_len / 2 + 0.85), 0,
                z_eave + h - 0.05, MAT["gold"])
    if w < 60:
        return
    for sx in (-1, 1):
        for sy in (-1, 1):
            x0, y0 = sx * ridge_len / 2, 0.0
            x1, y1 = sx * w / 2 * 0.93, sy * d / 2 * 0.93
            n = 7
            for i in range(n):
                t0, t1 = i / n, (i + 1) / n
                xa, ya = x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0
                xb, yb = x0 + (x1 - x0) * t1, y0 + (y1 - y0) * t1
                za = z_eave + h * (1 - t0) ** 1.50 - 0.55
                zb = z_eave + h * (1 - t1) ** 1.50 - 0.55
                seg = math.hypot(xb - xa, yb - ya)
                ob = box(f"垂脊{sx}{sy}{i}", seg + 0.5, 0.6, 0.6,
                         (xa + xb) / 2, (ya + yb) / 2, (za + zb) / 2, MAT["tile2"])
                ob.rotation_euler[2] = math.atan2(yb - ya, xb - xa)


def balustrade_line(x0, x1, y, z, n=None, along_x=True):
    n = n or max(2, int(abs(x1 - x0) / 3.6))
    for i in range(n + 1):
        t = x0 + (x1 - x0) * i / n
        if along_x:
            box("三台·望柱", 0.32, 0.32, 1.1, t, y, z, MAT["stone"])
        else:
            box("三台·望柱", 0.32, 0.32, 1.1, y, t, z, MAT["stone"])


# ------------------------------------------------------------------ 门窗
def lattice_bay(name, w, h, x, y, z0, rot=0.0, bars=6):
    verts, faces = [], []

    def bx(x0, x1, z0_, z1_, y0, y1):
        b = len(verts)
        for yy in (y0, y1):
            for (xx, zz) in ((x0, z0_), (x1, z0_), (x1, z1_), (x0, z1_)):
                verts.append((xx, yy, zz))
        faces.extend([(b, b + 1, b + 5, b + 4), (b + 1, b + 2, b + 6, b + 5),
                      (b + 2, b + 3, b + 7, b + 6), (b + 3, b, b + 4, b + 7),
                      (b + 4, b + 5, b + 6, b + 7)])

    hw, y0, y1 = w / 2, -0.055, 0.055
    bx(-hw, hw, 0.0, h, y0, y1)
    for i in range(bars):
        xx = -hw + (i + 1) * w / (bars + 1)
        bx(xx - 0.045, xx + 0.045, h * 0.36, h * 0.96, y0 - 0.03, y1 + 0.03)
    for j in range(bars + 1):
        zz = h * 0.36 + (j + 1) * h * 0.60 / (bars + 2)
        bx(-hw, hw, zz - 0.045, zz + 0.045, y0 - 0.03, y1 + 0.03)
    bx(-hw, hw, h * 0.16, h * 0.34, y0 - 0.02, y1 + 0.02)
    ob = mesh_from(name, verts, faces, MAT["door"])
    ob.location = (x, y, z0)
    ob.rotation_euler[2] = rot
    return ob


def small_house(name, w, d, z=0.0, h=4.5, tile=None):
    """值房/库房：台明 + 墙 + 门 + 窗 + 青瓦两坡顶。"""
    tile = tile or MAT["tile_gray"]
    box(name + "·台明", w + 0.9, d + 0.9, 0.42, 0, 0, z, MAT["stone2"])
    box(name + "·墙", w, d, h, 0, 0, z + 0.42, MAT["wall"])
    box(name + "·门", min(1.6, w * 0.30), 0.14, h * 0.72, 0, -d / 2 - 0.04, z + 0.42, MAT["door"])
    for sgn in (1, -1):
        box(name + "·窗", min(1.2, w * 0.18), 0.10, h * 0.26, sgn * w * 0.28,
            -d / 2 - 0.03, z + h * 0.55, MAT["lattice"])
    gable_roof(name + "·顶", w + 0.5, d + 0.5, z + 0.42 + h,
               max(1.5, min(d, w) * 0.30), tile, overhang=0.9)


def crenel_band(name, x0, x1, y, z, h=1.5, spacing=1.9, along_x=True, mat=None):
    """城墙垛口：一条带上按间距排小垛，合成一个网格。"""
    mat = mat or MAT["citywall"]
    verts, faces = [], []
    n = max(int(abs(x1 - x0) / spacing), 2)
    for i in range(n):
        t = x0 + (x1 - x0) * (i + 0.5) / n
        if along_x:
            cuboid(verts, faces, t, y, z + h / 2, 1.2, 0.7, h)
        else:
            cuboid(verts, faces, y, t, z + h / 2, 0.7, 1.2, h)
    return mesh_from(name, verts, faces, mat, merge=False)


def gable_roof(name, w, d, z_eave, h, mat=None, overhang=1.2):
    """两坡（悬山）顶：给廊庑、值房用。"""
    mat = mat or MAT["tile"]
    w2, d2 = w + 2 * overhang, d + 2 * overhang
    swap = d2 > w2
    if swap:
        w2, d2 = d2, w2
    v = [(-w2 / 2, -d2 / 2, 0), (w2 / 2, -d2 / 2, 0), (w2 / 2, d2 / 2, 0), (-w2 / 2, d2 / 2, 0),
         (-w2 / 2, 0, h), (w2 / 2, 0, h)]
    f = [(0, 1, 5, 4), (3, 2, 5, 4), (0, 4, 3), (1, 2, 5)]
    if swap:
        v = [(b, a, c) for a, b, c in v]
    return mesh_from(name, [(a, b, z_eave + c) for a, b, c in v], f, mat)


def colonnade(name, w, d, z=0.0, h=4.6, bays=None):
    """廊庑：两排柱 + 阑额 + 两坡瓦顶。"""
    long_x = w >= d
    span = w if long_x else d
    n = bays or max(3, int(span / 4.5))
    for i in range(n + 1):
        t = -span / 2 + i * span / n
        if long_x:
            column(t, -(d / 2 - 0.7), z, z + h, 0.20)
            column(t, d / 2 - 0.7, z, z + h, 0.20)
        else:
            column(-(w / 2 - 0.7), t, z, z + h, 0.20)
            column(w / 2 - 0.7, t, z, z + h, 0.20)
    ring_beam(name + "·阑额", w, d, z + h, 0.34, 0.30, MAT["cai_blue"])
    box(name + "·墙", w - 1.6, d - 1.6, h - 0.3, 0, 0, z, MAT["wall"])
    gable_roof(name + "·顶", w + 0.6, d + 0.6, z + h + 0.34,
               max(1.4, (d if long_x else w) * 0.26), overhang=1.0)


# ------------------------------------------------------------------ 整殿
def wall_tower(name, w, d, z=0.0, body_h=10.0):
    """角楼：城台 + 上层柱廊 + 斗拱 + 庑殿顶。"""
    box(name + "·台", w, d, body_h, 0, 0, z, MAT["citywall"])
    zt = z + body_h
    for sx in (-1, 1):
        for sy in (-1, 1):
            column(sx * (w / 2 - 1.4), sy * (d / 2 - 1.4), zt, zt + 2.8, 0.28)
    ring_beam(name + "·额", w - 1.6, d - 1.6, zt + 2.8, 0.42, 0.34, MAT["cai_blue"])
    box(name + "·窗", w - 3.2, 0.14, 1.5, 0, -d / 2 + 1.2, zt + 0.9, MAT["lattice"])
    dougong_ring(w - 1.2, d - 1.2, zt + 3.3, spacing=1.4, lod=1)
    hip_roof(name + "·顶", w + 3.4, d + 3.4, zt + 3.9, max(3.4, w * 0.30), step=0.5)
    ridges(w + 3.4, d + 3.4, zt + 3.9, max(3.4, w * 0.30), (w + 3.4) - (d + 3.4),
           with_kiss=False)


def bridge(name, w, d, z=0.0):
    """石桥：桥面 + 两侧望柱栏板。"""
    box(name + "·面", w, d, 0.95, 0, 0, z, MAT["stone2"])
    for sx in (-1, 1):
        n = max(2, int(w / 2.4))
        for i in range(n + 1):
            x = -w / 2 + i * w / n
            box(name + "·望柱", 0.24, 0.24, 0.95, x, sx * (d / 2 - 0.28), z + 0.95, MAT["stone"])
        box(name + "·栏板", w, 0.18, 0.5, 0, sx * (d / 2 - 0.28), z + 1.1, MAT["stone"])


def rockery(name, w, d, h, z=0.0):
    """假山：几块不规则石头叠成。"""
    import math as _m
    specs = [(0.0, -0.10, 0.00, 0.62), (-0.26, 0.10, 0.05, 0.44), (0.24, 0.14, 0.03, 0.40),
             (0.05, 0.24, 0.10, 0.34), (-0.12, -0.22, 0.08, 0.30), (0.16, -0.16, 0.16, 0.26)]
    for i, (dx, dy, dz, sc) in enumerate(specs):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1.0,
                                              location=(dx * w, dy * d, z + dz * h))
        ob = bpy.context.object
        ob.name = f"{name}·石{i}"
        ob.scale = (sc * w * 0.62, sc * d * 0.62, sc * h * 0.75)
        ob.rotation_euler = (_m.radians(18 * i), _m.radians(11 * i), _m.radians(37 * i))
        ob.data.materials.append(MAT["stone2"])


def hall(name, w, d, bays=None, dbays=None, z=0.0, storeys=1,
         base_h=3.2, col_h=12.0, plaque=None, lod=1, stairs=True, balustrade=True):
    """按明官式排一座殿：台基 + 柱网 + 额枋 + 斗拱 + 椽 + 屋顶（单檐/重檐）。"""
    if bays is None:
        n = max(3, int(round(w / 8)))
        bays = [w / n] * n
    if dbays is None:
        m = max(3, int(round(d / 10)))
        dbays = [d / m] * m
    base_platform(w, d, base_h, stairs=stairs, balustrade=balustrade)
    z0 = z + base_h
    xs, ys = edges(bays), edges(dbays)
    col_h = min(col_h, max(7.0, w * 0.13))
    columns_ring(xs, ys, z0, z0 + col_h)
    # 墙身（柱间填充，隔扇在其外侧）
    box(f"{name}·墙身", w - 1.4, d - 1.4, col_h - 0.2, 0, 0, z0, MAT["wall"])
    beams(xs, ys, z0 + col_h, 0.9)
    ring_beam(f"{name}·平板枋", w + 1, d + 1, z0 + col_h + 0.9, 0.28, 0.7, MAT["wall"])
    eave_lo = z0 + col_h + 1.68   # 檐口抬高，露出斗拱
    if lod > 0:
        dougong_ring(w + 1, d + 1, eave_lo - 0.62, lod=lod)
        rafter_band(f"{name}·椽", w + 1, d + 1, eave_lo - 0.12, depth=3.4)

    if storeys == 1:
        roof_h = max(0.36 * d, 5.0)
        hip_roof(name + "·顶", w + 8, d + 8, eave_lo + 0.42, roof_h,
                 step=0.55 if lod >= 2 else 0.8)
        ridges(w + 8, d + 8, eave_lo + 0.42, roof_h, (w + 8) - (d + 8))
        # 隔扇
        for i in range(len(xs) - 1):
            bw = xs[i + 1] - xs[i] - 1.0
            cx = (xs[i] + xs[i + 1]) / 2
            lattice_bay(f"{name}·门S{i}", bw, col_h * 0.62, cx, -d / 2 + 0.15, z0,
                        bars=4 if lod >= 2 else 3)
            lattice_bay(f"{name}·门N{i}", bw, col_h * 0.62, cx, d / 2 - 0.15, z0,
                        bars=4 if lod >= 2 else 3)
        for i in range(len(ys) - 1):
            bw = ys[i + 1] - ys[i] - 1.0
            cy = (ys[i] + ys[i + 1]) / 2
            lattice_bay(f"{name}·门E{i}", bw, col_h * 0.62, w / 2 - 0.15, cy, z0,
                        rot=math.pi / 2, bars=3)
            lattice_bay(f"{name}·门W{i}", bw, col_h * 0.62, -w / 2 + 0.15, cy, z0,
                        rot=math.pi / 2, bars=3)
    else:
        up_w, up_d = w * 0.78, d * 0.80
        ring_z = eave_lo + max(4.2, 0.075 * w)      # 围脊：下檐之上 5~7 m
        ring_roof(name + "·下檐", w + 8, d + 8, up_w + 1.2, up_d + 1.2,
                  eave_lo + 0.42, ring_z - eave_lo - 0.42, nu=34, nv=6)
        for nm, ww, dd, yy, xx in (("S", up_w + 3.4, 0.85, -(up_d / 2 + 0.6), 0),
                                   ("N", up_w + 3.4, 0.85, (up_d / 2 + 0.6), 0),
                                   ("E", 0.85, up_d + 1.2, 0, up_w / 2 + 0.6),
                                   ("W", 0.85, up_d + 1.2, 0, -(up_w / 2 + 0.6))):
            box(f"{name}·围脊{nm}", ww, dd, 0.8, xx, yy, ring_z - 0.1, MAT["tile2"])
        box(f"{name}·上檐身", up_w - 2, up_d - 2, 3.0, 0, 0, ring_z, MAT["wall"])
        ring_beam(f"{name}·上额枋", up_w - 2, up_d - 2, ring_z + 3.0, 0.8, 0.8, MAT["cai_blue"])
        ring_beam(f"{name}·上平板", up_w - 1.1, up_d - 1.1, ring_z + 3.8, 0.25, 0.65, MAT["wall"])
        eave_hi = ring_z + 5.2
        dougong_ring(up_w - 1.1, up_d - 1.1, eave_hi - 0.82, spacing=2.0, lod=lod)
        rafter_band(f"{name}·上椽", up_w - 1.1, up_d - 1.1, eave_hi - 0.3, depth=2.8)
        roof_h = max(0.34 * up_d, 6.0)
        hip_roof(name + "·上顶", up_w + 6, up_d + 6, eave_hi + 0.35, roof_h,
                 step=0.55 if lod >= 2 else 0.8)
        ridges(up_w + 6, up_d + 6, eave_hi + 0.35, roof_h, (up_w + 6) - (up_d + 6))
        for i in range(len(xs) - 1):
            bw = xs[i + 1] - xs[i] - 1.0
            cx = (xs[i] + xs[i + 1]) / 2
            lattice_bay(f"{name}·门S{i}", bw, col_h * 0.68, cx, -d / 2 + 0.15, z0,
                        bars=4 if lod >= 2 else 3)
            lattice_bay(f"{name}·门N{i}", bw, col_h * 0.68, cx, d / 2 - 0.15, z0,
                        bars=4 if lod >= 2 else 3)

    if plaque:
        zz = z0 + col_h * 0.72
        pw, ph = min(5.2, w * 0.12), min(2.1, col_h * 0.2)
        box(name + "·匾框", pw, 0.28, ph, 0, -d / 2 - 0.12, zz - ph / 2, MAT["gold"])
        box(name + "·匾", pw * 0.9, 0.32, ph * 0.82, 0, -d / 2 - 0.16, zz - ph * 0.41,
            MAT["plaque"])
        cu = bpy.data.curves.new(name + "·匾文", type="FONT")
        cu.body = plaque
        cu.size = ph * 0.52
        cu.align_x = "CENTER"
        cu.align_y = "CENTER"
        cu.extrude = 0.03
        for fp in (r"C:\Windows\Fonts\simhei.ttf", r"C:\Windows\Fonts\msyh.ttc"):
            try:
                cu.font = bpy.data.fonts.load(fp)
                break
            except Exception:
                continue
        ob = bpy.data.objects.new(name + "·匾文", cu)
        _col().objects.link(ob)
        ob.location = (0, -d / 2 - 0.36, zz)
        ob.rotation_euler = (math.pi / 2, 0, 0)
        ob.data.materials.append(MAT["gold"])
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.convert(target="MESH")


def gate_house(name, w, d, z=0.0, h=9.0):
    """宫门：砖城台 + 门洞 + 门楼。"""
    box(name + "·城台", w, d, h, 0, 0, z, MAT["citywall"])
    box(name + "·门洞", w * 0.22, d + 0.6, h * 0.62, 0, 0, z, MAT["soffit"])
    roof_h = max(0.30 * d, 3.0)
    hip_roof(name + "·顶", w + 4, d + 4, z + h + 0.3, roof_h, step=0.7)
    ridges(w + 4, d + 4, z + h + 0.3, roof_h, (w + 4) - (d + 4))
