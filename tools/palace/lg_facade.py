"""宫殿立面构件库 —— 隔扇门、槛墙、匾额、柱础、石栏。

与 precise_lib.py 的分工：precise_lib 负责台基 / 柱网 / 额枋 / 斗拱 / 屋顶，
本模块只负责"外皮"（隔扇、槛墙、匾额、柱础），全部按明官式比例做近看细节。

坐标与返回值约定
----------------
* 每个函数第一个参数 ``pl`` 是 precise_lib 模块（本模块不 import 它，避免环依赖）。
* ``x, y`` = 构件**平面中心**；``z`` = 构件**下沿标高**（米）。
* ``rot`` 绕构件**自身中心**旋转：0 = 面向 -Y（南立面）、π/2 = 朝 +X（东）、
  π = 朝 +Y（北）、-π/2 = 朝 -X（西）。
  做法：顶点在**局部坐标**里建（平面以原点为中心），最后才设 ``ob.location`` 与
  ``ob.rotation_euler``。precise_lib.box 把世界坐标直接写进顶点、物体原点留在
  (0,0,0)，再去设 rotation_euler 就会绕世界原点甩走 —— 本模块不这么干。
* 返回值：``lattice_door`` / ``plaque`` / ``column_base`` / ``railing`` 返回
  ``(对象数, 三角面数)``；``bay_skin`` 返回统计字典（含 spans / names）。

所有尺寸单位：米。所有几何都在调用前需先 ``pl.make_materials()``。
"""

import math

import bmesh
import bpy

__all__ = ["lattice_door", "bay_skin", "plaque", "column_base", "railing",
           "LEAF_T", "LEAF_STILE", "LEAF_RAIL", "BAR_W", "BAR_T", "SILL_H"]

# ---------------------------------------------------------------- 隔扇常数
LEAF_T = 0.09        # 隔扇整体厚
LEAF_STILE = 0.12    # 边梃宽
LEAF_RAIL = 0.10     # 抹头高
LEAF_GAP = 0.02      # 扇与扇之间
BAR_W = 0.042        # 棂条宽（原 0.028 太细，隔扇格心远看像铁丝网）
BAR_T = 0.03         # 棂条厚
SILL_H = 0.20        # 下槛高
ZC_SKIRT = 0.28      # 裙板下界（占全高比例）
ZC_KUAN = 0.42       # 绦环板上界（28% + 14%）
DIAG_STEP = 0.235    # 菱花斜棂的垂直间距（格眼放大，才对得上三交六椀的尺度）
EMBED = 0.010        # 同材质木构件之间的微量叠压，只为躲开共面 z-fighting

FONT_PATHS = (r"C:\Windows\Fonts\simhei.ttf", r"C:\Windows\Fonts\msyh.ttc")
_FONT = [None]       # 缓存；None = 未尝试，False = 全部加载失败


