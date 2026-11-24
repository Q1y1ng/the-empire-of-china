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


def merge_ring(pl, name, dg, w, d, z, unit, spacing, lod, xs=None, ys=None):
    """把一圈斗拱合成**一个**网格对象（整宫精模里 100+ 殿，散着放会有上万对象）。

    给了柱位（xs / ys）就按开间布攒：柱头科对每根柱、平身科在开间内均分、四角 45° 角科；
    没给就退回每边等分的 `ring_layout()`。
    """
    import math as _m
    slots = (dg.ring_layout_bays(w, d, spacing, xs, ys)
             if (xs and ys) else dg.ring_layout(w, d, spacing))
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
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
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
            top = h * (n - i) / n          # 贴台身最高，向外出最低
            box(f"{name}·踏跺{i}", sw, 0.92, top, 0, y0 - 0.46 - i * 0.92, 0.0,
                MAT["stone2"])
        # 垂带（两侧斜板）
        for sx in (-1, 1):
            x = sx * (sw / 2 + 0.55)
            for i in range(n):
                box(f"{name}·垂带{sx}{i}", 1.1, 0.92, h * (n - i) / n,
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



def railing_poly(name, poly, z, step=2.4, h=1.02, post=0.34, t=0.18, mat=None,
                 gap=None):
    """沿闭合多边形铺一圈汉白玉栏板：望柱 + 栏板 + 寻杖。合成一个网格。

    gap=((x0,x1),(y0,y1)) 的矩形范围内不排栏板——三台前陛要留出踏跺口，
    否则一圈栏杆会横着把台阶挡死。
    """
    mat = mat or MAT["stone"]

    def _skip(cx, cy):
        if not gap:
            return False
        (gx0, gx1), (gy0, gy1) = gap
        return gx0 <= cx <= gx1 and gy0 <= cy <= gy1
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

    _cx0 = sum(p[0] for p in poly) / len(poly)
    _cy0 = sum(p[1] for p in poly) / len(poly)
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
            if _skip(cx, cy):
                continue
            # 地栿 → 栏板 → 寻杖，三层连续（原来栏板顶到 0.76、寻杖悬在 0.82，中间空一道缝）
            obb(cx, cy, z + 0.00, seg - post - 0.04, t * 1.45, 0.16, rot)        # 地栿
            obb(cx, cy, z + 0.16, seg - post - 0.04, t * 1.15, h - 0.44, rot)    # 栏板
            # 净瓶：栏板中央的小凸起，远看是栏板上的浮雕点
            obb(cx, cy, z + 0.30, 0.30, t * 1.55, h - 0.78, rot)
            obb(cx, cy, z + h - 0.28, seg - post + 0.06, t * 1.55, 0.16, rot)    # 寻杖
        for j in range(k + 1):
            t0 = j / k
            cx = x0 + (x1 - x0) * t0
            cy = y0 + (y1 - y0) * t0
            if _skip(cx, cy):
                continue
            obb(cx, cy, z, post, post, h, rot)                                  # 望柱
            obb(cx, cy, z + h, post * 0.86, post * 0.86, 0.12, rot)             # 柱头
            # 螭首：从望柱根部向外挑出的龙头石（真实照片里最醒目的细节之一）
            _nx, _ny = cx - _cx0, cy - _cy0
            _nl = math.hypot(_nx, _ny) or 1.0
            _nx, _ny = _nx / _nl, _ny / _nl
            _ar = math.atan2(_ny, _nx)
            obb(cx + _nx * 0.42, cy + _ny * 0.42, z - 0.42, 0.46, 0.62, 0.30, _ar)
            obb(cx + _nx * 0.62, cy + _ny * 0.62, z - 0.36, 0.30, 0.34, 0.20, _ar)
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


def window_band(name, w, d, z0, h, pane_w=1.35, mat_frame=None, mat_pane=None,
                t=0.16):
    """重檐上层一圈槛窗（三交六椀菱花）：下槛 / 上槛 / 两端边框 / 分扇边梃 /
    格心暗底 / 棂条网格。整圈合成**一个**网格对象，两个材质槽（棂、格心）。

    以前这里只是四块贴片 box，重檐上层看着就是四条无细节的灰板；故宫上檐
    那一圈是混金菱花窗，远看是一条金色格网，得靠棂条才立得住。
    """
    fr = mat_frame or MAT.get("gold") or MAT["lattice"]
    pn = mat_pane or MAT.get("glass") or MAT["soffit"]
    verts, faces, fmat = [], [], []
    hw, hd, ht = w / 2.0, d / 2.0, t / 2.0

    def bx(rot, cx, cy, x0, x1, zz0, zz1, y0, y1, mi=0):
        if x1 - x0 < 1e-4 or zz1 - zz0 < 1e-4 or y1 - y0 < 1e-4:
            return
        c, s = math.cos(rot), math.sin(rot)
        b = len(verts)
        for yy in (y0, y1):
            for (xx, zz) in ((x0, zz0), (x1, zz0), (x1, zz1), (x0, zz1)):
                verts.append((cx + xx * c - yy * s, cy + xx * s + yy * c, zz))
        for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1),
                  (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
            faces.append(tuple(b + i for i in f))
            fmat.append(mi)

    # 四边：(转角, 中心, 长度)。+Y / -Y 沿 X，+X / -X 沿 Y。
    for rot, cx, cy, run in ((0.0, 0.0, hd, w), (math.pi, 0.0, -hd, w),
                             (-math.pi / 2, hw, 0.0, d), (math.pi / 2, -hw, 0.0, d)):
        L = run
        hl = L / 2.0
        n = max(1, int(round(L / pane_w)))
        pw = L / n
        zt = h
        # 下槛 + 上槛 + 两端边框
        bx(rot, cx, cy, -hl, hl, 0.0, 0.14, -ht, ht, 0)
        bx(rot, cx, cy, -hl, hl, zt - 0.13, zt, -ht, ht, 0)
        bx(rot, cx, cy, -hl, -hl + 0.15, 0.14, zt - 0.13, -ht, ht, 0)
        bx(rot, cx, cy, hl - 0.15, hl, 0.14, zt - 0.13, -ht, ht, 0)
        # 格心暗底（后退半档，形成窗洞的纵深感）
        bx(rot, cx, cy, -hl + 0.12, hl - 0.12, 0.15, zt - 0.14,
           -ht * 0.45, ht * 0.10, 1)
        zb0, zb1 = 0.30, zt - 0.26
        # 分扇边梃
        for i in range(1, n):
            u = -hl + i * pw
            bx(rot, cx, cy, u - 0.055, u + 0.055, 0.14, zt - 0.13,
               -ht - 0.025, ht + 0.025, 0)
        # 棂条：每扇两竖三横（三交六椀的骨架）
        for i in range(n):
            u0 = -hl + i * pw + 0.16
            u1 = -hl + (i + 1) * pw - 0.16
            if u1 - u0 < 0.10:
                continue
            for k in (1, 2):
                uu = u0 + (u1 - u0) * k / 3.0
                bx(rot, cx, cy, uu - 0.028, uu + 0.028, zb0, zb1,
                   -ht - 0.025, ht + 0.025, 0)
            for j in (1, 2, 3):
                zz = zb0 + (zb1 - zb0) * j / 4.0
                bx(rot, cx, cy, u0, u1, zz - 0.028, zz + 0.028,
                   -ht - 0.025, ht + 0.025, 0)

    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate(verbose=False)
    me.materials.append(fr)
    me.materials.append(pn)
    for i, p in enumerate(me.polygons):
        if i < len(fmat):
            p.material_index = fmat[i]
    me.update()
    for p in me.polygons:          # 金棂微反光，别做成死平
        if p.material_index == 0:
            p.use_smooth = False
    ob = bpy.data.objects.new(name, me)
    _col().objects.link(ob)
    ob.location = (0.0, 0.0, z0)
    return ob


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
    """值房/库房：阶条石台明 + 下碱墙 + 板门门框 + 槛窗棂条 + 悬山瓦顶。"""
    tile = tile or MAT["tile_gray"]
    md = MAT.get("wood_dark") or MAT.get("door") or MAT["wall"]
    mk = MAT.get("soffit") or MAT["wall"]
    ms = MAT.get("stone") or MAT["stone2"]
    # 台明两级
    # 台身同样加高到 0.54（顶面 z+0.42）：原来顶面正好压在地坪顶面上（共面 771 m²/座）。
    box(f"{name}·台身", w + 1.10, d + 1.10, 0.54, 0, 0, z - 0.12, MAT["stone2"])
    box(f"{name}·阶条", w + 0.72, d + 0.72, 0.24, 0, 0, z + 0.28, ms)
    zt = z + 0.52
    # 墙身 + 下碱
    # 墙底再压进阶条石 4 cm：原来墙底与下碱底**同在 zt 平面**，两张朝下的面完全重合
    # （每座值房 704 m²）。压进去以后两张面错开，顶面标高不变（高度同步加 4 cm）。
    box(f"{name}·墙", w, d, h + 0.04, 0, 0, zt - 0.04, MAT["wall"])
    box(f"{name}·下碱", w + 0.05, d + 0.05, min(0.56, h * 0.16), 0, 0, zt, MAT["stone2"])
    yf = -d / 2
    # 板门：两扇 + 门框 + 门楣
    dw = min(1.8, w * 0.32)
    dh = min(h * 0.72, 3.0)
    box(f"{name}·门扇", dw, 0.10, dh, 0, yf - 0.05, zt, md)
    box(f"{name}·门缝", 0.05, 0.13, dh * 0.96, 0, yf - 0.06, zt + 0.04 * dh, mk)
    for sx in (-1, 1):
        box(f"{name}·门框{'LR'[sx > 0]}", 0.16, 0.16, dh + 0.14,
            sx * (dw / 2 + 0.08), yf - 0.06, zt, md)
    box(f"{name}·门楣", dw + 0.32, 0.16, 0.16, 0, yf - 0.06, zt + dh + 0.06, md)
    # 槛窗：两侧各一，暗底 + 棂条
    for sx in (-1, 1):
        cx = sx * (w / 4 + dw * 0.2)
        ww = min(w * 0.26, 1.9)
        wh = min(h * 0.34, 1.5)
        wz = zt + h * 0.44
        box(f"{name}·窗洞{sx}", ww, 0.08, wh, cx, yf - 0.04, wz, mk)
        nb = 5
        for i in range(nb + 1):
            box(f"{name}·棂{sx}{i}", 0.05, 0.05, wh, cx - ww / 2 + i * ww / nb,
                yf - 0.08, wz, md)
        for j in (0.33, 0.66):
            box(f"{name}·横{sx}{j}", ww, 0.05, 0.05, cx, yf - 0.08,
                wz + wh * j, md)
    # 连檐：前后各一条
    for sy in (-1, 1):
        box(f"{name}·连檐{'SN'[sy > 0]}", w + 1.5, 0.16, 0.18, 0,
            sy * (d / 2 + 0.72), zt + h - 0.02, md)
    gable_roof(name + "·顶", w + 0.5, d + 0.5, zt + h,
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
    """两坡（悬山）顶：给廊庑、值房用。举折与四坡同一套曲线，带米制 UV 与正脊。"""
    ROOF, _, _ = _lg()
    long_x = w >= d
    span = (d if long_x else w) + 2 * overhang
    ridge = (w if long_x else d) + 2 * overhang
    # two_slope() 只会把正脊排在 X 向。d > w 的廊庑/值房必须把整顶绕 Z 转 90°，
    # 否则屋顶与墙身成 90° 错位——东庑的顶因此横跨 201 m、压在三台正中。
    before = set(_col().objects)
    ob = ROOF.two_slope(_self(), name, ridge, span, z_eave, h, mat=mat)
    if not long_x:
        for _o in set(_col().objects) - before:
            _o.rotation_euler[2] = math.pi / 2.0
    return ob


def colonnade(name, w, d, z=0.0, h=4.6, bays=None):
    """廊庑：石台明 + 两排檐柱 + 阑额 + 墙身 + 两坡瓦顶。

    原来柱、墙、闌额全部直接落在 z 上、且墙比柱线内收 0.8 m，远看是一排
    "悬在柱子上的红盒子"；补一层 0.30 m 石台明并把墙收到 0.35 m。
    """
    long_x = w >= d
    span = w if long_x else d
    n = bays or max(3, int(span / 4.5))
    # 台明顶要与铺装**错开**：原来 0.42 高、从 z−0.12 起 → 顶面正好落在宫城地坪的
    # 顶面（0.30）上，两层石面同平面互相重叠 2100 m²（东朝房一处），机位一动就闪。
    # 加高到 0.54（顶面 z+0.42），台明露 0.12 m 石口 —— 既是实物做法，也彻底避开共面。
    box(f"{name}·台明", w + 0.9, d + 0.9, 0.54, 0, 0, z - 0.12,
        MAT.get("stone2") or MAT["stone"])
    zz = z + 0.30
    for i in range(n + 1):
        t = -span / 2 + i * span / n
        if long_x:
            column(t, -(d / 2 - 0.7), zz, zz + h, 0.20)
            column(t, d / 2 - 0.7, zz, zz + h, 0.20)
        else:
            column(-(w / 2 - 0.7), t, zz, zz + h, 0.20)
            column(w / 2 - 0.7, t, zz, zz + h, 0.20)
    ring_beam(name + "·阑额", w, d, zz + h, 0.34, 0.30,
              MAT.get("wood_dark") or MAT["cai_blue"])
    # 墙身要顶到阑额下皮：原来 h-0.28，阑额与墙之间空 0.28 m，整条廊庑像悬着的
    box(name + "·墙", w - 0.7, d - 0.7, h + 0.02, 0, 0, zz, MAT["wall"])
    # 出檐收到 0.35：原来 1.0，廊庑两端露出 0.65 m 空当，俯视看就是"屋顶浮在墙外"
    gable_roof(name + "·顶", w + 0.6, d + 0.6, zz + h + 0.34,
               max(1.4, (d if long_x else w) * 0.26), overhang=0.35)


def great_door(name, x0, x1, y_face, z0, h, depth=3.0, angle=100.0,
               mat_door=None, mat_dark=None):
    """一樘敞开的板门：门洞（暗腔内衬）+ 门框 + 门槛 + 两扇门（绕门轴向内开）+ 门钉。"""
    import math as _m
    md = mat_door or MAT.get("door") or MAT["wall"]
    mk = mat_dark or MAT.get("soffit") or MAT["wall"]
    w = x1 - x0
    jamb = 0.34
    cx = (x0 + x1) / 2
    # 门洞内衬：前脸略突出于隔扇，把里面的隔扇遮掉
    box(f"{name}·门洞", w - 0.02, depth, h, cx, y_face + 0.22 + depth / 2, z0, mk)
    # 门框
    box(f"{name}·门框L", jamb, 0.52, h, x0 + jamb / 2, y_face + 0.10, z0, md)
    box(f"{name}·门框R", jamb, 0.52, h, x1 - jamb / 2, y_face + 0.10, z0, md)
    box(f"{name}·上槛", w, 0.52, 0.44, cx, y_face + 0.10, z0 + h - 0.44, md)
    box(f"{name}·门槛", w - 2 * jamb, 0.46, 0.26, cx, y_face + 0.10, z0, md)
    # 两扇门：angle=0 关闭（贴在门面），>0 向殿内（+y）旋开
    lw = (w - 2 * jamb) / 2 - 0.02
    th = 0.16
    lh = h - 0.44 - 0.26
    ang = _m.radians(angle)
    ca, sa = _m.cos(ang), _m.sin(ang)
    for s2 in (-1, 1):
        hx = (x0 + jamb) if s2 < 0 else (x1 - jamb)
        dirx = ca if s2 < 0 else -ca
        diry = sa
        nxy = (-diry, dirx)                 # 门扇法向（水平）
        verts, faces = [], []
        for dz in (0.0, lh):
            for u in (0.0, lw):
                for v in (-th / 2, th / 2):
                    verts.append((hx + u * dirx + v * nxy[0],
                                  y_face + 0.08 + u * diry + v * nxy[1],
                                  z0 + 0.26 + dz))
        faces.extend([(0, 1, 3, 2), (6, 7, 5, 4), (0, 4, 5, 1),
                      (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])
        mesh_from(f"{name}·门扇{s2}", verts, faces, md, merge=True)
        # 门钉：五路五钉（统一放在朝外 -y 一侧）
        for ix in range(5):
            for iz in range(5):
                u = (ix + 1) / 6 * lw
                dz = 0.30 + (iz + 1) / 6 * (lh - 0.5)
                box(f"{name}·钉{s2}{ix}{iz}", 0.08, 0.06, 0.08,
                    hx + u * dirx, y_face - 0.01, z0 + 0.26 + dz,
                    MAT.get("gold") or md)
        # 铺首（门环座）：靠门缝那一侧
        px0 = hx + (lw - 0.32) * dirx
        box(f"{name}·铺首{s2}", 0.34, 0.07, 0.34, px0, y_face - 0.02,
            z0 + 0.26 + lh * 0.44, MAT.get("gold") or md)
    return w

def _roof_offset(before, x, y):
    """把刚造出来的整顶（含 two_slope() 额外生成的独立「·正脊」对象）一起落位。

    two_slope() 返回的是**屋身**，正脊是另一个对象：调用方只设返回值的 location 时，
    全宫的院门/翼墙帽/八字帽正脊就都留在原点 —— 实测原点附近堆了 **90 根脊**。
    """
    for _o in set(_col().objects) - before:
        _o.location.x = x
        _o.location.y = y


def court_gate(name, x, y, z=0.0, w=4.2, h=4.2, face=-1, leaves=1,
               wall_t=2.5, wall_h=None):
    """院门（随墙门楼）：门垛 + 门楣 + 板门 + 小两坡顶 + 垂带台阶。

    face = -1 表示门朝南（门楼向 -y 凸出）。
    leaves > 1 时把门扇分成几扇（宽洞口不能是一整块板门）。
    wall_t / wall_h：所在院墙的厚度与高度。瓦顶进深取 wall_t+1.3、檐口抬到墙帽之上，
    这样门顶**盖过墙帽两侧**（原来进深写死 2.6 m，比 2.5 m 的墙只宽 0.1 m、
    比 3.45 m 宽的瓦帽还窄 —— 墙帽从门顶两侧穿出来）。"""
    md = MAT.get("wood_dark") or MAT.get("door") or MAT["wall"]
    mk = MAT.get("soffit") or MAT["wall"]
    ms = MAT.get("stone") or MAT["stone2"]
    ys = y + face * 0.35
    wt = max(0.8, float(wall_t))
    wh = float(wall_h) if wall_h else max(h + 0.45, 3.0)
    # 门垛
    for sx in (-1, 1):
        box(f"{name}·垛{'EW'[sx > 0]}", 0.62, 0.86, h + 0.45,
            x + sx * (w / 2 + 0.31), ys, z, MAT["wall"])
    # 门楣与门扇
    box(f"{name}·门楣", w + 1.3, 0.80, 0.42, x, ys, z + h + 0.03, md)
    box(f"{name}·门扇", w, 0.12, h - 0.05, x, ys + face * 0.30, z, md)
    box(f"{name}·门缝", 0.05, 0.16, h * 0.94, x, ys + face * 0.30, z + 0.03 * h, mk)
    for _i in range(1, max(1, int(leaves))):
        box(f"{name}·门缝{_i}", 0.06, 0.16, h - 0.02,
            x - w / 2 + w * _i / leaves, ys + face * 0.30, z, mk)
    # 小两坡顶：进深盖过墙帽、檐口抬到墙帽之上
    ROOF, _, _ = _lg()
    _zr = z + max(h + 0.45, wh + 0.58)
    _rb = set(_col().objects)
    _rf = ROOF.two_slope(_self(), f"{name}·顶", w + 2.6, wt + 1.3, _zr, 0.95,
                         mat=MAT.get("tile_gray") or MAT["tile_gray"])
    _roof_offset(_rb, x, ys)
    # 台阶
    for i in range(3):
        box(f"{name}·阶{i}", w + 1.0, 0.40, 0.50 - i * 0.15, x,
            ys + face * (0.55 + i * 0.40), z, ms)


# ------------------------------------------------------------------ 整殿
def wall_tower(name, w, d, z=0.0, body_h=10.0):
    """角楼：砖城台（带垛口）+ 台上重檐楼（台基/隔扇/斗拱/脊吻全部复用 hall()）。"""
    box(name + "·城台", w, d, body_h, 0, 0, z, MAT["citywall"])
    box(name + "·压顶", w + 1.0, d + 1.0, 0.34, 0, 0, z + body_h, MAT.get("ridge") or MAT["stone2"])
    # 城台顶一圈垛口
    hb = 0.9
    for sy in (-1, 1):
        crenel_band(f"{name}·垛{'S' if sy < 0 else 'N'}", -w / 2 + 1.2, w / 2 - 1.2,
                    sy * (d / 2 - 0.45), z + body_h + 0.34, h=hb, along_x=True)
    for sx in (-1, 1):
        crenel_band(f"{name}·垛{'W' if sx < 0 else 'E'}", -d / 2 + 1.2, d / 2 - 1.2,
                    sx * (w / 2 - 0.45), z + body_h + 0.34, h=hb, along_x=False)
    # 台上重檐楼
    tw, td = w * 0.66, d * 0.66
    hall(name + "·楼", tw, td, z=z + body_h + 0.34, storeys=2,
         base_h=0.85, col_h=min(5.6, tw * 0.24), plaque=None, lod=2,
         stairs=False, balustrade=False)



def bridge(name, w, d, z=0.0):
    """石桥：桥面 + 桥台 + 两侧望柱栏板。"""
    box(name + "·面", w, d, 0.95, 0, 0, z, MAT["stone2"])
    # 桥台：桥面两端原来直接悬在铺装面上方 0.10 m，人视能看见一条影子缝。
    # 两端各垫一块 0.9 m 高的桥台，压进地坪 0.8 m、托住桥面。
    for sy in (-1, 1):
        box(f"{name}·桥台{'SN'[sy > 0]}", w + 0.24, 1.9, 0.9,
            0, sy * (d / 2 - 0.95), z - 0.9, MAT["stone2"])
    for sx in (-1, 1):
        n = max(2, int(w / 2.4))
        for i in range(n + 1):
            x = -w / 2 + i * w / n
            box(name + "·望柱", 0.24, 0.24, 0.95, x, sx * (d / 2 - 0.28), z + 0.95, MAT["stone"])
        box(name + "·栏板", w, 0.18, 0.5, 0, sx * (d / 2 - 0.28), z + 1.1, MAT["stone"])


def rockery(name, w, d, h, z=0.0, mat=None):
    """假山：一堆不规则石块叠涩起来。

    原来把 ico 球压成 (0.62w, 0.62d, 0.75h) 的扁椭球，46 m 长的假山成了三块
    二十米宽的白纸片。改为**七八块尺度和朝向各异的立体石块**，逐层收分。
    """
    import math as _m
    mat = mat or MAT.get("rock") or MAT.get("stone2") or MAT["stone"]
    specs = [(0.00, 0.00, 0.00, 0.30, 0.34),
             (-0.26, 0.12, 0.06, 0.26, 0.30), (0.24, -0.10, 0.04, 0.25, 0.28),
             (-0.02, 0.22, 0.16, 0.22, 0.26), (-0.12, -0.20, 0.10, 0.21, 0.24),
             (0.16, 0.14, 0.34, 0.17, 0.22), (-0.04, -0.04, 0.50, 0.14, 0.20),
             (0.30, 0.02, 0.18, 0.13, 0.18)]
    for i, (dx, dy, dz, sc, hz) in enumerate(specs):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1.0,
                                              location=(dx * w, dy * d, z + dz * h))
        ob = bpy.context.object
        ob.name = f"{name}·石{i}"
        ob.scale = (sc * w, sc * d, hz * h)
        ob.rotation_euler = (_m.radians(23 * i + 7), _m.radians(17 * i),
                             _m.radians(41 * i))
        ob.data.materials.append(mat)

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
    _before = set(_col().objects)
    base_platform(w, d, base_h, stairs=stairs, balustrade=balustrade)
    if z:                       # 台基是按原点建的，抬到院落/三台标高
        for _ob in set(_col().objects) - _before:
            _ob.location.z += z
    z0 = z + base_h
    xs, ys = edges(bays), edges(dbays)
    col_h = min(col_h, max(7.0, w * 0.13))
    col_r = max(0.26, min(0.48, w / 210.0))
    unit = unit_for(w)
    dou_h = 11.0 * unit
    # 出檐 = 挑檐桁出挑（9 斗口）+ 飞椽 + 檐椽出挑。原来只有 10.5 斗口 + 1.15 m，
    # 90 m 的大殿出檐不足 3 m，比故宫实物短一截，檐下阴影也做得不够深。
    ov = 15.5 * unit + 1.90
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

    # 墙身要顶到柱网线：原来内收 0.3 m，四个转角处隔扇外皮之间就露出缝
    # （作者看到"楼的墙没有拼合"就是这四个角）
    # 但 lod>=2 时外面还有一层真隔扇（bay_skin 铺在柱轴上，只凸出墙 5 mm），
    # 墙身贴着柱轴会把整排隔扇埋进墙里 —— 正立面就糊成一大片死红。
    # 所以精模档把墙身退到柱轴内 0.35 m，让隔扇真正站在墙面之前，才有投影。
    _wall_in = 0.70 if lod >= 2 else 0.05
    box(f"{name}·墙身", w - _wall_in, d - _wall_in, col_h - 0.2, 0, 0, z0,
        MAT["wall"])
    beams(xs, ys, z0 + col_h, beam_h)
    z_ping = z0 + col_h + beam_h
    ring_beam(f"{name}·平板枋", w + 0.4, d + 0.4, z_ping, 0.26, 0.66, MAT["wall"])
    # 斗拱下的白粉线：平板枋顶一道窄白带，把"枋"和"斗拱"分开
    # （真实做法里这道线是檐下最抓眼的一根亮线，没有它斗拱和枋就糊成一条）
    # 位置：贴在平板枋上口（z_ping+0.16..+0.26）、比枋面（0.66 厚）略凸 0.02 的一圈白线。
    # 原来写的是 z_ping+0.66、0.30 高、0.07 厚 —— 既压在斗拱坐斗的高度上（从拱腰横切过去），
    # 又比枋面缩进 0.30 m，实际被枋挡住，等于不存在。
    ring_beam(f"{name}·白粉线", w + 0.40, d + 0.40, z_ping + 0.16, 0.10, 0.70,
              MAT.get("marble_carved") or MAT["stone"])
    dou_z = z_ping + 0.26
    # 斗拱 LOD 压一档：整宫 100+ 殿时 lod2 的 2200 面/攒会把总面数顶到千万级
    dou_lod = 1 if lod >= 2 else 0
    if lod >= 1:
        merge_ring(_self(), f"{name}·斗拱", DG, w, d, dou_z, unit,
                   11.0 * unit, dou_lod, xs=xs, ys=ys)
    else:      # 远距离：一条斗拱带代替整圈构件（102 殿省下 300 万面）
        ring_beam(f"{name}·斗拱带", w + 1.0, d + 1.0, dou_z + dou_h * 0.18,
                  dou_h * 0.72, 0.72, MAT["dou"])
    # 角梁：两向挑檐桁在转角处各断一头，两个端面相差 9√2 斗口（90 m 殿约 2 m），
    # 中间什么都没有，仰视时就是两根悬空的蓝管子。补一根 45° 角梁把它们接上。
    if lod >= 1:
        _l45 = 9.0 * math.sqrt(2.0) * unit + 0.30
        for _sx in (-1, 1):
            for _sy in (-1, 1):
                _ob = box_at(f"{name}·角梁{'E' if _sx > 0 else 'W'}"
                             f"{'N' if _sy > 0 else 'S'}",
                             _l45, 1.9 * unit, 1.6 * unit,
                             _sx * (w / 2 + 4.5 * unit),
                             _sy * (d / 2 + 4.5 * unit),
                             dou_z + 9.4 * unit,
                             MAT.get("wood_dark") or MAT["column"])
                if _ob:
                    _ob.rotation_euler[2] = math.atan2(-_sy, _sx)
    eave_lo = dou_z + dou_h + 0.34

    if lod >= 2:
        FC.bay_skin(_self(), name, xs, ys, w, d, z0, col_h, lod=LOD, col_r=col_r)
    if lod >= 1 and len(xs) >= 5:            # 明间做敞开的板门
        ci = len(xs) // 2 - 1
        d_h = min(col_h - 1.4, col_h * 0.66)
        great_door(f"{name}·大门", xs[ci] + 0.6, xs[ci + 1] - 0.6,
                   ys[0] - 0.12, z0, d_h, angle=0.0,
                   mat_door=MAT.get("red_lacquer") or MAT["column"])
    elif lod == 0:      # 最简立面：一樘门 + 两窗，避免"白台明上空房子"
        dh = min(col_h * 0.55, col_h - 1.2)
        box(f"{name}·门0", min(2.4, w * 0.22), 0.10, dh, 0, ys[0] - 0.05, z0,
            MAT.get("door") or MAT["wall"])
        for _sx in (-1, 1):
            box(f"{name}·窗{_sx}", w * 0.13, 0.10, dh * 0.46, _sx * w * 0.25,
                ys[0] - 0.05, z0 + dh * 0.34, MAT.get("lattice") or MAT["wall"])
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
        # 重檐上层墙身：原来只有 4.05 m，两重檐之间几乎贴着，不像重檐；故宫实物约 8~10 m
        z_wall = max(5.2, 0.082 * w)
        box(f"{name}·上层墙身", up_w - 1.4, up_d - 1.4, z_wall, 0, 0, ring_z,
            MAT["wall"])
        # 上层槛窗一圈：重檐上层的墙身本该是一排窗，否则就是一整片朱红
        _wh = min(3.4, z_wall * 0.52)
        _wz = ring_z + z_wall * 0.26
        # 一度只是四块 0.14 厚的贴片 → 上檐看着是四条无细节的灰板；
        # 换成真槛窗（边框 + 边梃 + 菱花金棂 + 后退的格心暗底）。
        window_band(f"{name}·上层槛窗", up_w - 1.32, up_d - 1.32, _wz, _wh,
                    pane_w=max(1.05, min(1.55, up_w / 46.0)))
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
                   11.0 * unit2, dou_lod, xs=up_xs, ys=up_ys)
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



# 城门两侧翼墙的长度。城墙断口的宽度 = 城台宽 + 2*GATE_WING，
# 所以 build_massing（造城墙）与这里（造翼墙）必须共用同一个数：
# 原来城墙按 GATES["opening"] 断开、翼墙按 46 往外接，两边对不上，
# 城墙就从门里横穿过去把券洞堵死了（东/西华门还有一条 66 m 的真空缺口）。
GATE_WING = 46.0


def gate_wing(w):
    """翼墙长度：正门用到满 46 m，小门按面阔收（≈0.55w，下限 12 m）。

    原来所有宫门一律 46 m：协和门（面阔 26 m）的翼墙一直伸到 x=91，
    正好插进承天门（面阔 96 m、翼墙到 94 m）的翼墙里 —— 两座门撞在一起。
    造城墙断口与造翼墙必须调用同一个函数，否则又会对不上。
    """
    return min(GATE_WING, max(12.0, 0.55 * float(w)))


def gate_house(name, w, d, z=0.0, h=9.0, n_arch=1, wing_off=0.0, face=1, wing=None):
    """宫门：砖城台（**多券洞**）＋ 重檐门楼 ＋ 两侧翼墙。

    n_arch=5 用于正门（承天门那种"中间高大、两侧递小"的五券洞）；3 / 1 用于侧门。
    各券洞的**拱顶取同一标高**，城台就能统一拆成"墩台＋拱顶以上整片"，不必逐洞处理。
    face=±1：八字墙向哪一侧回折（+1 = 本地 +y）。北门/西门的院内在 −y/−x，必须传 −1，
    否则八字墙就翻到城墙外、架在护城河上（玄武门的八字墙一度 7/7 个采样点全悬空）。
    """
    ROOF, _, _ = _lg()
    mat_w = MAT["citywall"]
    mat_d = MAT.get("soffit") or MAT["wall"]
    mat_s = MAT.get("stone") or MAT["stone2"]
    crown = z + 0.58 * h
    if n_arch >= 5:
        # 中间最高、向外递小（天安门实物：5.9 / 4.4 / 3.5 m on 66 m 城台）
        specs = [(-0.262 * w, 0.055 * w), (-0.131 * w, 0.067 * w), (0.0, 0.090 * w),
                 (0.131 * w, 0.067 * w), (0.262 * w, 0.055 * w)]
    elif n_arch == 3:
        specs = [(-0.235 * w, 0.080 * w), (0.0, 0.100 * w), (0.235 * w, 0.080 * w)]
    else:
        specs = [(0.0, min(max(6.5, w * 0.26), 11.0))]
    arch = [(cx, rw / 2.0, crown - rw / 2.0) for cx, rw in specs]   # (cx, r, 起券标高)
    y0, y1 = -d / 2, d / 2

    # 拱顶以上：整片上墙
    if h - (crown - z) > 0.2:
        box(f"{name}·城台上", w, d, h - (crown - z), 0, 0, crown, mat_w)
    # 墩台：券洞之间与两端
    edges, prev = [], -w / 2.0
    for cx, r, _sp in arch:
        edges.append((prev, cx - r))
        prev = cx + r
    edges.append((prev, w / 2.0))
    for i, (x0, x1) in enumerate(edges):
        if x1 - x0 < 0.15:
            continue
        box(f"{name}·墩台{i}", x1 - x0, d, crown - z, (x0 + x1) / 2, 0, z, mat_w)

    # 拱肩：券背以上到拱顶之间是弧线，方盒子填不住，用 8 层薄板逼近弧边
    # （少了这一层，券洞两上角会露出黑洞——五券洞第一次渲就是这么翻车的）
    K = 8
    for i, (cx, r, sp) in enumerate(arch):
        for k in range(K):
            y0k = r * k / K
            y1k = r * (k + 1) / K
            hw = math.sqrt(max(r * r - y0k * y0k, 0.0))
            if r - hw < 0.02:
                continue
            for sx in (-1, 1):
                box(f"{name}·拱肩{i}{k}{'EW'[sx > 0]}", r - hw, d, y1k - y0k,
                    cx + sx * (hw + (r - hw) / 2), 0, sp + y0k, mat_w)

    # 券洞：矩形＋半圆的暗色棱柱，加券脸石圈与券脚
    seg = 14
    for i, (cx, r, sp) in enumerate(arch):
        prof = [(-r, 0.0), (r, 0.0)]
        for k in range(1, seg):
            a = math.pi * k / seg
            prof.append((r * math.cos(a), (sp - z) + r * math.sin(a)))
        prof.append((-r, (sp - z)))
        n = len(prof)
        verts, faces = [], []
        for yy in (y0 - 0.05, y1 + 0.05):
            for (px, pz) in prof:
                verts.append((cx + px, yy, z + pz))
        faces.append(tuple(range(n)))
        faces.append(tuple(range(n, 2 * n))[::-1])
        for k in range(n):
            j = (k + 1) % n
            faces.append((k, j, n + j, n + k))
        mesh_from(f"{name}·券洞{i}", verts, faces, mat_d, merge=False)
        for sx in (-1, 1):
            box(f"{name}·券脚{i}{'EW'[sx > 0]}", 0.34, 0.30, sp - z + 0.05,
                cx + sx * (r + 0.17), y0 - 0.06, z, mat_s)
        for k in range(seg):
            a0 = math.pi * k / seg
            a1 = math.pi * (k + 1) / seg
            p0 = ((r + 0.00) * math.cos(a0), (r + 0.00) * math.sin(a0))
            p1 = ((r + 0.00) * math.cos(a1), (r + 0.00) * math.sin(a1))
            q0 = ((r + 0.42) * math.cos(a0), (r + 0.42) * math.sin(a0))
            q1 = ((r + 0.42) * math.cos(a1), (r + 0.42) * math.sin(a1))
            vv = []
            for yy in (y0 - 0.07, y0 - 0.01):
                for (px, pz) in (p0, q0, q1, p1):
                    vv.append((cx + px, yy, sp + pz))
            ff = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2),
                  (2, 6, 7, 3), (3, 7, 4, 0)]
            mesh_from(f"{name}·券脸{i}_{k}", vv, ff, mat_s, merge=False)

    # 城台顶女墙：四面围合。原来只做南、北两条，东西两边的台顶边敞着，
    # 12 m 高的砖台顶上看过去就是一条没有压顶的裸边（鸟瞰尤其明显）。
    for sy in (-1, 1):
        box(f"{name}·女墙{'SN'[sy > 0]}", w - 1.2, 0.7, 1.15, 0,
            sy * (d / 2 - 0.4), z + h, mat_w)
    for sx in (-1, 1):
        box(f"{name}·女墙{'EW'[sx > 0]}", 0.7, d - 1.2, 1.15,
            sx * (w / 2 - 0.4), 0, z + h, mat_w)

    # 两侧翼墙：让门接进一道墙里；端头加墩收口
    # wing_off：翼墙组沿**墙厚方向**平移到城墙中线上。承天门 / 玄武门的城台中心
    # 比城墙线各内收 10.5 m（城台有意往外挑），翼墙若还跟着城台中心走，
    # 翼墙端头就与 6 m 厚的城墙错开半米多，接口处露一条竖缝。
    sw = float(wing) if wing else gate_wing(w)
    st, shh = max(3.2, min(d * 0.42, 8.0)), h * 0.90
    yo = wing_off
    _rise = max(0.38, st * 0.24)          # 墙帽要有真正的坡，不然 8~18 m 宽的翼墙顶就是块平板
    for sx in (-1, 1):
        cxw = sx * (w / 2 + sw / 2)
        box(f"{name}·翼墙{'EW'[sx > 0]}", sw, st, shh, cxw, yo, z, mat_w)
        _cb = set(_col().objects)
        _cap = ROOF.two_slope(_self(), f"{name}·翼墙帽{'EW'[sx > 0]}",
                              sw + 0.9, st + 0.9, z + shh - 0.16, _rise,
                              mat=MAT.get("glaze_plain_dark") or MAT.get("tile_gray")
                              or MAT["tile_gray"])
        _roof_offset(_cb, cxw, yo)
        box(f"{name}·墙端{'EW'[sx > 0]}", 2.4, st + 1.0, shh + 0.6,
            sx * (w / 2 + sw - 1.2), yo, z, mat_w)
        # 八字墙：翼墙到头后向内折回一段，收成有交代的门口，而不是截断在半空
        box(f"{name}·八字墙{'EW'[sx > 0]}", st, 12.0, shh * 0.94,
            sx * (w / 2 + sw - st / 2), yo + face * (12.0 + st / 2), z, mat_w)
        _c2b = set(_col().objects)
        _cap2 = ROOF.two_slope(_self(), f"{name}·八字帽{'EW'[sx > 0]}",
                               st + 0.9, 12.9, z + shh * 0.94, max(0.48, _rise * 0.8),
                               mat=MAT.get("glaze_plain_dark") or MAT.get("tile_gray")
                              or MAT["tile_gray"])
        # 帽要落在八字墙上（墙中心 y = 12 + st/2）。原来写死 6.0，
        # 帽子就整块盖在翼墙顶上、被翼墙帽压住——S/N 门看不见，E/W 门一转 90° 就飞到护城河上。
        _roof_offset(_c2b, sx * (w / 2 + sw - st / 2), yo + face * (12.0 + st / 2))

    # 门楼：城台上复用 hall()
    tw, td = w * 0.56, d * 0.62
    hall(name + "·门楼", tw, td, z=z + h + 1.15, storeys=2, base_h=0.55,
         col_h=min(6.4, tw * 0.16), plaque=None, lod=2,
         stairs=False, balustrade=False)



