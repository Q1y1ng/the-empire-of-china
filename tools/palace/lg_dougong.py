# -*- coding: utf-8 -*-
"""清式单翘重昂七踩斗拱 —— 参数化构件（供 palace 精模替换旧方块斗拱）。

几何全部直接写进顶点（本地坐标），因此物体可以安全地 ``location + rotation_euler``
摆到墙上，不会像 ``precise_lib.box`` 那样让几何绕世界原点飞走。

坐标口径
--------
* 原点：坐斗（栌斗）底面中心
* +Y：墙外（垂直墙面方向）  -Y：墙里（里跳）
* +Z：向上                  X：沿墙面阔方向
* 所有几何先按「斗口」为单位建模，出网格时统一乘 ``unit``（米）

层高（斗口）
------------
坐斗 0~2.0；第 k 层（k=0..3）拱底 = 2.0 + 2.4k，拱高 1.4，升高 1.0；
挑檐枋 10.6~11.0，挑檐桁下皮 11.0 → 总高 11 斗口。
出跳：每拽架 3.0，七踩 = 3 拽架；挑檐桁中线 y = 9.0，耍头鼻尖 10.67。
"""

from __future__ import annotations

import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

__all__ = [
    "make_mesh",
    "place_ring",
    "ring_layout",
    "DOUGONG_DIMS",
]

# ---------------------------------------------------------------- 基本尺寸（斗口）
U_DEFAULT = 0.16

SLOT = 1.0          # 拱厚 / 斗口
GONG_H = 1.4        # 拱高
DOU_H = 2.0         # 坐斗高
SUP_H = 1.0         # 升高
LAYER = GONG_H + SUP_H          # 2.4，每层（拱+升）
N_JUMP = 3                       # 七踩 = 3 拽架
JUMP = 3.0                       # 每拽架出跳
Z0 = DOU_H                       # 第一层拱底 = 2.0
Z_TOP = Z0 + N_JUMP * LAYER      # 9.2 = 第四层（耍头层）拱底
Z_EAVE = Z_TOP + GONG_H + 0.4    # 11.0 = 挑檐桁下皮

GONG_LEN = {"gua": 6.2, "wan": 9.2, "xiang": 7.2}
DOU_S = 3.2                      # 坐斗 3.2×3.2×2.0
SUP_L, SUP_D, SUP_HH = 1.6, 1.4, 1.0   # 升 / 十八斗

DOUGONG_DIMS = {
    "unit": U_DEFAULT,
    "坐斗": (3.2, 3.2, 2.0),
    "拱厚": 1.0, "拱高": 1.4,
    "瓜拱": 6.2, "万拱": 9.2, "厢拱": 7.2,
    "升": (1.6, 1.4, 1.0),
    "拽架": JUMP, "踩数": 7, "拽架数": N_JUMP,
    "总高": Z_EAVE,               # 11.0 斗口
    "出挑": 9.0,                  # 挑檐桁中线
    "攒当": 11.0,
}

_MESH_CACHE = {}
_MAT_CACHE = {}


# ---------------------------------------------------------------- 材质
def _lib():
    """取同目录的 precise_lib（只读复用其材料表）。"""
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    import precise_lib  # noqa: E402  (bpy 内导入)

    return precise_lib


def _dark_mat():
    """昂嘴 / 耍头：比斗拱灰绿深一档的青黑。"""
    m = bpy.data.materials.get("斗拱·昂")
    if m:
        return m
    m = bpy.data.materials.new("斗拱·昂")
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    if b:
        b.inputs["Base Color"].default_value = (0.13, 0.17, 0.15, 1.0)
        b.inputs["Roughness"].default_value = 0.62
    return m