# ================================================================ 底层缓冲
class _Buf:
    """顶点 / 面累加器（局部坐标），最后一次性丢给 pl.mesh_from。"""

    __slots__ = ("v", "f")

    def __init__(self):
        self.v = []
        self.f = []

    # -------------------------------------------------- 轴对齐盒子
    def box(self, x0, x1, y0, y1, z0, z1):
        if x1 < x0:
            x0, x1 = x1, x0
        if y1 < y0:
            y0, y1 = y1, y0
        if z1 < z0:
            z0, z1 = z1, z0
        b = len(self.v)
        for z in (z0, z1):
            for xy in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
                self.v.append((xy[0], xy[1], z))
        self.f += [(b + 0, b + 3, b + 2, b + 1), (b + 4, b + 5, b + 6, b + 7),
                   (b + 0, b + 1, b + 5, b + 4), (b + 1, b + 2, b + 6, b + 5),
                   (b + 2, b + 3, b + 7, b + 6), (b + 3, b + 0, b + 4, b + 7)]

    # -------------------------------------------------- XZ 平面斜条（沿 Y 拉伸）
    def bar(self, p0, p1, hw, y0, y1):
        dx, dz = p1[0] - p0[0], p1[1] - p0[1]
        ln = math.hypot(dx, dz)
        if ln < 1e-9:
            return
        nx, nz = -dz / ln * hw, dx / ln * hw
        pts = [(p0[0] + nx, p0[1] + nz), (p1[0] + nx, p1[1] + nz),
               (p1[0] - nx, p1[1] - nz), (p0[0] - nx, p0[1] - nz)]
        b = len(self.v)
        for y in (y0, y1):
            for (x, z) in pts:
                self.v.append((x, y, z))
        self.f += [(b + 3, b + 2, b + 1, b + 0), (b + 4, b + 5, b + 6, b + 7),
                   (b + 0, b + 1, b + 5, b + 4), (b + 1, b + 2, b + 6, b + 5),
                   (b + 2, b + 3, b + 7, b + 6), (b + 3, b + 0, b + 4, b + 7)]

    # -------------------------------------------------- 三棱柱（如意角花）
    def tri(self, a, b, c, y0, y1):
        i = len(self.v)
        for y in (y0, y1):
            for (x, z) in (a, b, c):
                self.v.append((x, y, z))
        self.f += [(i + 0, i + 1, i + 2), (i + 5, i + 4, i + 3),
                   (i + 0, i + 1, i + 4, i + 3), (i + 1, i + 2, i + 5, i + 4),
                   (i + 2, i + 0, i + 3, i + 5)]

    # -------------------------------------------------- 正 n 棱柱 / 圆柱
    def cyl(self, cx, cy, z0, z1, r, n=24, phase=0.0):
        b = len(self.v)
        for z in (z0, z1):
            for i in range(n):
                a = phase + 2.0 * math.pi * i / n
                self.v.append((cx + r * math.cos(a), cy + r * math.sin(a), z))
        for i in range(n):
            j = (i + 1) % n
            self.f.append((b + i, b + j, b + n + j, b + n + i))
        self.f.append(tuple(b + n + i for i in range(n)))
        self.f.append(tuple(b + i for i in range(n - 1, -1, -1)))


def _fix_normals(ob):
    """逐壳重算法线朝外（各构件都是闭合壳，安全）。"""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def _flush(pl, name, parts):
    """parts = [(后缀, 材质, _Buf)] -> [obj]"""
    objs = []
    for suffix, mat, buf in parts:
        if not buf.f:
            continue
        ob = pl.mesh_from("%s·%s" % (name, suffix), buf.v, buf.f, mat, merge=False)
        _fix_normals(ob)
        objs.append(ob)
    return objs


def _tris(objs):
    n = 0
    for ob in objs:
        ob.data.calc_loop_triangles()
        n += len(ob.data.loop_triangles)
    return n


# ================================================================ 字形
def _font():
    if _FONT[0] is not None:
        return _FONT[0] or None
    for fp in FONT_PATHS:
        try:
            _FONT[0] = bpy.data.fonts.load(fp)
            return _FONT[0]
        except Exception:
            continue
    _FONT[0] = False
    print("[lg_facade] 警告：simhei/msyh 都加载失败，匾额文字将用内置字体")
    return None


def _text_mesh(pl, name, body, size, extrude, mat, loc, rot_z, res=6):
    """FONT 曲线 -> MESH 物体（保留 precise_lib 的字体加载方式）。"""
    cu = bpy.data.curves.new(name, type="FONT")
    cu.body = body
    cu.size = size
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.resolution_u = res
    cu.extrude = extrude
    ft = _font()
    if ft:
        cu.font = ft
    try:
        col = pl._col()
    except Exception:
        col = bpy.context.scene.collection
    ob = bpy.data.objects.new(name, cu)
    col.objects.link(ob)
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    try:
        bpy.ops.object.convert(target="MESH")
        ob = bpy.context.view_layer.objects.active or ob
    except Exception as exc:      # 兜底：直接取求值网格
        print("[lg_facade] convert 失败，改用 to_mesh:", exc)
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        old = ob.data
        ob.data = me
        bpy.data.curves.remove(old)
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    for p in ob.data.polygons:
        p.use_smooth = False
    ob.location = loc
    ob.rotation_euler = (math.pi / 2.0, 0.0, rot_z)
    return ob


