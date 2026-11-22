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


def box_at(name, w, d, h, x, y, z0, mat=None):
    """局部建盒子再定位：Object 空间以自身中心为原点；UV 的 U 沿长边 0..1、V 沿高度 0..1。

    彩画、匾额这类"按构件长度分段"的着色器要的就是这个口径（用 Object X 或 UV.U）。
    """
    hx, hy = w / 2.0, d / 2.0
    verts = [(-hx, -hy, 0.0), (hx, -hy, 0.0), (hx, hy, 0.0), (-hx, hy, 0.0),
             (-hx, -hy, h), (hx, -hy, h), (hx, hy, h), (-hx, hy, h)]
    faces = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2),
             (2, 6, 7, 3), (3, 7, 4, 0)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    uv = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        n = poly.normal
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            if abs(n.x) > max(abs(n.y), abs(n.z)):
                u = (co.y + hy) / (2 * hy) if hy else 0.5
                v = co.z / h if h else 0.0
            elif abs(n.y) > abs(n.z):
                u = (co.x + hx) / (2 * hx) if hx else 0.5
                v = co.z / h if h else 0.0
            else:
                u = (co.x + hx) / (2 * hx) if hx else 0.5
                v = (co.y + hy) / (2 * hy) if hy else 0.5
            uv.data[li].uv = (u, v)
    me.validate()
    me.update()
    ob = bpy.data.objects.new(name, me)
    _col().objects.link(ob)
    if mat:
        ob.data.materials.append(mat)
    ob.location = (x, y, z0)
    return ob


_LG = None


def _lg():
    """延迟导入三个新构件库（lg_roof / lg_dougong / lg_facade）。"""
    global _LG
    if _LG is None:
        import lg_dougong
        import lg_facade
        import lg_roof
        _LG = (lg_roof, lg_dougong, lg_facade)
    return _LG


def _self():
    import sys
    return sys.modules[__name__]


def unit_for(w):
    """斗口（材宽）按面阔定：太和殿 60 m → 0.11 m，本工程 90 m 殿 → 0.165 m。"""
    return max(0.070, min(0.170, w / 545.0))


def merge_ring(pl, name, dg, w, d, z, unit, spacing, lod):
    """把一圈斗拱合成**一个**网格对象（整宫精模里 100+ 殿，散着放会有上万对象）。"""
    import math as _m
    slots = dg.ring_layout(w, d, spacing)
    verts, faces, midx = [], [], []
    cache = {}
    mats = []
    for (x, y, rot, sp, _side) in slots:
        key = round(sp, 6)
        if key not in cache:
            me = dg.make_mesh(unit, lod, seg=sp / unit)
            cache[key] = ([tuple(v.co) for v in me.vertices],
                          [tuple(p.vertices) for p in me.polygons],
                          [p.material_index for p in me.polygons])
            if not mats:
                mats = list(me.materials)
        vs, fs, mi = cache[key]
        c, s = _m.cos(rot), _m.sin(rot)
        b = len(verts)
        for (vx, vy, vz) in vs:
            verts.append((x + vx * c - vy * s, y + vx * s + vy * c, z + vz))
        for f in fs:
            faces.append(tuple(b + i for i in f))
        midx.extend(mi)
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    for m in mats:
        me.materials.append(m)
    me.update()
    for i, p in enumerate(me.polygons):
        if i < len(midx):
            p.material_index = midx[i]
        if p.material_index == 2 and abs(p.normal.x) < 0.9:
            p.use_smooth = True
    me.validate()
    me.update()
    ob = bpy.data.objects.new(name, me)
    _col().objects.link(ob)
    return ob


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
def _ring_extrude(name, W, D, prof, mat, cap=True):
    """把 (内收量, 相对高度) 剖面绕矩形一圈挤出 —— 须弥座台基用，不会像叠盒子那样 z-fighting。"""
    verts, faces = [], []
    n = len(prof)
    for (dx, z) in prof:
        ww, dd = W - 2 * dx, D - 2 * dx
        b = len(verts)
        verts.extend([(-ww / 2, -dd / 2, z), (ww / 2, -dd / 2, z),
                      (ww / 2, dd / 2, z), (-ww / 2, dd / 2, z)])
        if b:
            for k in range(4):
                k2 = (k + 1) % 4
                faces.append((b - 4 + k, b - 4 + k2, b + k2, b + k))
    if cap:
        b = (n - 1) * 4
        faces.append((b, b + 1, b + 2, b + 3))
    return mesh_from(name, verts, faces, mat, merge=False)