def _red_mat():
    """垫拱板：刷红（清式斗拱之间那道竖板，多为土朱红）。"""
    m = bpy.data.materials.get("斗拱·垫板")
    if m:
        return m
    m = bpy.data.materials.new("斗拱·垫板")
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    if b:
        # 土朱比柱红更暗一档：垫拱板面积大，刷得跟柱子一样亮，
        # 远看整条檐下就是"红砖墙 + 青绿小块"，拱反而退到后面去了
        b.inputs["Base Color"].default_value = (0.235, 0.038, 0.024, 1.0)
        b.inputs["Roughness"].default_value = 0.66
    return m


def _mats(main=None):
    pl = _lib()
    m = pl.make_materials()
    main = main or m["dou"]
    key = main.name
    if key in _MAT_CACHE:
        return _MAT_CACHE[key]
    out = [main, _dark_mat(), m["cai_blue"], m["cai_green"], _red_mat()]
    _MAT_CACHE[key] = out
    return out


# ---------------------------------------------------------------- 顶点缓冲
class _Buf:
    __slots__ = ("verts", "faces", "mats")

    def __init__(self):
        self.verts = []
        self.faces = []
        self.mats = []

    # ---- 盒子
    def box(self, x0, x1, y0, y1, z0, z1, m=0):
        if x1 <= x0 or y1 <= y0 or z1 <= z0:
            return
        b = len(self.verts)
        self.verts += [
            (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
            (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
        ]
        for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1),
                  (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
            self.faces.append(tuple(b + i for i in f))
            self.mats.append(m)

    # ---- 多环放样
    def loft(self, rings, m=0, cap_bottom=True, cap_top=True):
        n = len(rings[0])
        base = len(self.verts)
        for r in rings:
            self.verts.extend(r)
        for k in range(len(rings) - 1):
            a = base + k * n
            c = base + (k + 1) * n
            for i in range(n):
                j = (i + 1) % n
                self.faces.append((a + i, a + j, c + j, c + i))
                self.mats.append(m)
        if cap_bottom:
            self.faces.append(tuple(base + i for i in range(n)))
            self.mats.append(m)
        if cap_top:
            top = base + (len(rings) - 1) * n
            self.faces.append(tuple(top + i for i in range(n)))
            self.mats.append(m)

    # ---- 二维型材沿 X 挤出（昂 / 耍头）
    def profile_x(self, prof, x0, x1, m=0):
        n = len(prof)
        base = len(self.verts)
        for x in (x0, x1):
            for (y, z) in prof:
                self.verts.append((x, y, z))
        for i in range(n):
            j = (i + 1) % n
            self.faces.append((base + i, base + j, base + n + j, base + n + i))
            self.mats.append(m)
        poly = [Vector((y, z, 0.0)) for (y, z) in prof]
        for (i, j, k) in tessellate_polygon([poly]):
            self.faces.append((base + i, base + j, base + k))
            self.mats.append(m)
            self.faces.append((base + n + k, base + n + j, base + n + i))
            self.mats.append(m)

    # ---- 圆柱（沿 X）
    def cyl_x(self, x0, x1, y, zc, r, n, m=2):
        base = len(self.verts)
        for x in (x0, x1):
            for i in range(n):
                a = 2 * math.pi * i / n
                self.verts.append((x, y + r * math.cos(a), zc + r * math.sin(a)))
        for i in range(n):
            j = (i + 1) % n
            self.faces.append((base + i, base + j, base + n + j, base + n + i))
            self.mats.append(m)
        self.faces.append(tuple(base + i for i in range(n - 1, -1, -1)))
        self.mats.append(m)
        self.faces.append(tuple(base + n + i for i in range(n)))
        self.mats.append(m)


# ---------------------------------------------------------------- 构件
def _dou(b, w, d, h, z0, ears=0, lod=2, m=0):
    """斗：栌斗（ears=4）/ 十八斗（ears=4）/ 三才升（ears=2）。

    lod>=2 做斗欹（下收 1/5 的两段弧）与十字/顺身开口；
    ears=4 → 四角斗耳（十字口）；ears=2 → 两侧通长斗耳（顺身口）；
    ears=0 → 无耳。"""
    if lod <= 1 or ears <= 0:
        # lod 1 是「省掉斗欹」：直方块；升本就没有耳，也用方块收口
        if lod <= 1:
            b.box(-w / 2, w / 2, -d / 2, d / 2, z0, z0 + h, m)
            return
    # 斗欹：0 → 0.18h → 0.36h → 收口（有耳时 0.6h，无耳时全高）
    top = 0.6 if ears > 0 else 1.0
    rings = []
    for zf, s in ((0.0, 0.80), (0.18, 0.93), (0.36, 1.0), (top, 1.0)):
        z = z0 + zf * h
        hx, hy = w * s / 2, d * s / 2
        rings.append([(-hx, -hy, z), (hx, -hy, z), (hx, hy, z), (-hx, hy, z)])
    b.loft(rings, m)
    if ears <= 0:
        return
    zt = z0 + top * h
    e_slot = SLOT / 2
    if ears == 4:
        x1, y1 = w / 2, d / 2
        if x1 <= e_slot + 1e-4 or y1 <= e_slot + 1e-4:
            return
        for sx in (-1, 1):
            for sy in (-1, 1):
                bx0, bx1 = sorted((sx * e_slot, sx * x1))
                by0, by1 = sorted((sy * e_slot, sy * y1))
                b.box(bx0, bx1, by0, by1, zt, z0 + h, m)
    else:  # 2：两侧通长耳，留出顺身口
        x1 = w / 2
        if x1 <= e_slot + 1e-4:
            return
        for sx in (-1, 1):
            bx0, bx1 = sorted((sx * e_slot, sx * x1))
            b.box(bx0, bx1, -d / 2, d / 2, zt, z0 + h, m)


def _gong(b, length, y, z0, lod=2, m=0):
    """沿 X 的拱：厚 1.0、高 1.4，两端四瓣卷杀（平面收分 + 底边起翘）。"""
    if lod <= 1:
        b.box(-length / 2, length / 2, y - SLOT / 2, y + SLOT / 2, z0, z0 + GONG_H, m)
        return
    # 四瓣：距端头 d 处的宽度系数 / 底边抬升（卷杀只做端头一小段）
    ends = ((0.0, 0.72, 0.16), (0.18, 0.82, 0.09),
            (0.38, 0.92, 0.04), (0.62, 0.98, 0.01))
    prof = [(-length / 2 + d, ws, lift) for (d, ws, lift) in ends]
    prof.append((0.0, 1.0, 0.0))
    prof += [(length / 2 - d, ws, lift) for (d, ws, lift) in reversed(ends)]
    rings = []
    for (x, ws, lift) in prof:
        t = SLOT * ws / 2
        z = z0 + lift
        rings.append([(x, y - t, z), (x, y + t, z),
                      (x, y + t, z + GONG_H), (x, y - t, z + GONG_H)])
    b.loft(rings, m)


def _bar_y(b, y0, y1, z0, lod=2, m=0):
    """沿 Y 的翘（两端卷杀，同拱）。"""
    if lod <= 1:
        b.box(-SLOT / 2, SLOT / 2, y0, y1, z0, z0 + GONG_H, m)
        return
    ends = ((0.0, 0.72, 0.16), (0.18, 0.82, 0.09),
            (0.38, 0.92, 0.04), (0.62, 0.98, 0.01))
    prof = [(y0 + d, ws, lift) for (d, ws, lift) in ends]
    prof.append(((y0 + y1) / 2, 1.0, 0.0))
    prof += [(y1 - d, ws, lift) for (d, ws, lift) in reversed(ends)]
    rings = []
    for (y, ws, lift) in prof:
        t = SLOT * ws / 2
        z = z0 + lift
        rings.append([(-t, y, z), (t, y, z), (t, y, z + GONG_H), (-t, y, z + GONG_H)])
    b.loft(rings, m)


def _ang(b, y_root, y_head, z0, lod=2, m=1):
    """下昂：昂背平（承十八斗），昂嘴斜下、昂尖略上翘，昂嘴斜杀。

    y_head = 该昂头部十八斗的中心（也是下一跳的起点）。"""
    zb = z0
    zt = z0 + GONG_H
    yh = y_head
    if lod == 0:
        b.box(-SLOT / 2, SLOT / 2, y_root, yh + 1.3, zb, zt, m)
        return
    if lod == 1:
        prof = [
            (y_root, zb), (y_root, zt), (yh + 0.65, zt), (yh + 1.25, zt - 0.45),
            (yh + 1.0, zb - 0.55), (yh + 0.45, zb - 0.55),
            (yh - 2.6, zb + 0.02),
        ]
        b.profile_x(prof, -SLOT / 2, SLOT / 2, m)
        return
    # lod 2：昂背从 y_root 一直平到 yh+0.75（十八斗压在上面），
    # 之后卷起昂尖、斜杀前沿、掏空昂嘴下缘。
    prof = [
        (y_root, zb),
        (y_root, zt),
        (yh + 0.66, zt),
        (yh + 1.00, zt + 0.10),
        (yh + 1.34, zt + 0.28),        # 昂尖明显上翘
        (yh + 1.56, zt + 0.10),        # 尖
        (yh + 1.50, zb + 0.22),        # 斜杀前沿
        (yh + 1.10, zb - 0.72),
        (yh + 0.86, zb - 1.00),        # 昂嘴下尖
        (yh + 0.30, zb - 1.06),        # 嘴喉（最低）
        (yh - 0.30, zb - 0.76),
        (yh - 1.05, zb - 0.40),
        (yh - 1.60, zb - 0.18),
        (y_root, zb),
    ]
    b.profile_x(prof, -SLOT / 2, SLOT / 2, m)
    # 琴面昂：背上一条窄脊，增加高光层次
    b.box(-0.16, 0.16, y_root + 0.2, yh + 0.45, zt, zt + 0.10, m)


def _shuatou(b, y_root, y_head, z0, lod=2, m=1):
    """耍头：蚂蚱头形（额头圆、嘴下有缺口）。"""
    zb, zt = z0, z0 + GONG_H
    if lod == 0:
        b.box(-SLOT / 2, SLOT / 2, y_root, y_head + 0.6, zb, zt, m)
        return
    if lod == 1:
        prof = [
            (y_root, zb), (y_root, zt), (y_head - 0.2, zt),
            (y_head + 0.25, zt - 0.45), (y_head - 0.05, zb + 0.05),
            (y_root, zb),
        ]
        b.profile_x(prof, -SLOT / 2, SLOT / 2, m)
        return
    prof = [
        (y_root, zb),
        (y_root, zt),
        (y_head, zt),
        (y_head + 0.22, zt - 0.10),    # 额头
        (y_head + 0.48, zt - 0.42),
        (y_head + 0.72, zt - 0.70),    # 鼻尖
        (y_head + 0.60, zt - 1.00),    # 嘴
        (y_head + 0.25, zt - 1.08),    # 缺口内
        (y_head + 0.25, zt - 1.30),
        (y_head - 0.10, zt - 1.44),    # 下颏
        (y_head - 0.90, zt - 1.52),
        (y_root, zb),
    ]
    b.profile_x(prof, -SLOT / 2, SLOT / 2, m)


def _bank(b, y, z0, z1, seg_x0, seg_x1, m=4):
    """垫拱板：填在相邻拱之间的竖板，正面比拱身前脸退 0.2 斗口。

    没有它，檐下一眼能透过攒与攒之间的缝看到天，整排斗拱就读成「一排散块」；
    有了它才是连续的一道板带，斗与拱从板前凸出，明暗层次立刻出来。"""
    # 两端各收 0.10 斗口：转角处两向的垫板本来正交穿插，收一档就不打架
    b.box(seg_x0 + 0.10, seg_x1 - 0.10, y - 0.55, y + 0.30, z0, z1, m)


def _sup(b, x, y, z0, lod, m=3, ears=2):
    """斗：清式斗拱里「斗」刷青、「拱」刷绿，同色就全糊成一格一格的瓷砖。"""
    _dou(b, SUP_L, SUP_D, SUP_HH, z0, ears=ears if lod >= 2 else 0, lod=lod, m=m)


def _sup_lo(b, x, y, z0, lod, m=3):
    """lod0 极简档不摆三才升（远看只是碎块，省面数）。"""
    if lod >= 1:
        _sup(b, x, y, z0, lod, m=m)


# ---------------------------------------------------------------- 组一攒
def _build(b, lod, seg):
    """全部尺寸以斗口为单位；seg = 桁/枋每段的长度（斗口）。"""
    n_cyl = 12 if lod >= 2 else (8 if lod == 1 else 6)
    seg_x0, seg_x1 = -seg / 2, seg / 2

    # 1) 栌斗
    if lod >= 1:
        _dou(b, DOU_S, DOU_S, DOU_H, 0.0, ears=4 if lod >= 2 else 0, lod=lod, m=3)
    else:
        b.box(-DOU_S / 2, DOU_S / 2, -DOU_S / 2, DOU_S / 2, 0.0, DOU_H, 3)

    # 2) 第一层：正心瓜拱 + 头翘（十字相交于栌斗口内）
    _gong(b, GONG_LEN["gua"], 0.0, Z0, lod)
    _bar_y(b, -3.6, 3.6, Z0, lod)

    # 3) 正心列：瓜拱→升→万拱→升→厢拱→升→正心枋→正心桁
    _sup_lo(b, 2.3, 0.0, Z0 + GONG_H, lod)
    _sup_lo(b, -2.3, 0.0, Z0 + GONG_H, lod)
    _gong(b, GONG_LEN["wan"], 0.0, Z0 + LAYER, lod)
    _sup_lo(b, 3.8, 0.0, Z0 + LAYER + GONG_H, lod)
    _sup_lo(b, -3.8, 0.0, Z0 + LAYER + GONG_H, lod)
    if lod >= 1:
        _gong(b, GONG_LEN["xiang"], 0.0, Z0 + 2 * LAYER, lod)
    _sup_lo(b, 2.8, 0.0, Z0 + 2 * LAYER + GONG_H, lod)
    _sup_lo(b, -2.8, 0.0, Z0 + 2 * LAYER + GONG_H, lod)
    # 正心枋（坐在厢拱两端的升上，上面压正心桁）
    b.box(seg_x0, seg_x1, -SLOT / 2, SLOT / 2, 9.2, 11.2, 0)
    b.cyl_x(seg_x0, seg_x1, 0.0, 12.7, 1.5, n_cyl, 2)

    # 4) 外跳三条拽架：y=3 / 6 / 9
    # y=3：外拽瓜拱(层1)→万拱(层2)→厢拱(层3)
    _gong(b, GONG_LEN["gua"], 3.0, Z0 + LAYER, lod)
    _sup_lo(b, 2.3, 3.0, Z0 + LAYER + GONG_H, lod)
    _sup_lo(b, -2.3, 3.0, Z0 + LAYER + GONG_H, lod)
    _gong(b, GONG_LEN["wan"], 3.0, Z0 + 2 * LAYER, lod)
    _sup_lo(b, 3.8, 3.0, Z0 + 2 * LAYER + GONG_H, lod)
    _sup_lo(b, -3.8, 3.0, Z0 + 2 * LAYER + GONG_H, lod)
    if lod >= 1:
        _gong(b, GONG_LEN["xiang"], 3.0, Z_TOP, lod)
    # y=6：外拽瓜拱(层2)→万拱(层3)
    _gong(b, GONG_LEN["gua"], 6.0, Z0 + 2 * LAYER, lod)
    _sup_lo(b, 2.3, 6.0, Z0 + 2 * LAYER + GONG_H, lod)
    _sup_lo(b, -2.3, 6.0, Z0 + 2 * LAYER + GONG_H, lod)
    _gong(b, GONG_LEN["wan"], 6.0, Z_TOP, lod)
    # y=9：厢拱(层4)
    _gong(b, GONG_LEN["xiang"], 9.0, Z_TOP, lod)

    # 5) 里跳（只做一拽架，藏在墙里，保证从内侧看不是空的）
    if lod >= 1:
        _gong(b, GONG_LEN["gua"], -3.0, Z0 + LAYER, lod)
        _sup_lo(b, 2.3, -3.0, Z0 + LAYER + GONG_H, lod)
        _sup_lo(b, -2.3, -3.0, Z0 + LAYER + GONG_H, lod)
        _gong(b, GONG_LEN["wan"], -3.0, Z0 + 2 * LAYER, lod)

    # 5b) 垫拱板：把拱与拱之间补成连续板带（否则檐下透空，整排读成散块）
    _bank(b, 0.0, Z0, 9.2, seg_x0, seg_x1)
    _bank(b, 3.0, Z0 + LAYER, 10.6, seg_x0, seg_x1)
    _bank(b, 6.0, Z0 + 2 * LAYER, 10.6, seg_x0, seg_x1)
    if lod >= 1:
        _bank(b, 9.0, Z_TOP, 10.6, seg_x0, seg_x1)
        _bank(b, -3.0, Z0 + LAYER, Z0 + 2 * LAYER + GONG_H, seg_x0, seg_x1)

    # 6) 十八斗（出跳构件下的斗）
    _sup(b, 0.0, 3.0, Z0 + GONG_H, lod, ears=4)
    _sup(b, 0.0, -3.0, Z0 + GONG_H, lod, ears=4)
    _sup(b, 0.0, 6.0, Z0 + LAYER + GONG_H, lod, ears=4)
    _sup(b, 0.0, 9.0, Z0 + 2 * LAYER + GONG_H, lod, ears=4)

    # 7) 出跳构件：头翘→头昂→二昂→耍头
    _ang(b, 0.6, 6.0, Z0 + LAYER, lod, m=1)
    _ang(b, 3.6, 9.0, Z0 + 2 * LAYER, lod, m=1)
    _shuatou(b, 6.6, 9.95, Z_TOP, lod, m=1)

    # 8) 挑檐枋 + 挑檐桁（最外端，桁中线正好 9 斗口）
    b.box(seg_x0, seg_x1, 8.40, 9.60, 10.6, 11.0, 3)
    b.cyl_x(seg_x0, seg_x1, 9.00, 12.5, 1.5, n_cyl, 2)


def make_mesh(unit=0.16, lod=2, seg=11.0, mat=None):
    """返回一攒清式单翘重昂七踩斗拱的 Mesh（本地坐标，米）。

    unit : 斗口（材宽），米
    lod  : 2 细（斗欹、十字口、四瓣卷杀、昂嘴、琴面、蚂蚱头）
           1 中（省斗欹/卷杀，保留昂嘴与耍头轮廓）
           0 极简（体块，远距离整宫用）
    seg  : 该攒分摊到的攒当（斗口数），决定正心桁/挑檐桁/枋的分段长度。
           单攒自测可不管；place_ring 会按实际中距传入。
    mat  : 主材（斗/拱）覆盖，默认 precise_lib.MAT["dou"]。
    """
    unit = float(unit)
    lod = int(lod)
    key = (round(unit, 6), lod, round(float(seg), 4), mat.name if mat else None)
    if key in _MESH_CACHE:
        me = _MESH_CACHE[key]
        try:
            if me.name and bpy.data.meshes.get(me.name) is me:
                return me
        except ReferenceError:      # 场景被重置后旧 mesh 已失效，重建
            pass
        _MESH_CACHE.pop(key, None)

    mats = _mats(mat)
    b = _Buf()
    seg_len = max(2.0, float(seg) - 0.01 / unit)  # 两端各留 5mm 缝，避免共面闪烁
    _build(b, lod, seg_len)

    me = bpy.data.meshes.new("清式斗拱·七踩·L%d" % lod)
    me.from_pydata([(x * unit, y * unit, z * unit) for (x, y, z) in b.verts], [], b.faces)
    for i, p in enumerate(me.polygons):
        if i < len(b.mats):
            p.material_index = b.mats[i]
    for m in mats:
        me.materials.append(m)
    me.validate(verbose=False)

    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()

    # 圆桁侧面平滑（cai_blue 且法线不是 ±X 的端盖）
    for p in me.polygons:
        if p.material_index == 2 and abs(p.normal.x) < 0.9:
            p.use_smooth = True

    _MESH_CACHE[key] = me
    return me


# ---------------------------------------------------------------- 布环
def ring_layout(w, d, spacing):
    """返回 [(x, y, rot_z, 本侧实际中距, side_idx)]。

    每侧用 ceil 保证实际中距 ≤ spacing；四角各留半档，不设角科，
    所以第一/最后一攒的拱头离角只有约 0.4 m，桁则正好在角上相接。
    """
    out = []
    n = max(1, int(math.ceil(w / spacing - 1e-9)))
    sp = w / n
    for i in range(n):
        x = -w / 2 + (i + 0.5) * sp
        out.append((x, -d / 2, math.pi, sp, 0))       # 南：+Y(本) → -Y(世)
        out.append((x, d / 2, 0.0, sp, 0))            # 北
    n = max(1, int(math.ceil(d / spacing - 1e-9)))
    sp = d / n
    for j in range(n):
        y = -d / 2 + (j + 0.5) * sp
        out.append((-w / 2, y, math.pi / 2, sp, 1))   # 西：+Y(本) → -X(世)
        out.append((w / 2, y, -math.pi / 2, sp, 1))   # 东
    return out


def place_ring(pl, w, d, z, unit=0.16, spacing=None, lod=2, mat=None):
    """沿 w×d 矩形四周布一圈斗拱，z = 坐斗底面高度。

    每攒本地 +Y 指向墙外；中距按侧取整，相邻攒不穿插（桁/枋每段比中距短 1 cm）。
    返回 (对象数, 三角面数)。
    """
    spacing = float(spacing) if spacing else 11.0 * unit
    slots = ring_layout(w, d, spacing)
    col = getattr(pl, "COL", None) or bpy.context.scene.collection
    meshes = {}
    nobj = 0
    tris = 0
    for idx, (x, y, rot, sp, _side) in enumerate(slots):
        me = meshes.get(round(sp, 6))
        if me is None:
            me = make_mesh(unit, lod, seg=sp / unit, mat=mat)
            me.calc_loop_triangles()
            meshes[round(sp, 6)] = me
        ob = bpy.data.objects.new("斗拱%03d" % idx, me)
        ob.location = (x, y, z)
        ob.rotation_euler = (0.0, 0.0, rot)
        col.objects.link(ob)
        nobj += 1
        tris += len(me.loop_triangles)
    return nobj, tris


# ---------------------------------------------------------------- 自测
def _selftest():
    print("=== 清式单翘重昂七踩斗拱 ===")
    for k, v in DOUGONG_DIMS.items():
        print("  %-6s %s" % (k, v))
    for lod in (0, 1, 2):
        me = make_mesh(0.16, lod)
        me.calc_loop_triangles()
        print("  lod=%d : %5d verts  %5d faces  %5d tris"
              % (lod, len(me.vertices), len(me.polygons), len(me.loop_triangles)))
    n = len(ring_layout(90.0, 50.0, 1.76))
    print("  90x50 一圈: %d 攒" % n)


if __name__ == "__main__":
    _selftest()