# ================================================================ 格心
def _clip_seg(p0, p1, x0, x1, z0, z1):
    """Liang-Barsky：把线段裁到矩形 [x0,x1]×[z0,z1]，返回新端点或 None。"""
    dx, dz = p1[0] - p0[0], p1[1] - p0[1]
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, p0[0] - x0), (dx, x1 - p0[0]),
                 (-dz, p0[1] - z0), (dz, z1 - p0[1])):
        if abs(p) < 1e-12:
            if q < 0.0:
                return None
            continue
        r = q / p
        if p < 0.0:
            if r > t1:
                return None
            if r > t0:
                t0 = r
        else:
            if r < t0:
                return None
            if r < t1:
                t1 = r
    if t1 - t0 < 1e-6:
        return None
    return ((p0[0] + dx * t0, p0[1] + dz * t0),
            (p0[0] + dx * t1, p0[1] + dz * t1))


def _lat_diamond(buf, x0, x1, z0, z1, step=DIAG_STEP):
    """三交六椀 / 菱花：两族 45° 斜棂相交成菱形格（圆点省略）。"""
    hw = BAR_W / 2.0
    y0, y1 = -BAR_T / 2.0, BAR_T / 2.0
    span = (x1 - x0) + (z1 - z0) + 0.5
    step = step * math.sqrt(2.0)
    # 族 A：z = x + c
    c = z0 - x1 + step * 0.5
    while c < z1 - x0:
        seg = _clip_seg((x0 - span, x0 - span + c), (x1 + span, x1 + span + c),
                        x0, x1, z0, z1)
        if seg:
            buf.bar(seg[0], seg[1], hw, y0, y1)
        c += step
    # 族 B：z = -x + c
    c = z0 + x0 + step * 0.5
    while c < z1 + x1:
        seg = _clip_seg((x0 - span, c - (x0 - span)), (x1 + span, c - (x1 + span)),
                        x0, x1, z0, z1)
        if seg:
            buf.bar(seg[0], seg[1], hw, y0, y1)
        c += step


def _lat_step(buf, x0, x1, z0, z1, sx=0.14, sz=0.30):
    """步步锦：直棂条 + 错缝横棂（远看像步步锦，面数很低）。"""
    hw = BAR_W / 2.0
    y0, y1 = -BAR_T / 2.0, BAR_T / 2.0
    nx = max(2, int(round((x1 - x0) / sx)))
    for i in range(1, nx):
        x = x0 + (x1 - x0) * i / nx
        buf.box(x - hw, x + hw, y0, y1, z0, z1)
    nz = max(2, int((z1 - z0) / sz))
    for j in range(1, nz):
        z = z0 + (z1 - z0) * j / nz
        for i in range(nx):
            if (i + j) % 2:
                continue
            xa = x0 + (x1 - x0) * i / nx
            xb = x0 + (x1 - x0) * (i + 1) / nx
            buf.box(xa, xb, y0, y1, z - hw, z + hw)


# ================================================================ 一扇
TRANSOM_T = 0.08     # 横披窗厚
TRANSOM_B = 0.09     # 横披窗框宽


def _transom_win(fr, lt, w, h, lod, t=TRANSOM_T, b=TRANSOM_B):
    """横披窗（局部坐标）：四边框 + 棂条。lod0 塞一块板，免得透空。"""
    ht = t / 2.0
    fr.box(-w / 2, w / 2, -ht, ht, 0.0, b)
    fr.box(-w / 2, w / 2, -ht, ht, h - b, h)
    fr.box(-w / 2, -w / 2 + b, -ht, ht, b, h - b)
    fr.box(w / 2 - b, w / 2, -ht, ht, b, h - b)
    ix0, ix1 = -w / 2 + b + EMBED, w / 2 - b - EMBED
    iz0, iz1 = b + EMBED, h - b - EMBED
    if lod <= 0:
        fr.box(ix0, ix1, -0.02, 0.02, iz0, iz1)
    elif lod == 1:
        fr.box(ix0, ix1, 0.020, 0.042, iz0, iz1)      # 背板，同框色
        _lat_step(lt, ix0, ix1, iz0, iz1, sx=0.34, sz=0.50)
    else:
        fr.box(ix0, ix1, 0.020, 0.042, iz0, iz1)      # 背板，同框色
        _lat_diamond(lt, ix0, ix1, iz0, iz1, step=0.235)


