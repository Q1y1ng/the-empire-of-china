"""官式庑殿顶与瓦作构件库（明/清式）。

约定
----
- 坐标：x 东西（+x 东）、y 南北（+y 北）、z 上，单位米。z0 = 檐口（屋面最低边）标高。
- 全部直接拼顶点，不走 bpy.ops，1024 段的屋面也在秒级。
- 屋面网格带 UV，**单位米**：**U 沿檐口方向**（累计米数），**V 沿坡向**（累计米数）。
  琉璃瓦着色器按 TILE_U=0.32 / TILE_V=0.30 的周期切瓦垄，所以网格可以粗（0.8 m 一格），
  瓦垄仍是 0.32 m 一根，不会被网格拉斜（UV 在面内是线性精确的）。
- 举折用《清式营造则例》八步举架（檐步 0.50 → 脊步 0.95），积分后归一，脊高由 H 定。
- 翼角：四角起翘 lift，檐口轮廓在角部抬起，脊线自然跟着走。

用法
----
    import lg_roof as ROOF
    ROOF.roof(PL, "金瓯殿·顶", W, D, z0, H, lod=2)   # 面 + 檐口 + 椽 + 脊
单独调试：
    blender -b --factory-startup -P lg_roof.py -- --out %TEMP%/roof --lod 2
"""

import math
import os
import sys

import bpy

TILE_U = 0.32          # 垄距（筒瓦中距）
TILE_V = 0.30          # 瓦长（外露）
JIA_STEPS = (0.50, 0.56, 0.63, 0.70, 0.77, 0.84, 0.90, 0.95)   # 清式举架


# ------------------------------------------------------------------ 数学
def profile(t):
    """归一化举折曲线：t=0 檐口，t=1 屋脊；返回 0..1 的相对高度。"""
    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0
    n = len(JIA_STEPS)
    seg = 1.0 / n
    i = min(int(t / seg), n - 1)
    acc = sum(JIA_STEPS[:i]) * seg + JIA_STEPS[i] * (t - i * seg)
    return acc / (sum(JIA_STEPS) * seg)


def slope_at(t):
    """t 处的坡度（dz/d水平）。"""
    n = len(JIA_STEPS)
    i = min(max(int(t * n), 0), n - 1)
    return JIA_STEPS[i]


def surf_t(x, y, W, D):
    """归一化坡长：0 在檐口，1 在脊（等坡，四坡同举）。"""
    r = D / 2.0
    return max(0.0, min(1.0, min(r + y, r - y, W / 2 - x, W / 2 + x) / r))


def corner_w(x, y, W, D, p=3.4):
    """角部权重：只在四角为 1，沿檐口迅速衰减。"""
    u = min(abs(x) / (W / 2), 1.0)
    v = min(abs(y) / (D / 2), 1.0)
    return (u ** p) * (v ** p)


def surf_z(x, y, W, D, z0, H, lift=1.35):
    """屋面上任意点标高（含翼角起翘）。"""
    return z0 + H * profile(surf_t(x, y, W, D)) + lift * corner_w(x, y, W, D)


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a):
    m = math.sqrt(a[0] ** 2 + a[1] ** 2 + a[2] ** 2) or 1.0
    return (a[0] / m, a[1] / m, a[2] / m)


# ------------------------------------------------------------------ 网格工具
def _mesh_multi(pl, name, grids, mat, thick=0.36, smooth=True, flip=None):
    """把若干「点阵」拼成一个对象；每个点阵是**列**的列表，列长可以不等（沿戗脊裁短）。

    点：(x, y, z, u, v)。列长不等时，短列顶端与相邻长列之间用三角扇补满。
    行距按物理距离取等距，**不按列归一**，否则瓦口（V 向横缝）会在列间来回跳。
    """
    verts, uvs, faces = [], [], []
    for cols in grids:
        base = len(verts)
        offsets = []
        for col in cols:
            offsets.append(len(verts))
            for p in col:
                verts.append((p[0], p[1], p[2]))
                uvs.append((p[3] if len(p) > 3 else 0.0, p[4] if len(p) > 4 else 0.0))
        nz = 0.0
        quads = []
        for i in range(len(cols) - 1):
            a0, b0 = offsets[i], offsets[i + 1]
            la, lb = len(cols[i]), len(cols[i + 1])
            m = min(la, lb)
            for j in range(m - 1):
                quad = (a0 + j, b0 + j, b0 + j + 1, a0 + j + 1)
                p0, p1, p2 = verts[quad[0]], verts[quad[1]], verts[quad[2]]
                n = _cross(_sub(p1, p0), _sub(p2, p0))
                if math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2) < 1e-10:
                    continue
                nz += n[2]
                quads.append(quad)
            # 长出来的部分：与四边形同绕序补三角（a_top → b_j → b_j+1 方向）
            if la > m:
                for j in range(m - 1, la - 1):
                    quads.append((a0 + j, b0 + m - 1, a0 + j + 1))
            elif lb > m:
                for j in range(m - 1, lb - 1):
                    quads.append((a0 + m - 1, b0 + j, b0 + j + 1))
        if (nz < 0) != bool(flip):
            quads = [tuple(reversed(q)) for q in quads]
        faces.extend(quads)

    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate()
    uv = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index
            uv.data[li].uv = uvs[vi]
    me.update()
    ob = bpy.data.objects.new(name, me)
    (pl._col() if hasattr(pl, "_col") else bpy.context.scene.collection).objects.link(ob)
    ob.data.materials.append(mat)
    if smooth:
        for p in ob.data.polygons:
            p.use_smooth = True
    if thick:
        pl.solidify(ob, thick)
    return ob