def base_platform(w, d, h=3.2, stairs=True, balustrade=True, name="台基"):
    """须弥座台基：圭角 → 下枋 → 束腰 → 上枋 → 台面，一圈挤出成型。"""
    W0, D0 = w + 7.0, d + 7.0
    k = h / 3.10
    prof = [(0.00, 0.00 * k), (0.00, 0.34 * k), (0.30, 0.40 * k), (0.30, 0.92 * k),
            (0.54, 1.06 * k), (0.54, 2.08 * k), (0.30, 2.22 * k), (0.30, 2.80 * k),
            (0.10, 2.94 * k), (0.00, 3.10 * k)]
    _ring_extrude(name, W0, D0, prof, MAT["stone"])
    # 束腰做深一档（把 3~6 段单独上一遍暗色会 z-fighting，改在剖面里用同一材质即可）
    if stairs:
        sw = min(20.0, w * 0.26)
        n = 9
        y0 = -D0 / 2
        for i in range(n):
            top = h * (i + 1) / n
            box(f"{name}·踏跺{i}", sw, 0.92, top, 0, y0 - 0.46 - i * 0.92, 0.0,
                MAT["stone2"])
        # 垂带（两侧斜板）
        for sx in (-1, 1):
            x = sx * (sw / 2 + 0.55)
            for i in range(n):
                box(f"{name}·垂带{sx}{i}", 1.1, 0.92, h * (i + 1) / n,
                    x, y0 - 0.46 - i * 0.92, 0.0, MAT["stone"])
        # 御路：从台面斜到地面的石坡（不做浮空平板）
        hw = sw * 0.13
        yw = y0 - n * 0.92 - 0.15
        ve = [(-hw, y0, h - 0.02), (hw, y0, h - 0.02), (hw, yw, 0.02), (-hw, yw, 0.02),
              (-hw, y0, h - 0.30), (hw, y0, h - 0.30), (hw, yw, 0.0), (-hw, yw, 0.0)]
        fe = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3),
              (3, 7, 4, 0)]
        mesh_from(f"{name}·御路", ve, fe,
                  MAT.get("marble_carved") or MAT["stone"], merge=False)
    if balustrade:
        rail_h, rail_t = 0.92, 0.16
        # 栏板：沿台面边缘一圈（南面留出踏跺口）
        gap = (min(20.0, w * 0.26) / 2 + 1.6) if stairs else 0.0
        yS, yN = -D0 / 2 + 0.10, D0 / 2 - 0.10
        xE, xW = W0 / 2 - 0.10, -W0 / 2 + 0.10
        for (x0, x1, y) in ((-W0 / 2 + 0.1, -gap, yS), (gap, W0 / 2 - 0.1, yS),
                            (-W0 / 2 + 0.1, W0 / 2 - 0.1, yN)):
            if x1 - x0 > 0.5:
                box(f"{name}·栏板S", x1 - x0, rail_t, rail_h, (x0 + x1) / 2, y, h,
                    MAT["stone"])
                box(f"{name}·栏板压", x1 - x0, rail_t + 0.10, 0.12, (x0 + x1) / 2, y,
                    h + rail_h, MAT["stone"])
        for (y0, y1, x) in ((-D0 / 2 + 0.1, D0 / 2 - 0.1, xE),
                            (-D0 / 2 + 0.1, D0 / 2 - 0.1, xW)):
            box(f"{name}·栏板E", rail_t, y1 - y0, rail_h, x, (y0 + y1) / 2, h,
                MAT["stone"])
            box(f"{name}·栏板压", rail_t + 0.10, y1 - y0, 0.12, x, (y0 + y1) / 2,
                h + rail_h, MAT["stone"])
        # 望柱
        for side in ("S", "N", "E", "W"):
            if side in ("S", "N"):
                length, n_post = W0 - 0.2, max(6, int(w / 5.5))
                y = yS if side == "S" else yN
                for i in range(n_post + 1):
                    x = -length / 2 + i * length / n_post
                    if side == "S" and stairs and abs(x) < gap:
                        continue
                    box(f"{name}·望柱{side}{i}", 0.36, 0.36, 1.22, x, y, h, MAT["stone"])
            else:
                length, n_post = [d + 7.0 - 0.2][0], max(4, int(d / 5.5))
                x = xE if side == "E" else xW
                for i in range(n_post + 1):
                    y = -length / 2 + i * length / n_post
                    box(f"{name}·望柱{side}{i}", 0.36, 0.36, 1.22, x, y, h, MAT["stone"])