def _leaf(fr, lt, bd, x0, lw, h, lod):
    """单扇：边梃 / 抹头 / 格心 / 绦环板 / 裙板 / 格心背板，局部 x0 为扇左沿。

    bd = 格心背板缓冲。菱花后面必须有一层暗板：以前格心是透空的，背后就是
    砖红墙身，整排隔扇在正立面上直接糊成一大片死红，看不出是门。"""
    st, ra, t = LEAF_STILE, LEAF_RAIL, LEAF_T
    x1 = x0 + lw
    ht = t / 2.0
    zr = ZC_SKIRT * h
    zk = ZC_KUAN * h
    # 边梃（通高）
    fr.box(x0, x0 + st, -ht, ht, 0.0, h)
    fr.box(x1 - st, x1, -ht, ht, 0.0, h)
    # 抹头：下、上、裙板上、绦环板上
    fr.box(x0 + st, x1 - st, -ht, ht, 0.0, ra)
    fr.box(x0 + st, x1 - st, -ht, ht, h - ra, h)
    fr.box(x0 + st, x1 - st, -ht, ht, zr - ra / 2, zr + ra / 2)
    fr.box(x0 + st, x1 - st, -ht, ht, zk - ra / 2, zk + ra / 2)
    ix0, ix1 = x0 + st, x1 - st
    # ---- 裙板：实心板，比边框凸出 0.02，四角如意角花
    sz0, sz1 = ra, zr - ra / 2
    fr.box(ix0 - EMBED, ix1 + EMBED, -(ht + 0.02), ht + 0.02, sz0, sz1)
    if lod >= 2 and sz1 - sz0 > 0.08 and ix1 - ix0 > 0.08:
        s = min(0.10, (ix1 - ix0) * 0.22, (sz1 - sz0) * 0.22)
        fy0 = -(ht + 0.02) - 0.012
        fy1 = -(ht + 0.02) + 0.006
        for (px, sx) in ((ix0 + EMBED, 1.0), (ix1 - EMBED, -1.0)):
            for (pz, sz) in ((sz0 + 0.012, 1.0), (sz1 - 0.012, -1.0)):
                fr.tri((px + sx * s, pz), (px, pz + sz * s), (px, pz), fy0, fy1)
    # ---- 绦环板：实心板 + 一圈细边框
    kz0, kz1 = zr + ra / 2, zk - ra / 2
    kt = t * 0.30
    fr.box(ix0 - EMBED, ix1 + EMBED, -kt / 2, kt / 2, kz0, kz1)
    if lod >= 1:
        bw = 0.032
        bt = kt / 2 + 0.012
        fr.box(ix0 - EMBED, ix1 + EMBED, -bt, bt, kz0, kz0 + bw)
        fr.box(ix0 - EMBED, ix1 + EMBED, -bt, bt, kz1 - bw, kz1)
        fr.box(ix0 - EMBED, ix0 + bw, -bt, bt, kz0 + bw - EMBED, kz1 - bw + EMBED)
        fr.box(ix1 - bw, ix1 + EMBED, -bt, bt, kz0 + bw - EMBED, kz1 - bw + EMBED)
    # ---- 格心
    gz0, gz1 = zk + ra / 2, h - ra
    if lod >= 2:
        # 背板：落在菱花之后（Y 向里侧），稍退一档，让棂条有投影
        bd.box(ix0 - EMBED, ix1 + EMBED, 0.020, 0.042, gz0 - EMBED, gz1 + EMBED)
        _lat_diamond(lt, ix0 - EMBED, ix1 + EMBED, gz0 - EMBED, gz1 + EMBED)
    elif lod == 1:
        bd.box(ix0 - EMBED, ix1 + EMBED, 0.020, 0.042, gz0 - EMBED, gz1 + EMBED)
        _lat_step(lt, ix0 - EMBED, ix1 + EMBED, gz0 - EMBED, gz1 + EMBED)