# ------------------------------------------------------------------ 屋面
def _arc_table(H, R, n):
    """按行 t（0 檐口 → 1 脊）算坡长（米），供 V 坐标使用；四坡同一张表。"""
    ts = [i / n for i in range(n + 1)]
    zs = [H * profile(t) for t in ts]
    s = [0.0]
    for i in range(n):
        s.append(s[-1] + math.hypot(R / n, zs[i + 1] - zs[i]))
    return ts, s


def hip_surface(pl, name, W, D, z0, H, step=0.8, lift=1.35, mat=None, thick=0.36):
    """庑殿屋面（四坡）。W 面阔（x）、D 进深（y）；等坡，水平进深 R = D/2。"""
    mat = mat or pl.MAT["tile"]
    L = max(W - D, 0.5)
    R = D / 2.0
    nrows = max(5, int(R / max(step, 0.3)))
    ts, vs = _arc_table(H, R, nrows)
    grids = []

    def build(cols, coord, u_of):
        """cols: [(列坐标, tmax)]；行按 t 等距（物理等距），列尾**精确落在戗脊线上**。"""
        g = []
        for (c, tmax) in cols:
            col = []
            jlast = -1
            for j, t in enumerate(ts):
                if t > tmax + 1e-9:
                    break
                px, py = coord(c, t)
                pz = surf_z(px, py, W, D, z0, H, lift)
                col.append((px, py, pz, u_of(c), vs[j]))
                jlast = j
            if jlast >= 0 and tmax - ts[jlast] > 1e-6:
                f = (tmax - ts[jlast]) / (ts[min(jlast + 1, nrows)] - ts[jlast])
                v = (vs[jlast] + (vs[min(jlast + 1, nrows)] - vs[jlast]) * f)
                px, py = coord(c, tmax)
                pz = surf_z(px, py, W, D, z0, H, lift)
                col.append((px, py, pz, u_of(c), v))
            if len(col) >= 2:
                g.append(col)
        return g if len(g) >= 2 else None

    # ---- 南北大坡：列 = 常数 x
    nxs = max(3, int(W / step))
    for sy in (-1, 1):
        cols = []
        for i in range(nxs + 1):
            x = -W / 2 + i * W / nxs
            cols.append((x, 1.0 - max(0.0, abs(x) - L / 2) / R))
        g = build(cols,
                  lambda x, t, sy=sy: (x, sy * R * (1.0 - t)),
                  lambda x: (x + W / 2))
        if g:
            grids.append(g)

    # ---- 东西山面：列 = 常数 y
    nys = max(3, int(D / step))
    for sx in (-1, 1):
        cols = []
        for j in range(nys + 1):
            y = -R + j * D / nys
            cols.append((y, max(0.0, 1.0 - abs(y) / R)))
        g = build(cols,
                  lambda y, t, sx=sx: (sx * (W / 2 - t * R), y),
                  lambda y: (y + R))
        if g:
            grids.append(g)
    return _mesh_multi(pl, name, grids, mat, thick=thick)


def two_slope(pl, name, W, D, z_eave, H, step=0.8, mat=None, thick=0.32):
    """两坡（悬山）顶：W = 脊向长边，D = 进深；举折与四坡同一套 profile。"""
    mat = mat or pl.MAT.get("tile_gray") or pl.MAT["tile"]
    R = D / 2.0
    nrows = max(4, int(R / max(step, 0.35)))
    ts, vs = _arc_table(H, R, nrows)
    nx = max(2, int(W / step))
    grids = []
    for sy in (-1, 1):
        g = []
        for i in range(nx + 1):
            x = -W / 2 + i * W / nx
            col = []
            for j, t in enumerate(ts):
                y = sy * R * (1.0 - t)
                z = z_eave + H * profile(t)
                col.append((x, y, z, x + W / 2, vs[j]))
            g.append(col)
        grids.append(g)
    ob = _mesh_multi(pl, name, grids, mat, thick=thick)
    # 正脊
    zr = z_eave + H
    _rm = pl.MAT.get("glaze_plain_dark") if mat is not pl.MAT.get("tile_gray") else mat
    sweep(pl, name + "·正脊", [(-W / 2, 0.0, zr - 0.04), (W / 2, 0.0, zr - 0.04)],
          0.26, -0.10, 0.34, _rm or mat)
    return ob