def railing_poly(name, poly, z, step=2.4, h=1.02, post=0.34, t=0.18, mat=None):
    """沿闭合多边形铺一圈汉白玉栏板：望柱 + 栏板 + 寻杖。合成一个网格。"""
    mat = mat or MAT["stone"]
    verts, faces = [], []

    def obb(cx, cy, cz, sx, sy, sz, rot):
        ca, sa = math.cos(rot), math.sin(rot)
        b = len(verts)
        for dz in (0.0, sz):
            for dy in (-sy / 2, sy / 2):
                for dx in (-sx / 2, sx / 2):
                    verts.append((cx + dx * ca - dy * sa, cy + dx * sa + dy * ca, cz + dz))
        faces.extend([(b, b + 1, b + 3, b + 2), (b + 4, b + 6, b + 7, b + 5),
                      (b, b + 4, b + 5, b + 1), (b + 2, b + 3, b + 7, b + 6),
                      (b, b + 2, b + 6, b + 4), (b + 1, b + 5, b + 7, b + 3)])

    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        L = math.hypot(x1 - x0, y1 - y0)
        if L < 1.0:
            continue
        rot = math.atan2(y1 - y0, x1 - x0)
        k = max(1, int(L / step))
        seg = L / k
        for j in range(k):
            t0 = (j + 0.5) / k
            cx = x0 + (x1 - x0) * t0
            cy = y0 + (y1 - y0) * t0
            obb(cx, cy, z + 0.06, seg - post - 0.06, t, h - 0.34 + 0.02, rot)   # 栏板
            obb(cx, cy, z + h - 0.20, seg - post + 0.10, t + 0.10, 0.14, rot)   # 寻杖
        for j in range(k + 1):
            t0 = j / k
            cx = x0 + (x1 - x0) * t0
            cy = y0 + (y1 - y0) * t0
            obb(cx, cy, z, post, post, h, rot)                                  # 望柱
            obb(cx, cy, z + h, post * 0.86, post * 0.86, 0.12, rot)             # 柱头
    return mesh_from(name + "·栏板", verts, faces, mat, merge=False)


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
    """额枋：一根整盒子（局部原点在枋心），交给彩画着色器按 UV 分段。"""
    green = MAT.get("caihua_uv_green") or MAT.get("caihua_green") or MAT["cai_green"]
    blue = MAT.get("caihua_uv_blue") or MAT.get("caihua_blue") or MAT["cai_blue"]
    out = []
    for i in range(len(xs) - 1):
        bw = xs[i + 1] - xs[i]
        cx = (xs[i] + xs[i + 1]) / 2
        mat = green if i % 2 == 0 else blue
        out.append(box_at(f"额枋S{i}", bw, t, h, cx, ys[0], z, mat))
        out.append(box_at(f"额枋N{i}", bw, t, h, cx, ys[-1], z, mat))
    for i in range(len(ys) - 1):
        bw = ys[i + 1] - ys[i]
        cy = (ys[i] + ys[i + 1]) / 2
        mat = green if i % 2 == 0 else blue
        out.append(box_at(f"额枋W{i}", t, bw, h, xs[0], cy, z, mat))
        out.append(box_at(f"额枋E{i}", t, bw, h, xs[-1], cy, z, mat))
    return out


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