def lattice_door(pl, name, w, h, x, y, z, rot=0.0, lod=2, leaves=None,
                 mat_frame=None):
    """一樘隔扇（按开间铺满 w）。

    w 含扇间 0.02 缝；h 不含下槛。rot 绕自身中心（0 = 面向 -Y）。
    leaves 缺省按 w//0.72 取扇数。返回 (对象数, 三角面数)。
    """
    w = float(w)
    h = float(h)
    n = int(leaves) if leaves else max(1, int(w / 0.72))
    n = max(1, n)
    while n > 1 and (w - (n - 1) * LEAF_GAP) / n < 2 * LEAF_STILE + 0.05:
        n -= 1
    lw = (w - (n - 1) * LEAF_GAP) / n
    fr, lt, bd = _Buf(), _Buf(), _Buf()
    for i in range(n):
        _leaf(fr, lt, bd, -w / 2 + i * (lw + LEAF_GAP), lw, h, lod)
    frame = mat_frame or pl.MAT["door"]
    back = (pl.MAT.get("window_void") or pl.MAT.get("soffit")
            or pl.MAT["door"])
    objs = _flush(pl, name, [("框", frame, fr), ("格心", pl.MAT["lattice"], lt),
                             ("背板", back, bd)])
    for ob in objs:
        ob.location = (x, y, z)
        ob.rotation_euler = (0.0, 0.0, rot)
    return len(objs), _tris(objs)


# ================================================================ 外皮
def _side_axes(side, xs, ys):
    if side in ("S", "N"):
        return xs
    return ys


def _baybox(buf, side, pf, u0, u1, dep0, dep1, z0, z1):
    """把 (沿面 u, 进深 dep) 映射成世界坐标盒；dep 从外皮平面向内为正。"""
    if side == "S":
        buf.box(u0, u1, pf + dep0, pf + dep1, z0, z1)
    elif side == "N":
        buf.box(u0, u1, pf - dep1, pf - dep0, z0, z1)
    elif side == "E":
        buf.box(pf - dep1, pf - dep0, u0, u1, z0, z1)
    else:  # W
        buf.box(pf + dep0, pf + dep1, u0, u1, z0, z1)


def _baypos(side, pf, u, dep):
    """平面中心落在 (u, 进深 dep) 的世界坐标，给旋转构件用。"""
    if side == "S":
        return u, pf + dep
    if side == "N":
        return u, pf - dep
    if side == "E":
        return pf - dep, u
    return pf + dep, u