def ring_surface(pl, name, OW, OD, IW, ID, z0, H, step=0.8, lift=1.35, mat=None, thick=0.36):
    """重檐下檐（围屋面）：外檐口 OW×OD 升到内圈 IW×ID。"""
    mat = mat or pl.MAT["tile"]
    grids = []
    # 南/北两条
    nxs = max(3, int(OW / step))
    for sy in (-1, 1):
        g = []
        for i in range(nxs + 1):
            u = i / nxs
            xa = -OW / 2 + u * OW
            xi = -IW / 2 + u * IW
            ya, yi = sy * OD / 2, sy * ID / 2
            span = abs(ya - yi)
            ny = max(3, int(span / step))
            col, s = [], 0.0
            prev = None
            for j in range(ny + 1):
                v = j / ny
                x = xa + (xi - xa) * v
                y = ya + (yi - ya) * v
                z = z0 + H * profile(v) + lift * corner_w(xa, ya, OW, OD)
                if prev:
                    s += math.dist((x, y, z), prev)
                prev = (x, y, z)
                col.append((x, y, z, (xa + OW / 2), s))
            g.append(col)
        grids.append(g)
    # 东/西两条
    nys = max(3, int(OD / step))
    for sx in (-1, 1):
        g = []
        for j in range(nys + 1):
            u = j / nys
            ya = -OD / 2 + u * OD
            yi = -ID / 2 + u * ID
            xa, xi = sx * OW / 2, sx * IW / 2
            span = abs(xa - xi)
            nx = max(3, int(span / step))
            col, s = [], 0.0
            prev = None
            for i in range(nx + 1):
                v = i / nx
                x = xa + (xi - xa) * v
                y = ya + (yi - ya) * v
                z = z0 + H * profile(v) + lift * corner_w(xa, ya, OW, OD)
                if prev:
                    s += math.dist((x, y, z), prev)
                prev = (x, y, z)
                col.append((x, y, z, (ya + OD / 2), s))
            g.append(col)
        grids.append(g)
    return _mesh_multi(pl, name, grids, mat, thick=thick)


def _half_tube(verts, faces, pts, w_dir, n_dir, r, steps_side=4):
    """沿 pts 扫一条半圆筒（筒瓦）：pts 已含 z；w_dir 为横向、n_dir 为法向。"""
    ws = (-1.0, -0.62, 0.0, 0.62, 1.0)
    hs = (0.0, 0.78, 1.0, 0.78, 0.0)
    base = len(verts)
    for p in pts:
        for (w, h) in zip(ws, hs):
            verts.append((p[0] + w_dir[0] * w * r + n_dir[0] * h * r,
                          p[1] + w_dir[1] * w * r + n_dir[1] * h * r,
                          p[2] + w_dir[2] * w * r + n_dir[2] * h * r))
    n = len(ws)
    for i in range(len(pts) - 1):
        a = base + i * n
        b = a + n
        for k in range(n - 1):
            faces.append((a + k, a + k + 1, b + k + 1, b + k))


def tile_ribs(pl, name, W, D, z0, H, lift=1.35, t_max=0.55, r=0.085,
              steps=9, mat=None, thick=0.0):
    """檐口一带的**真实筒瓦垄**（lod2 用；更远处由着色器的瓦垄图案接管）。

    垄位与 UV 完全对齐：u = (k+0.5)*TILE_U，所以几何与着色器花纹不会错位。
    """
    mat = mat or pl.MAT["tile"]
    L = max(W - D, 0.5)
    R = D / 2.0
    verts, faces = [], []

    def stations(coord, t_hi, n):
        pts = []
        for i in range(n + 1):
            t = t_hi * i / n
            x, y = coord(t)
            pts.append((x, y, surf_z(x, y, W, D, z0, H, lift)))
        return pts

    # 南/北坡
    nxs = max(3, int(W / TILE_U))
    for sy in (-1, 1):
        for k in range(nxs):
            x = -W / 2 + (k + 0.5) * W / nxs
            t_hi = min(t_max, 1.0 - max(0.0, abs(x) - L / 2) / R)
            if t_hi < 0.04:
                continue
            pts = stations(lambda t: (x, sy * R * (1.0 - t)), t_hi, steps)
            _half_tube(verts, faces, pts, (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), r)
    # 东/西坡
    nys = max(3, int(D / TILE_U))
    for sx in (-1, 1):
        for k in range(nys):
            y = -R + (k + 0.5) * D / nys
            t_hi = min(t_max, max(0.0, 1.0 - abs(y) / R))
            if t_hi < 0.04:
                continue
            pts = stations(lambda t: (sx * (W / 2 - t * R), y), t_hi, steps)
            _half_tube(verts, faces, pts, (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), r)
    return pl.mesh_from(name + "·瓦垄", verts, faces, mat, merge=False)