def hip_height(x, y, w, d, h):
    """庑殿屋面上任意点的相对高度（举折 + 瓦垄 + 翼角）。"""
    L = max(w - d, 0.18 * w)
    t = min(max(max(abs(y), max(abs(x) - L / 2, 0.0)) / (d / 2), 0.0), 1.0)
    z = h * (1.0 - t) ** 1.50
    amp = 0.115 * (0.30 + 0.70 * t)
    z += corr(x if abs(x) <= L / 2 else y, amp)
    z += 0.5 * max(0.0, (abs(x) / (w / 2)) * (abs(y) / (d / 2))) ** 6
    return z


def hip_roof(name, w, d, z_eave, h, step=0.55, mat=None):
    """庑殿屋面（转到 lg_roof；等坡要求 W≥D，近方形时直接对调）。"""
    ROOF, _, _ = _lg()
    if d > w:
        w, d = d, w
    return ROOF.hip_surface(_self(), name, w, d, z_eave, h,
                            step=max(0.5, step), lift=0.0, mat=mat)


def ring_roof(name, ow, od, iw, id_, z0, h, mat=None, nu=40, nv=7):
    """重檐下檐（转到 lg_roof）。"""
    ROOF, _, _ = _lg()
    return ROOF.ring_surface(_self(), name, ow, od, iw, id_, z0, h,
                             step=0.8, lift=1.2, mat=mat)