def bay_skin(pl, name, xs, ys, w, d, z0, col_h, lod=2,
             col_r=0.46, gap=0.03, base_k=2.3,
             sides=("S", "N", "E", "W"), door_frac=0.80, sill_h=SILL_H,
             top_rail=0.16, wall_h=1.05, wall_stone=0.12, transom=True,
             base_h=0.28, leaves=None, mat_frame=None):
    """按开间铺一殿的外皮。

    南/北面：抱框 + 下槛（0.2）+ 隔扇 + 上槛（0.16）+ 横披窗（到额枋下皮 - 0.03）；
    door_frac = 隔扇顶高 / 檐柱高。0.66 时横披窗高达 3.6 m，大半面墙都是暗格，
    改 0.80 才对得上故宫实物的窄横披。
    东/西面：抱框 + 槛墙（1.05，含 0.12 石活压面）+ 隔扇 + 上槛 + 横披窗。
    柱轴线 xs/ys（含两端）是唯一权威；w/d 只用于命名与校验。
    base_k = 柱础直径/柱半径（与 column_base 同口径），用来把外皮从柱础边上让开（0 = 只让柱）；
    让出来的那一条（clear - col_r）正好由抱框填上，否则每个开间两端会透光。
    返回统计字典（objects/tris/doors/leaves/spans/names 等），names 里的对象可直接查。
    """
    xs = [float(v) for v in xs]
    ys = [float(v) for v in ys]
    z0 = float(z0)
    col_h = float(col_h)
    t = LEAF_T
    ht = t / 2.0
    # 外皮到柱轴线的退让：柱础比柱粗多少就得让多少（柱础半径 = base_k·col_r/2）
    clear = max(col_r, base_k * col_r * 0.5) + gap
    top_hi = z0 + col_h - gap                     # 额枋下皮 - 缝
    dtop = z0 + door_frac * (col_h - gap)         # 隔扇上沿
    dtop = max(dtop, z0 + sill_h + 1.0)
    dtop = min(dtop, top_hi - top_rail - 0.10)
    st = {"objects": 0, "tris": 0, "doors": 0, "leaves": 0, "sills": 0,
          "walls": 0, "transoms": 0, "sides": {}, "spans": [], "names": [],
          "clear": clear, "door_top": dtop, "top_hi": top_hi}
    frame = mat_frame or pl.MAT["door"]
    for side in sides:
        axis = _side_axes(side, xs, ys)
        if len(axis) < 2:
            continue
        if side == "S":
            pf, rot = ys[0] + gap, 0.0
        elif side == "N":
            pf, rot = ys[-1] - gap, math.pi
        elif side == "E":
            pf, rot = xs[-1] - gap, math.pi / 2.0
        elif side == "W":
            pf, rot = xs[0] + gap, -math.pi / 2.0
        else:
            continue
        nb = 0
        for i in range(len(axis) - 1):
            u0 = axis[i] + clear
            u1 = axis[i + 1] - clear
            bw = u1 - u0
            if bw < 0.6:
                continue
            uc = (u0 + u1) / 2.0
            tag = "%s·%s%d" % (name, side, i)
            bufs = []
            if side in ("S", "N"):
                # 下槛：0.2 高木框，比隔扇外皮再凸 0.02
                bufs.append(("下槛·%s" % side, frame, _Buf()))
                _baybox(bufs[-1][2], side, pf, u0, u1, -0.02, 0.12, z0, z0 + sill_h)
                zd0 = z0 + sill_h
                st["sills"] += 1
            else:
                # 槛墙：砖体 + 0.12 石活压面
                bufs.append(("槛墙·%s" % side, pl.MAT["wall"], _Buf()))
                _baybox(bufs[-1][2], side, pf, u0, u1, 0.0, 0.24,
                        z0, z0 + wall_h - wall_stone)
                bufs.append(("压面石·%s" % side, pl.MAT["stone"], _Buf()))
                _baybox(bufs[-1][2], side, pf, u0, u1, -0.03, 0.27,
                        z0 + wall_h - wall_stone, z0 + wall_h)
                zd0 = z0 + wall_h
                st["walls"] += 1
            # 隔扇
            nl = int(leaves) if leaves else max(1, int(bw / 0.72))
            px, py = _baypos(side, pf, uc, ht)
            cnt, tri = lattice_door(pl, tag + "·隔扇", bw, dtop - zd0, px, py,
                                    zd0, rot=rot, lod=lod, leaves=nl, mat_frame=frame)
            st["objects"] += cnt
            st["tris"] += tri
            st["doors"] += 1
            st["leaves"] += max(1, nl)
            for suf in ("框", "格心"):
                nm = "%s·隔扇·%s" % (tag, suf)
                if bpy.data.objects.get(nm):
                    st["names"].append(nm)
            st["spans"].append({"side": side, "i": i, "u0": u0, "u1": u1,
                                "z0": zd0, "z1": dtop})
            # 抱框：柱面到隔扇边那一条（clear - col_r），没有它每个开间两端都透光
            if clear - col_r > 0.008 and dtop - (z0 + base_h) > 0.2:
                posts = _Buf()
                for ua, ub in ((axis[i] + col_r, u0), (u1, axis[i + 1] - col_r)):
                    _baybox(posts, side, pf, ua, ub, -0.01, 0.10,
                            z0 + base_h, dtop)
                bufs.append(("抱框·%s" % side, frame, posts))
            # 上槛
            zb = dtop
            bufs.append(("上槛·%s" % side, frame, _Buf()))
            _baybox(bufs[-1][2], side, pf, u0, u1, -0.01, 0.11, zb, zb + top_rail)
            objs = _flush(pl, tag, bufs)
            st["objects"] += len(objs)
            st["tris"] += _tris(objs)
            st["names"] += [o.name for o in objs]
            # 横披窗：上槛以上直到额枋下皮 - 0.03
            zt = zb + top_rail
            if transom and top_hi - zt > 0.45:
                tfr, tlt = _Buf(), _Buf()
                _transom_win(tfr, tlt, bw, top_hi - zt, lod)
                tobs = _flush(pl, tag + "·横披", [("框", frame, tfr),
                                                 ("棂", pl.MAT["lattice"], tlt)])
                px, py = _baypos(side, pf, uc, ht + 0.005)
                for ob in tobs:
                    ob.location = (px, py, zt)
                    ob.rotation_euler = (0.0, 0.0, rot)
                st["objects"] += len(tobs)
                st["tris"] += _tris(tobs)
                st["transoms"] += 1
                st["names"] += [o.name for o in tobs]
            nb += 1
        st["sides"][side] = nb
    return st