def ring_ribs(pl, name, OW, OD, IW, ID, z0, H, lift=1.2, t_max=0.55, r=0.085,
              steps=8, mat=None):
    """重檐下檐的筒瓦垄。"""
    mat = mat or pl.MAT["tile"]
    verts, faces = [], []
    nxs = max(3, int(OW / TILE_U))
    for sy in (-1, 1):
        for k in range(nxs):
            u = (k + 0.5) / nxs
            xa = -OW / 2 + u * OW
            xi = -IW / 2 + u * IW
            ya, yi = sy * OD / 2, sy * ID / 2
            pts = []
            for i in range(steps + 1):
                v = t_max * i / steps
                x = xa + (xi - xa) * v
                y = ya + (yi - ya) * v
                z = z0 + H * profile(v) + lift * corner_w(xa, ya, OW, OD) * (1 - v) ** 2
                pts.append((x, y, z))
            _half_tube(verts, faces, pts, (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), r)
    nys = max(3, int(OD / TILE_U))
    for sx in (-1, 1):
        for k in range(nys):
            u = (k + 0.5) / nys
            ya = -OD / 2 + u * OD
            yi = -ID / 2 + u * ID
            xa, xi = sx * OW / 2, sx * IW / 2
            pts = []
            for i in range(steps + 1):
                v = t_max * i / steps
                x = xa + (xi - xa) * v
                y = ya + (yi - ya) * v
                z = z0 + H * profile(v) + lift * corner_w(xa, ya, OW, OD) * (1 - v) ** 2
                pts.append((x, y, z))
            _half_tube(verts, faces, pts, (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), r)
    return pl.mesh_from(name + "·瓦垄", verts, faces, mat, merge=False)


# ------------------------------------------------------------------ 檐口
def _eave_segments(W, D, z0, H, lift, n=90):
    """四条檐口的采样点：[(x,y,z, 外法向)]"""
    segs = []
    for sy in (-1, 1):
        pts = []
        for i in range(n + 1):
            x = -W / 2 + i * W / n * 1.0
            y = sy * D / 2
            pts.append((x, y, surf_z(x, y, W, D, z0, H, lift)))
        segs.append((pts, (0.0, sy, 0.0)))
    for sx in (-1, 1):
        pts = []
        for i in range(n + 1):
            y = -D / 2 + i * D / n
            x = sx * W / 2
            pts.append((x, y, surf_z(x, y, W, D, z0, H, lift)))
        segs.append((pts, (sx, 0.0, 0.0)))
    return segs


def eave_trim(pl, name, W, D, z0, H, lift=1.35, lod=2, mat_tile=None, mat_wood=None):
    """檐口：连檐 + 飞椽（木）+ 瓦当 + 滴水（瓦）。近看全靠这一圈。"""
    mat_tile = mat_tile or pl.MAT["tile"]
    mat_wood = mat_wood or pl.MAT.get("door") or pl.MAT["column"]
    tv, tf = [], []          # 瓦件
    wv, wf = [], []          # 木件
    s0 = slope_at(0.02) * H / (D / 2)

    for pts, nrm in _eave_segments(W, D, z0, H, lift):
        # ---- 连檐：檐口下一道 0.26 m 高的板（截面 4 点沿檐口挤出）
        b0 = len(wv)
        for (x, y, z) in pts:
            ox, oy = x - nrm[0] * 0.06, y - nrm[1] * 0.06
            wv.append((ox, oy, z - 0.02))
            wv.append((ox, oy, z - 0.28))
            wv.append((ox - nrm[0] * 0.10, oy - nrm[1] * 0.10, z - 0.30))
            wv.append((ox - nrm[0] * 0.10, oy - nrm[1] * 0.10, z - 0.04))
        for k in range(len(pts) - 1):
            a = b0 + k * 4
            c = a + 4
            for (u, v) in ((0, 1), (1, 2), (2, 3), (3, 0)):
                wf.append((a + u, a + v, c + v, c + u))

        # ---- 瓦当 / 滴水 / 飞椽
        tang = _norm((pts[1][0] - pts[0][0], pts[1][1] - pts[0][1], 0.0))
        n_out = _norm((nrm[0], nrm[1], s0 * 0.85))
        length = abs(pts[-1][0] - pts[0][0]) + abs(pts[-1][1] - pts[0][1])
        k = max(2, int(length / TILE_U))
        for i in range(k):
            t = (i + 0.5) / k
            fi = t * (len(pts) - 1)
            i0 = min(int(fi), len(pts) - 2)
            fr = fi - i0
            px = pts[i0][0] + (pts[i0 + 1][0] - pts[i0][0]) * fr
            py = pts[i0][1] + (pts[i0 + 1][1] - pts[i0][1]) * fr
            pz = pts[i0][2] + (pts[i0 + 1][2] - pts[i0][2]) * fr
            if lod >= 1:
                _disc(tv, tf, (px + n_out[0] * 0.05, py + n_out[1] * 0.05,
                               pz + n_out[2] * 0.02), n_out, tang, 0.085, 0.05)
            if lod >= 2:
                c2 = (px + tang[0] * TILE_U * 0.5 + n_out[0] * 0.02,
                      py + tang[1] * TILE_U * 0.5 + n_out[1] * 0.02,
                      pz + n_out[2] * 0.02 - 0.06)
                _drip(tv, tf, c2, n_out, tang, 0.13, 0.10)
            _box_t(wv, wf, (px - n_out[0] * 0.34, py - n_out[1] * 0.34, pz - 0.22),
                   tang, n_out, (0.0, 0.0, 1.0), 0.13, 0.62, 0.13)

    ob = pl.mesh_from(name + "·檐口", tv, tf, mat_tile, merge=True)
    ob2 = pl.mesh_from(name + "·连檐飞椽", wv, wf, mat_wood, merge=True) if wv else None
    return ob, ob2