def ridges(w, d, z_eave, h, ridge_len=None, with_kiss=True):
    """正脊 + 鸱吻 + 垂脊（转到 lg_roof，旧版绕世界原点旋转的 bug 一并修掉）。"""
    ROOF, _, _ = _lg()
    if d > w:
        w, d = d, w
    mat = MAT.get("glaze_plain_dark") or MAT.get("tile2") or MAT["tile"]
    return ROOF.ridge_set(_self(), "脊", w, d, z_eave, h, lift=0.0, lod=1,
                          mat=mat, kiss=with_kiss)



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
    """按明/清官式排一座殿：台基 → 柱网 → 隔扇外皮 → 额枋 → 斗拱 → 屋面 → 脊吻。"""
    ROOF, DG, FC = _lg()
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
    col_r = max(0.26, min(0.48, w / 210.0))
    unit = unit_for(w)
    dou_h = 11.0 * unit
    ov = 10.5 * unit + 1.15                  # 出檐 = 挑檐桁出挑 + 飞椽
    beam_h = min(1.10, max(0.62, 0.085 * col_h))
    LOD = min(lod, 2)

    columns_ring(xs, ys, z0, z0 + col_h, r=col_r)
    if lod >= 1:
        for x in xs:
            for y in (ys[0], ys[-1]):
                FC.column_base(_self(), x, y, z0, col_r)
        for y in ys[1:-1]:
            for x in (xs[0], xs[-1]):
                FC.column_base(_self(), x, y, z0, col_r)

    box(f"{name}·墙身", w - 0.6, d - 0.6, col_h - 0.2, 0, 0, z0, MAT["wall"])
    beams(xs, ys, z0 + col_h, beam_h)
    z_ping = z0 + col_h + beam_h
    ring_beam(f"{name}·平板枋", w + 0.4, d + 0.4, z_ping, 0.26, 0.66, MAT["wall"])
    dou_z = z_ping + 0.26
    # 斗拱 LOD 压一档：整宫 100+ 殿时 lod2 的 2200 面/攒会把总面数顶到千万级
    dou_lod = 1 if lod >= 2 else 0
    if lod >= 1:
        merge_ring(_self(), f"{name}·斗拱", DG, w, d, dou_z, unit,
                   11.0 * unit, dou_lod)
    else:      # 远距离：一条斗拱带代替整圈构件（102 殿省下 300 万面）
        ring_beam(f"{name}·斗拱带", w + 1.0, d + 1.0, dou_z + dou_h * 0.18,
                  dou_h * 0.72, 0.72, MAT["dou"])
    eave_lo = dou_z + dou_h + 0.34

    if lod >= 2:
        FC.bay_skin(_self(), name, xs, ys, w, d, z0, col_h, lod=LOD, col_r=col_r)
    elif lod == 1:      # 中距离：一块隔扇板 + 槛墙，不做棂条
        dh = min(col_h * 0.72, col_h - 1.2)
        for i in range(len(xs) - 1):
            bw = xs[i + 1] - xs[i] - 0.4
            cx = (xs[i] + xs[i + 1]) / 2
            box(f"{name}·门S{i}", bw, 0.10, dh, cx, ys[0] - 0.06, z0, MAT["door"])
            box(f"{name}·门N{i}", bw, 0.10, dh, cx, ys[-1] + 0.06, z0, MAT["door"])
        for i in range(len(ys) - 1):
            bw = ys[i + 1] - ys[i] - 0.4
            cy = (ys[i] + ys[i + 1]) / 2
            box(f"{name}·门W{i}", 0.10, bw, dh, xs[0] - 0.06, cy, z0, MAT["door"])
            box(f"{name}·门E{i}", 0.10, bw, dh, xs[-1] + 0.06, cy, z0, MAT["door"])

    if storeys == 1:
        Wr, Dr = w + 2 * ov, d + 2 * ov
        ROOF.roof(_self(), name + "·顶", Wr, Dr, eave_lo, 0.73 * Dr / 2,
                  lift=max(0.9, 0.016 * w), lod=LOD)
    else:
        Wr, Dr = w + 2 * ov, d + 2 * ov
        # 下檐四边进深相等 → 四面同坡；围脊才是水平的
        d_in = min(0.42 * Dr, max(5.5, 0.105 * Wr))
        H_lo = 0.73 * d_in
        ring_z = eave_lo + H_lo
        IW, ID = Wr - 2 * d_in, Dr - 2 * d_in
        up_w, up_d = IW - 0.7, ID - 0.7
        ROOF.ring_roof(_self(), name + "·下檐", Wr, Dr, IW, ID, eave_lo, H_lo,
                       lift=max(0.9, 0.014 * w), lod=LOD)
        z_wall = max(3.4, 0.045 * w)
        box(f"{name}·上层墙身", up_w - 1.4, up_d - 1.4, z_wall, 0, 0, ring_z,
            MAT["wall"])
        unit2 = unit_for(up_w)
        n2 = max(3, int(round(up_w / 7)))
        m2 = max(3, int(round(up_d / 8)))
        up_xs = edges([up_w / n2] * n2)
        up_ys = edges([up_d / m2] * m2)
        columns_ring(up_xs, up_ys, ring_z, ring_z + z_wall, r=col_r * 0.95)
        beams(up_xs, up_ys, ring_z + z_wall, min(0.95, 0.30 + 0.055 * up_w / 10))
        ring_beam(f"{name}·上平板", up_w + 0.3, up_d + 0.3, ring_z + z_wall + 0.86,
                  0.24, 0.6, MAT["wall"])
        dou_z2 = ring_z + z_wall + 1.10
        merge_ring(_self(), f"{name}·上斗拱", DG, up_w, up_d, dou_z2, unit2,
                   11.0 * unit2, dou_lod)
        eave_hi = dou_z2 + 11.0 * unit2 + 0.30
        W2 = up_w + 2 * (10.5 * unit2 + 1.05)
        D2 = up_d + 2 * (10.5 * unit2 + 1.05)
        ROOF.roof(_self(), name + "·上顶", W2, D2, eave_hi, 0.73 * D2 / 2,
                  lift=max(0.8, 0.014 * up_w), lod=LOD)

    if plaque:
        pw = min(5.6, w * 0.13)
        ph = min(2.2, col_h * 0.20)
        FC.plaque(_self(), name, plaque, pw, ph, 0, -d / 2 - 0.02,
                  z0 + col_h - ph - 0.34, lod=max(1, LOD))



def gate_house(name, w, d, z=0.0, h=9.0):
    """宫门：砖城台 + 门洞 + 门楼。"""
    box(name + "·城台", w, d, h, 0, 0, z, MAT["citywall"])
    box(name + "·门洞", w * 0.22, d + 0.6, h * 0.62, 0, 0, z, MAT["soffit"])
    roof_h = max(0.30 * d, 3.0)
    hip_roof(name + "·顶", w + 4, d + 4, z + h + 0.3, roof_h, step=0.7)
    ridges(w + 4, d + 4, z + h + 0.3, roof_h, (w + 4) - (d + 4))