# ================================================================ 匾额
def _plaque_ratio(nchar):
    """按字数控宽高比：3 字 ≈ 2.4:1。"""
    return max(1.25, min(5.0, 0.62 * nchar + 0.55))


def plaque(pl, name, text, w, h, x, y, z, lod=2, rot=0.0, depth=0.16):
    """匾额：金框 + 蓝底 + 阴刻金字。w/h 传 0 或 None 时按字数补比例。

    x,y = 平面中心；z = 下沿；rot 同 lattice_door。返回 (对象数, 三角面数)。
    """
    text = text or ""
    n = max(1, len(text))
    ratio = _plaque_ratio(n)
    w = float(w or 0.0)
    h = float(h or 0.0)
    if w <= 0 and h <= 0:
        h, w = 1.0, ratio
    elif w <= 0:
        w = h * ratio
    elif h <= 0:
        h = w / ratio
    depth = float(depth)
    gold, blue = pl.MAT["gold"], pl.MAT["plaque"]
    # 局部坐标：平面中心在原点，z 自 0 起
    fr, fld, dec = _Buf(), _Buf(), _Buf()
    fb = min(0.13, 0.055 * w, 0.10 * h)            # 框宽
    # 金框做成**一圈**（不是实心块），否则蓝底和字都被埋在里面
    fr.box(-w / 2, w / 2, -depth / 2, depth / 2, 0.0, fb)
    fr.box(-w / 2, w / 2, -depth / 2, depth / 2, h - fb, h)
    fr.box(-w / 2, -w / 2 + fb, -depth / 2, depth / 2, fb, h - fb)
    fr.box(w / 2 - fb, w / 2, -depth / 2, depth / 2, fb, h - fb)
    fh = depth - 0.06                                # 匾心厚 0.10
    ff = -depth / 2 + 0.03                           # 匾心前皮
    fld.box(-w / 2 + fb, w / 2 - fb, ff, ff + fh, fb, h - fb)
    if lod >= 1:                                     # 内圈金线
        lip = 0.028
        lp0, lp1 = -depth / 2 + 0.012, -depth / 2 + 0.030
        dec.box(-w / 2 + fb - lip, w / 2 - fb + lip, lp0, lp1, fb - lip, fb)
        dec.box(-w / 2 + fb - lip, w / 2 - fb + lip, lp0, lp1, h - fb, h - fb + lip)
        dec.box(-w / 2 + fb - lip, -w / 2 + fb, lp0, lp1, fb, h - fb)
        dec.box(w / 2 - fb, w / 2 - fb + lip, lp0, lp1, fb, h - fb)
    if lod >= 2:                                     # 四角金龙云头
        s = min(0.10, 0.5 * fb)
        for sx in (-1.0, 1.0):
            for sz in (-1.0, 1.0):
                cx = sx * (w / 2 - fb / 2)
                cz = h / 2 + sz * (h / 2 - fb / 2)
                dec.box(cx - s, cx + s, -depth / 2 - 0.012, -depth / 2 + 0.02,
                        cz - s * 0.55, cz + s * 0.55)
    objs = _flush(pl, name, [("框", gold, fr), ("心", blue, fld), ("边", gold, dec)])
    for ob in objs:
        ob.location = (x, y, z)
        ob.rotation_euler = (0.0, 0.0, rot)
    # 文字：局部偏移要跟着转，绕 X 抬 90° 后字面朝 -Y
    fw = w - 2 * fb - 0.10
    fhgt = h - 2 * fb - 0.06
    size = max(0.03, min(fw * 0.90 / n, fhgt * 0.68))
    if text:
        off = (0.0, ff + 0.005, h / 2.0)
        co, si = math.cos(rot), math.sin(rot)
        lx = co * off[0] - si * off[1]
        ly = si * off[0] + co * off[1]
        ob = _text_mesh(pl, "%s·文" % name, text, size, 0.032, gold,
                        (x + lx, y + ly, z + off[2]), rot,
                        res=6 if lod >= 2 else 4)
        objs.append(ob)
    return len(objs), _tris(objs)