def _disc(verts, faces, c, n, t, r, th):
    """圆盘：法向 n，切向 t，半径 r，厚 th。"""
    b = _norm(_cross(n, t))
    b = _norm((b[0], b[1], b[2]))
    ring = []
    for k in range(6):
        a = 2 * math.pi * k / 6
        ring.append((c[0] + r * (math.cos(a) * t[0] + math.sin(a) * b[0]),
                     c[1] + r * (math.cos(a) * t[1] + math.sin(a) * b[1]),
                     c[2] + r * (math.cos(a) * t[2] + math.sin(a) * b[2])))
    i0 = len(verts)
    for p in ring:
        verts.append(p)
    for p in ring:
        verts.append((p[0] + n[0] * th, p[1] + n[1] * th, p[2] + n[2] * th))
    for k in range(6):
        k2 = (k + 1) % 6
        faces.append((i0 + k, i0 + k2, i0 + 6 + k2, i0 + 6 + k))
    faces.append(tuple(i0 + 6 + k for k in range(6)))


def _drip(verts, faces, c, n, t, w, h):
    """滴水舌板（矩形斜片）。"""
    b = len(verts)
    for dz, dw in ((-h, w * 0.55), (0.0, w)):
        for s in (-1, 1):
            verts.append((c[0] + t[0] * s * dw / 2 + n[0] * 0.0,
                          c[1] + t[1] * s * dw / 2 + n[1] * 0.0,
                          c[2] + dz))
    faces.extend([(b, b + 1, b + 3, b + 2), (b + 4, b + 6, b + 7, b + 5),
                  (b, b + 4, b + 5, b + 1), (b + 2, b + 3, b + 7, b + 6)])


def _box_t(verts, faces, c, ex, ey, ez, sx, sy, sz):
    """按局部基 (ex,ey,ez) 建盒子。"""
    b = len(verts)
    for dz in (-sz / 2, sz / 2):
        for dy in (-sy / 2, sy / 2):
            for dx in (-sx / 2, sx / 2):
                verts.append((c[0] + ex[0] * dx + ey[0] * dy + ez[0] * dz,
                              c[1] + ex[1] * dx + ey[1] * dy + ez[1] * dz,
                              c[2] + ex[2] * dx + ey[2] * dy + ez[2] * dz))
    faces.extend([(b, b + 1, b + 3, b + 2), (b + 4, b + 6, b + 7, b + 5),
                  (b, b + 4, b + 5, b + 1), (b + 2, b + 3, b + 7, b + 6),
                  (b, b + 2, b + 6, b + 4), (b + 1, b + 5, b + 7, b + 3)])


# ------------------------------------------------------------------ 椽
def rafters(pl, name, W, D, z0, H, lift=1.35, lod=2, depth=3.4, mat=None):
    """檐椽 + 飞椽：贴着屋面下方走，绝不穿出瓦面。"""
    if lod <= 1:
        return None
    mat = mat or pl.MAT["soffit"]
    verts, faces = [], []
    L = max(W - D, 0.5)
    drop = 0.34

    def run(col_x, side):
        """col_x: 沿檐口的坐标；side: 'S'/'N'（x 不变）或 'E'/'W'（y 不变）"""
        pts = []
        for k in range(4):
            frac = k / 3.0
            if side in ("S", "N"):
                sy = -1 if side == "S" else 1
                y = sy * (D / 2) + (-sy) * depth * frac
                x = col_x
            else:
                sx = -1 if side == "W" else 1
                x = sx * (W / 2) + (-sx) * depth * frac
                y = col_x
            z = surf_z(x, y, W, D, z0, H, lift) - drop - 0.08 * frac
            pts.append((x, y, z))
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            ex = _norm(_sub(b, a))
            ey = _norm(_cross(ex, (0, 0, 1.0)))
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2)
            seg = math.dist(a, b)
            _box_t(verts, faces, mid, ex, ey, (0, 0, 1.0), 0.15, seg + 0.06, 0.15)

    n_x = max(8, int(W / TILE_U))
    n_y = max(8, int(D / TILE_U))
    for i in range(n_x + 1):
        x = -W / 2 + (i + 0.5) * W / n_x
        run(x, "S")
        run(x, "N")
    for j in range(n_y + 1):
        y = -D / 2 + (j + 0.5) * D / n_y
        run(y, "E")
        run(y, "W")
    return pl.mesh_from(name + "·椽", verts, faces, mat, merge=True)


# ------------------------------------------------------------------ 脊
def sweep(pl, name, pts, half_w, z0, z1, mat, levels=None, close_end=True):
    """沿折线扫一个截面 —— 正脊/垂脊/戗脊通用。

    levels: [(宽度系数, 相对高度系数)]，自下而上；默认给出"脊筒 + 圆顶"的六点截面。
    """
    if levels is None:
        levels = ((1.00, 0.00), (0.94, 0.34), (0.74, 0.74), (0.38, 1.00))
    verts, faces = [], []
    n = len(pts)
    if n < 2:
        return None
    ring = len(levels) * 2
    for i, p in enumerate(pts):
        if i == 0:
            t = _norm(_sub(pts[1], pts[0]))
        elif i == n - 1:
            t = _norm(_sub(pts[-1], pts[-2]))
        else:
            t = _norm(_sub(pts[i + 1], pts[i - 1]))
        right = _norm(_cross(t, (0, 0, 1.0)))
        b = len(verts)
        for (wf, zf) in levels:
            for s in (-1, 1):
                verts.append((p[0] + right[0] * s * half_w * wf,
                              p[1] + right[1] * s * half_w * wf,
                              p[2] + z0 + (z1 - z0) * zf))
        if i > 0:
            b0 = b - ring
            seq = []
            for k in range(len(levels)):
                seq.append(k * 2)
            for k in range(len(levels) - 1, -1, -1):
                seq.append(k * 2 + 1)
            for k in range(len(seq)):
                u, v = seq[k], seq[(k + 1) % len(seq)]
                faces.append((b0 + u, b0 + v, b + v, b + u))
    if close_end:
        seq = []
        for k in range(len(levels)):
            seq.append(k * 2)
        for k in range(len(levels) - 1, -1, -1):
            seq.append(k * 2 + 1)
        faces.append(tuple(seq))
        e = (n - 1) * ring
        faces.append(tuple(e + i for i in reversed(seq)))
    return pl.mesh_from(name, verts, faces, mat, merge=True)


def _hip_line(W, D, z0, H, lift, sx, sy, n=14, inset=0.0):
    """一条垂脊的折线（从脊端到檐角）。"""
    L = max(W - D, 0.5)
    pts = []
    for i in range(n + 1):
        t = i / n
        x = sx * (L / 2 + (W / 2 - L / 2) * t)
        y = sy * (D / 2 + 0.0) * t
        if inset:
            x -= sx * inset * (1 - t)
            y -= sy * inset * (1 - t)
        z = surf_z(x, y, W, D, z0, H, lift) + 0.02
        pts.append((x, y, z))
    return pts


def _cap_tiles(pl, name, pts, z_top, mat, step=0.42, w=0.34, h=0.16):
    """沿折线铺一排盖脊瓦小块（垂脊/戗脊用）：按局部坐标基摆正，不设物体旋转。"""
    verts, faces = [], []
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        seg = math.dist(a, b)
        n = max(1, int(seg / step))
        t = _norm(_sub(b, a))
        right = _norm(_cross(t, (0, 0, 1.0)))
        for k in range(n):
            f = (k + 0.5) / n
            c = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f,
                 a[2] + (b[2] - a[2]) * f + z_top)
            _box_t(verts, faces, c, t, right, (0.0, 0.0, 1.0),
                   seg / n - 0.02, w, h)
    return pl.mesh_from(name, verts, faces, mat, merge=False)


def ridge_set(pl, name, W, D, z0, H, lift=1.35, lod=2, mat=None, kiss=True):
    """正脊 + 鸱吻 + 四条垂脊 + 走兽。"""
    mat = mat or pl.MAT.get("tile2") or pl.MAT["tile"]
    L = max(W - D, 0.5)
    zr = z0 + H
    objs = []
    # 正脊（脊筒：底 0.9、顶 0.56、高 1.05）
    pts = [(-L / 2, 0.0, zr - 0.06), (L / 2, 0.0, zr - 0.06)]
    objs.append(sweep(pl, name + "·正脊", pts, 0.60, -0.14, 1.34, mat))
    # 正脊下的当沟（一条略宽的压边）
    objs.append(sweep(pl, name + "·当沟", pts, 0.76, -0.20, 0.10,
                      pl.MAT.get("tile2") or mat))
    # 盖脊瓦：沿正脊顶排一排小块，破掉"一根光板"
    nseg = max(6, int(L / 0.42))
    vv, ff = [], []
    for i in range(nseg):
        t = (i + 0.5) / nseg
        x = -L / 2 + t * L
        _box_t(vv, ff, (x, 0.0, zr + 1.34 - 0.05), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0),
               (0.0, 0.0, 1.0), L / nseg - 0.02, 0.46, 0.16)
    objs.append(pl.mesh_from(name + "·盖脊瓦", vv, ff, mat, merge=False))
    if kiss:
        for s in (-1, 1):
            objs.append(_chiwen(pl, f"{name}·鸱吻{s}", s * L / 2, zr, s, mat,
                                pl.MAT.get("gold")))
    # 垂脊
    for sx in (-1, 1):
        for sy in (-1, 1):
            hp = _hip_line(W, D, z0, H, lift, sx, sy, n=16)
            objs.append(sweep(pl, f"{name}·垂脊{sx}{sy}", hp, 0.38, -0.36, 0.58, mat))
            objs.append(_cap_tiles(pl, f"{name}·垂脊瓦{sx}{sy}", hp, 0.66, mat,
                                   step=0.40, w=0.30, h=0.18))
            if lod >= 2:
                # 翼角走兽：靠檐口一段排 5 个小兽，坐在脊背上
                for k in range(5):
                    t = 0.86 + 0.024 * k
                    i = min(int(t * (len(hp) - 1)), len(hp) - 2)
                    p = hp[i]
                    sz = 0.34 - 0.026 * k
                    pl.box(f"{name}·走兽{k}", sz * 1.4, sz, sz * 1.15,
                           p[0], p[1], p[2] + 0.60, pl.MAT.get("gold") or mat)
    return [o for o in objs if o]