# ================================================================ 柱础
def column_base(pl, x, y, z, r, k=2.3, h=0.28, n_oct=8, n_cyl=24, mat=None):
    """鼓镜柱础：径 = k×柱径、高 h，上圆下八边形，汉白玉。返回 (对象数, 三角面数)。

    "柱径"这里取 **柱半径 r**：鼓镜直径 = k·r（k=2.3 时 ≈1.15×柱全径，正是官式鼓镜的
    比例，也只比柱面凸出 0.057 m）。
    若按柱全径 D=2r 取 2.3×，鼓镜直径会到 4.6r（r=0.38 时 1.75 m），吃掉开间近 1/3、
    和隔扇下槛 / 槛墙打架 —— 所以不取。要改口径只需调 k。
    """
    R = k * float(r) / 2.0
    h = float(h)
    mat = mat or pl.MAT["stone"]
    b = _Buf()
    b.cyl(0.0, 0.0, 0.0, h * 0.5, R, n=n_oct, phase=math.pi / n_oct)
    b.cyl(0.0, 0.0, h * 0.5, h, R * 0.965, n=n_cyl)
    objs = _flush(pl, "柱础", [(mat.name, mat, b)])
    for ob in objs:
        ob.location = (x, y, z)
        for p in ob.data.polygons:          # 上圆侧壁平滑，上下皮保持平直
            p.use_smooth = abs(p.normal.z) < 0.3 and p.center.z > h * 0.5 - 1e-9
    return len(objs), _tris(objs)


# ================================================================ 石栏
def railing(pl, name, x0, x1, y, z, n=None, along_x=True, h=1.1, lod=2):
    """石栏板望柱（台基边缘用）：望柱 + 栏板 + 地栿。返回 (对象数, 三角面数)。"""
    lo, hi = (x0, x1) if x0 <= x1 else (x1, x0)
    n = int(n or max(2, round((hi - lo) / 2.4)))
    n = max(1, n)
    post, panel, curb = _Buf(), _Buf(), _Buf()
    pw = 0.28
    for i in range(n + 1):
        u = lo + (hi - lo) * i / n
        if along_x:
            curb.box(u - pw / 2, u + pw / 2, -pw / 2, pw / 2, 0.0, 0.16)
            post.box(u - pw / 2, u + pw / 2, -pw / 2, pw / 2, 0.16, h)
        else:
            curb.box(-pw / 2, pw / 2, u - pw / 2, u + pw / 2, 0.0, 0.16)
            post.box(-pw / 2, pw / 2, u - pw / 2, u + pw / 2, 0.16, h)
    for i in range(n):
        a = lo + (hi - lo) * i / n + pw / 2
        c = lo + (hi - lo) * (i + 1) / n - pw / 2
        if c - a < 0.1:
            continue
        if along_x:
            panel.box(a, c, -0.06, 0.06, 0.16, h - 0.14)
        else:
            panel.box(-0.06, 0.06, a, c, 0.16, h - 0.14)
    objs = _flush(pl, name, [("望柱", pl.MAT["stone"], post),
                             ("栏板", pl.MAT["stone"], panel),
                             ("地栿", pl.MAT["stone"], curb)])
    for ob in objs:
        ob.location = (0.0, y, z) if along_x else (y, 0.0, z)
    return len(objs), _tris(objs)