def _chiwen(pl, name, x_end, zr, s, mat, gold):
    """鸱吻（正吻）：吻座 + 卷尾主体 + 剑把 + 背兽。

    侧看成"逗号"：底宽、背上鼓、尾上卷、口朝脊咬住正脊端；
    轮廓取直线段（不用多点平滑），4 m 高度在 60 m 外才立得住。
    """
    base_z = zr + 0.72                       # 坐在正脊顶（吻座下皮）
    # 吻座
    pl.box(name + "·吻座", 1.95, 1.02, 0.42, x_end + s * 0.72, 0, base_z,
           mat)
    z0 = base_z + 0.42
    prof = [(0.00, 0.00), (1.55, 0.00), (1.95, 0.45), (2.24, 1.30),
            (2.18, 2.20), (1.92, 2.92), (1.46, 3.42), (1.02, 3.66),
            (0.72, 3.56), (0.66, 3.22), (0.88, 2.94), (1.04, 2.66),
            (0.98, 2.42), (0.72, 2.30), (0.36, 2.22), (0.16, 1.86),
            (0.10, 1.30), (0.00, 1.02)]
    sc = 1.16
    verts, faces = [], []
    half = 0.48
    for (dx, dz) in prof:
        verts.append((x_end + s * dx * sc, -half, z0 + dz * sc))
        verts.append((x_end + s * dx * sc, half, z0 + dz * sc))
    n = len(prof)
    for i in range(n):
        j = (i + 1) % n
        faces.append((i * 2, i * 2 + 1, j * 2 + 1, j * 2))
    faces.append(tuple(i * 2 for i in range(n)))
    faces.append(tuple(i * 2 + 1 for i in range(n - 1, -1, -1)))
    ob = pl.mesh_from(name, verts, faces, mat, merge=True)
    # 剑把：斜插在背上
    pl.box(name + "·剑把", 0.20, 0.20, 1.55, x_end + s * 1.72, 0, z0 + 2.95,
           gold or mat)
    pl.box(name + "·剑把座", 0.44, 0.44, 0.26, x_end + s * 1.70, 0, z0 + 2.72,
           gold or mat)
    # 背兽：尾巴根上的小团
    pl.box(name + "·背兽", 0.52, 0.52, 0.52, x_end + s * 1.86, 0, z0 + 1.55,
           gold or mat)
    return ob


def ridge_ring(pl, name, OW, OD, z0, H, lift=1.35, mat=None):
    """重檐围脊：沿内圈矩形一圈脊。"""
    mat = mat or pl.MAT.get("tile2") or pl.MAT["tile"]
    zz = z0 + H
    for sy in (-1, 1):
        sweep(pl, f"{name}·围脊{sy}", [(-OW / 2, sy * OD / 2, zz - 0.05),
                                       (OW / 2, sy * OD / 2, zz - 0.05)],
              0.34, -0.12, 0.55, mat)
    for sx in (-1, 1):
        sweep(pl, f"{name}·围脊x{sx}", [(sx * OW / 2, -OD / 2, zz - 0.05),
                                        (sx * OW / 2, OD / 2, zz - 0.05)],
              0.34, -0.12, 0.55, mat)


def ridge_xie(pl, name, OW, OD, IW, ID, z0, H, lift=1.35, mat=None):
    """下檐四条戗脊（檐角 → 围脊角）。"""
    mat = mat or pl.MAT.get("tile2") or pl.MAT["tile"]
    for sx in (-1, 1):
        for sy in (-1, 1):
            pts = []
            for i in range(12):
                t = i / 11
                x = sx * (OW / 2 + (IW / 2 - OW / 2) * t)
                y = sy * (OD / 2 + (ID / 2 - OD / 2) * t)
                z = z0 + H * profile(t) + lift * corner_w(sx * OW / 2, sy * OD / 2,
                                                          OW, OD) * (1 - t) ** 2 + 0.02
                pts.append((x, y, z))
            sweep(pl, f"{name}·戗脊{sx}{sy}", pts, 0.26, -0.14, 0.36, mat)
            _cap_tiles(pl, f"{name}·戗脊瓦{sx}{sy}", pts, 0.42, mat,
                       step=0.40, w=0.22, h=0.16)


# ------------------------------------------------------------------ 组合
def roof(pl, name, W, D, z0, H, lift=1.35, lod=2, mat=None, thick=0.36):
    """一整套庑殿顶：屋面 + 檐口 + 椽 + 脊。

    瓦面（带 UV）用 `mat`；瓦件（脊、吻、瓦当、滴水）没有 UV，必须用无花纹的釉面材质，
    否则会吃上 0.32 m 周期的瓦垄条纹 —— 由 `pl.MAT["glaze_plain"]` 等提供。
    """
    fix = pl.MAT.get("glaze_plain") or mat or pl.MAT["tile"]
    fix_dark = pl.MAT.get("glaze_plain_dark") or pl.MAT.get("tile2") or fix
    if D > W:                      # 等坡要求脊向为长边，近方形时直接对调
        W, D = D, W
    objs = []
    objs.append(hip_surface(pl, name, W, D, z0, H, step=0.9 if lod < 2 else 0.7,
                            lift=lift, mat=mat, thick=thick))
    if lod >= 1:
        a, b = eave_trim(pl, name, W, D, z0, H, lift=lift, lod=lod, mat_tile=fix)
        objs += [a, b]
    if lod >= 2:
        objs.append(tile_ribs(pl, name, W, D, z0, H, lift=lift, t_max=0.985,
                              steps=14, mat=fix))
        objs.append(rafters(pl, name, W, D, z0, H, lift=lift, lod=lod))
    objs += ridge_set(pl, name, W, D, z0, H, lift=lift, lod=lod, mat=fix_dark)
    return [o for o in objs if o]


def ring_roof(pl, name, OW, OD, IW, ID, z0, H, lift=1.2, lod=2, mat=None):
    """重檐下檐整套。"""
    fix = pl.MAT.get("glaze_plain") or mat or pl.MAT["tile"]
    fix_dark = pl.MAT.get("glaze_plain_dark") or pl.MAT.get("tile2") or fix
    if OD > OW:
        OW, OD = OD, OW
        IW, ID = ID, IW
    objs = [ring_surface(pl, name, OW, OD, IW, ID, z0, H, step=0.9,
                         lift=lift, mat=mat)]
    if lod >= 2:
        objs.append(ring_ribs(pl, name, OW, OD, IW, ID, z0, H, lift=lift,
                              t_max=0.985, steps=12, mat=fix))
    if lod >= 1:
        a, b = eave_trim(pl, name, OW, OD, z0, H, lift=lift, lod=lod, mat_tile=fix)
        objs += [a, b]
    objs.append(ridge_ring(pl, name, IW, ID, z0, H, lift=lift, mat=fix_dark))
    objs.append(ridge_xie(pl, name, OW, OD, IW, ID, z0, H, lift=lift, mat=fix_dark))
    return [o for o in objs if o]


# ------------------------------------------------------------------ 自测
if __name__ == "__main__":
    HERE = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, HERE)
    import precise_lib as PL

    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = os.environ.get("TEMP", HERE)
    for i, a in enumerate(argv):
        if a == "--out":
            out = argv[i + 1]
    os.makedirs(out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    col = sc.collection
    PL.set_collection(col)
    PL.make_materials()

    # 一单体量（只为看屋顶）
    PL.box("身", 70, 36, 14, 0, 0, 0, PL.MAT["wall"])
    roof(PL, "顶", 86, 52, 16.5, 15.0, lift=1.5, lod=2)

    cam_d = bpy.data.cameras.new("C")
    cam_d.clip_end = 6000
    cam = bpy.data.objects.new("C", cam_d)
    col.objects.link(cam)
    sc.camera = cam
    from mathutils import Vector
    sun_d = bpy.data.lights.new("S", type="SUN")
    sun_d.energy = 3.6
    sun_d.angle = math.radians(2.5)
    sun = bpy.data.objects.new("S", sun_d)
    col.objects.link(sun)
    sun.rotation_euler = (math.radians(38), 0, math.radians(225))
    sc.world = bpy.data.worlds.new("W")
    sc.world.use_nodes = True
    sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.68, 0.88, 1)
    sc.world.node_tree.nodes["Background"].inputs[1].default_value = 0.45
    sc.render.engine = "CYCLES"
    sc.cycles.device = "GPU"
    sc.cycles.samples = 48
    sc.cycles.use_denoising = True
    sc.view_settings.view_transform = "Standard"
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720

    def look(ob, t):
        d = Vector(t) - ob.location
        ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

    for nm, loc, tgt, lens in (("eave", (52, -46, 12), (10, -8, 18), 45),
                               ("top", (40, -52, 48), (0, 0, 26), 55),
                               ("corner", (66, -40, 20), (24, -14, 22), 60),
                               ("front", (0, -95, 22), (0, 0, 22), 60)):
        cam.location = loc
        cam_d.lens = lens
        look(cam, tgt)
        sc.render.filepath = os.path.join(out, f"roof_{nm}.png")
        bpy.ops.render.render(write_still=True)
        print("OK", nm)
    print("VERTS", sum(len(o.data.vertices) for o in col.objects if o.type == "MESH"))
