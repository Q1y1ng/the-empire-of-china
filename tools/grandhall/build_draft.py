"""万人大礼堂 —— 2D 草稿：平面、纵剖面、横剖面、座席对账。

    "$TEMP/plaza-build/Scripts/python.exe" build_draft.py --dpi 300
    "$TEMP/plaza-build/Scripts/python.exe" build_draft.py --dpi 110 --out "$TEMP/out"

产物：<out>/国家广场(2026)·万人大礼堂·草稿.png / .svg
"""

from __future__ import annotations

import argparse
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.patches import Circle, Polygon, Rectangle, Wedge

import hall_data as D

HERE = os.path.dirname(os.path.abspath(__file__))

C = {
    "paper": "#F6F4EF",
    "ink": "#232220",
    "muted": "#6E6A61",
    "grid": "#D9D4C8",
    "wall": "#3B382F",
    "hallfill": "#F2EEE3",
    "foyerfill": "#F3EFE5",
    "stagefill": "#E6DCC6",
    "pit": "#C7A468",
    "bal1": "#DEC49B",
    "bal2": "#E7D9BC",
    "side": "#ECE6D8",
    "red": "#A8322A",
    "gold": "#B08A22",
    "blue": "#3D5A73",
}

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
FX, FY = D.FOCUS["x"], D.FOCUS["y"]


# ------------------------------------------------------------------ 小工具
def txt(ax, x, y, s, fs=7.0, color=None, ha="left", va="center", rot=0, weight="normal"):
    ax.text(x, y, s, fontsize=fs, color=color or C["ink"], ha=ha, va=va,
            rotation=rot, zorder=14, fontweight=weight)


def dim_h(ax, x0, x1, y, label, color=None, fs=6.6, tick=2.0):
    col = color or C["muted"]
    ax.annotate("", (x1, y), (x0, y),
                arrowprops=dict(arrowstyle="<|-|>", color=col, lw=0.7,
                                shrinkA=0, shrinkB=0), zorder=11)
    for x in (x0, x1):
        ax.plot([x, x], [y - tick, y + tick], color=col, lw=0.6, zorder=11)
    txt(ax, (x0 + x1) / 2, y + 1.5, label, fs=fs, color=col, ha="center", va="bottom")


def dim_v(ax, y0, y1, x, label, color=None, fs=6.6, tick=2.0, side="right"):
    col = color or C["muted"]
    ax.annotate("", (x, y1), (x, y0),
                arrowprops=dict(arrowstyle="<|-|>", color=col, lw=0.7,
                                shrinkA=0, shrinkB=0), zorder=11)
    for y in (y0, y1):
        ax.plot([x - tick, x + tick], [y, y], color=col, lw=0.6, zorder=11)
    txt(ax, x + (1.5 if side == "right" else -1.5), (y0 + y1) / 2, label, fs=fs,
        color=col, ha="left" if side == "right" else "right", va="center", rot=90)


def clean(ax, keep_frame=False):
    for s in ax.spines.values():
        s.set_visible(keep_frame)
        s.set_color(C["grid"])
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_facecolor("none")


def front_curve(tier, r_min):
    """U 形挑台前缘：r = r0 − wrap·(θ/θref)²，取落在厅内且不成负的一段。"""
    r0 = tier["r0"]
    wrap = tier.get("wrap", 0.0)
    tref = tier.get("theta_ref", 0.5)
    pts = []
    n = 160
    for i in range(n + 1):
        th = -1.0 + 2.0 * i / n
        r = r0 - wrap * (th / tref) ** 2
        if r < r_min:
            continue
        if abs(th) > D.wall_half_angle(r):
            continue
        pts.append((FX + r * math.cos(th), FY + r * math.sin(th)))
    return pts


# ------------------------------------------------------------------ 平面
def draw_plan(ax):
    x0, x1 = D.BUILD["x0"], D.BUILD["x1"]
    y0, y1 = D.BUILD["y0"], D.BUILD["y1"]
    ax.set_xlim(-566, -286)
    ax.set_ylim(-1190, -888)
    ax.set_aspect("equal")
    clean(ax)

    # 中厅体块
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor="#FBFAF6",
                           edgecolor=C["grid"], lw=1.0, ls=(0, (7, 5)), zorder=1))
    txt(ax, x0 + 3, y1 - 5, "中厅 230 × 240 m", fs=7.2, color=C["muted"], va="top")

    # 观众厅两侧（侧厅／休息厅／楼梯）：先铺满整块，再由观众厅覆盖
    ax.add_patch(Rectangle((x0, y0), (-389) - x0, y1 - y0, facecolor=C["side"],
                           edgecolor=C["grid"], lw=0.5, hatch="////", alpha=0.55,
                           zorder=2))
    for sx in (-470, -430):
        for sy in (y1 - 30, y0 + 30):
            ax.add_patch(Rectangle((sx - 6, sy - 3), 12, 6, facecolor=C["paper"],
                                   edgecolor=C["grid"], lw=0.5, zorder=2.4))
    txt(ax, -462, y1 - 8, "侧厅 · 休息厅 · 楼梯", fs=6.4, color=C["muted"], va="top")
    txt(ax, -462, y0 + 10, "侧厅 · 休息厅 · 楼梯", fs=6.4, color=C["muted"], va="bottom")

    # 中央前厅
    F = D.FOYER
    ax.add_patch(Rectangle((F["x0"], F["y0"]), F["x1"] - F["x0"], F["y1"] - F["y0"],
                           facecolor=C["foyerfill"], edgecolor=C["grid"], lw=0.7,
                           zorder=2))
    for gx in range(-378, -312, 12):
        ax.plot([gx, gx], [F["y0"] + 2, F["y1"] - 2], color=C["grid"], lw=0.3,
                ls=(0, (4, 4)), zorder=2)
    for gy in range(-1146, -920, 12):
        ax.plot([F["x0"] + 2, F["x1"] - 2], [gy, gy], color=C["grid"], lw=0.3,
                ls=(0, (4, 4)), zorder=2)
    for (cx, cy) in D.foyer_columns():
        ax.add_patch(Circle((cx, cy), 2.4, facecolor="white", edgecolor=C["muted"],
                            lw=0.55, zorder=7))
    txt(ax, (F["x0"] + F["x1"]) / 2, F["y1"] - 16, "中央前厅", fs=9.2, ha="center",
        va="top", weight="bold")
    txt(ax, (F["x0"] + F["x1"]) / 2, F["y1"] - 25,
        "20 根汉白玉明柱", fs=6.2, ha="center", va="top", color=C["muted"])
    txt(ax, (F["x0"] + F["x1"]) / 2, F["y0"] + 14,
        "桃红大理石 · 井字梁 · 5 组水晶吊灯", fs=6.2, ha="center", va="bottom",
        color=C["muted"])

    # 后台
    B = D.ZONES["backstage"]
    ax.add_patch(Rectangle((B["x0"], D.AXIS_Y - 30), B["x1"] - B["x0"], 60,
                           facecolor="#EFEBE2", edgecolor=C["grid"], lw=0.6, zorder=2.6))
    txt(ax, (B["x0"] + B["x1"]) / 2, D.AXIS_Y, "后台", fs=8.0, ha="center", rot=90)

    # 观众厅
    ax.add_patch(Polygon(D.hall_plan(), closed=True, facecolor=C["hallfill"],
                         edgecolor=C["wall"], lw=1.5, zorder=3))

    # 座席：自高层向低层叠印，池座最后压在最上（低层压高层）
    for z, t in ((0.0, D.TIERS[2]), (0.1, D.TIERS[1]), (0.2, D.TIERS[0])):
        col = C[t["key"]]
        for row in D.tier_rows(t):
            r = row["r"]
            for (a0, a1, _n) in row["blocks"]:
                ax.add_patch(Wedge((FX, FY), r + 0.78, math.degrees(a0),
                                   math.degrees(a1), width=0.78, facecolor=col,
                                   edgecolor="none", lw=0, zorder=4 + z))

    # 挑台前缘（U 形）
    for t in (D.TIERS[1], D.TIERS[2]):
        rows = D.tier_rows(t)
        pts = front_curve(t, rows[0]["r"] - 0.5)
        if pts:
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color=C["wall"], lw=2.4,
                    zorder=8, solid_capstyle="round")

    # 座席区后缘与后厅
    st = D.seat_stats()
    txt(ax, -399, D.AXIS_Y - 34, "后厅", fs=7.4, ha="center", color=C["muted"],
        weight="bold")
    txt(ax, -399, D.AXIS_Y - 41, "（三级错台）", fs=5.8, ha="center", color=C["muted"])

    # 分层引线标注（文字落在后厅空白处，引线指进各层）
    for t, ty in ((D.TIERS[0], -1016.0), (D.TIERS[1], -1003.0), (D.TIERS[2], -990.0)):
        rows = D.tier_rows(t)
        row = rows[len(rows) // 2]
        th = 0.45
        ax.annotate(f'{t["name"]} {st[t["key"]]["seats"]:,} 席',
                    xy=(FX + row["r"] * math.cos(th), FY + row["r"] * math.sin(th)),
                    xytext=(-414, ty), fontsize=6.6, color=C["ink"], ha="left",
                    va="center", zorder=15,
                    arrowprops=dict(arrowstyle="-", color=C["muted"], lw=0.55,
                                    shrinkA=1, shrinkB=3))

    # 主席台
    S = D.STAGE
    ax.add_patch(Rectangle((S["x0"], D.AXIS_Y - S["half_w"]), S["x1"] - S["x0"],
                           2 * S["half_w"], facecolor=C["stagefill"],
                           edgecolor=C["wall"], lw=1.1, zorder=6))
    txt(ax, (S["x0"] + S["x1"]) / 2 - 1, D.AXIS_Y, "主席台", fs=8.4, ha="center",
        weight="bold", rot=90)
    txt(ax, (S["x0"] + S["x1"]) / 2, D.AXIS_Y - 27, "44 × 28 m，台面 +1.5 m", fs=6.0,
        ha="center", color=C["muted"])

    # 台口
    pw = D.PROSCENIUM["w"] / 2
    px = D.PROSCENIUM["x"]
    for ya, yb in ((D.AXIS_Y + pw, D.AXIS_Y + 22.0), (D.AXIS_Y - 22.0, D.AXIS_Y - pw)):
        ax.plot([px, px], [ya, yb], color=C["wall"], lw=4.0, solid_capstyle="butt",
                zorder=9)
    ax.plot([px, px], [D.AXIS_Y - pw, D.AXIS_Y + pw], color=C["gold"], lw=1.2,
            ls=(0, (3, 2)), zorder=9)

    # 铜门
    for (dx, dy, w, _h) in D.DOORS["hall"]:
        ax.plot([dx, dx], [dy - w / 2, dy + w / 2], color=C["red"], lw=3.0,
                solid_capstyle="butt", zorder=10)
    for (dx, dy, w, _h) in D.DOORS["foyer"]:
        ax.plot([dx, dx], [dy - w / 2, dy + w / 2], color=C["red"], lw=3.0,
                solid_capstyle="butt", zorder=10)

    # 文字
    txt(ax, -322, D.AXIS_Y - 30, "五樘铜门", fs=6.2, ha="center", rot=90,
        color=C["red"])

    # 尺寸
    ax.annotate("台口 40 m 宽 × 22 m 高\n无立柱开敞",
                xy=(px, D.AXIS_Y + 20.0), xytext=(-512, -962),
                fontsize=6.3, color=C["red"], ha="left", va="center", zorder=15,
                arrowprops=dict(arrowstyle="-", color=C["red"], lw=0.6,
                                shrinkA=2, shrinkB=3))
    dw = D.HALL["w_rear"] / 2
    dim_v(ax, D.AXIS_Y - dw, D.AXIS_Y + dw, -384,
          f'后墙 {D.HALL["w_rear"]:.0f} m', color=C["blue"], fs=6.4)
    dim_h(ax, px, D.HALL["x_rear"], -1166, "观众厅进深 95 m", color=C["blue"], fs=6.4)
    dim_h(ax, x0, x1, -1182, "230 m")
    dim_v(ax, y0, y1, -548, "240 m")

    # 比例尺 / 指北
    sx, sy = -348, -1172
    for i in range(4):
        ax.add_patch(Rectangle((sx + i * 12.5, sy), 12.5, 2.4,
                               facecolor=C["ink"] if i % 2 == 0 else "white",
                               edgecolor=C["ink"], lw=0.4, zorder=9))
    txt(ax, sx, sy - 4.0, "0", fs=5.6, ha="center", va="top")
    txt(ax, sx + 50, sy - 4.0, "50 m", fs=5.6, ha="center", va="top")
    ax.annotate("N", (-296, -1160), (-296, -1146),
                arrowprops=dict(arrowstyle="-|>", color=C["ink"], lw=0.9),
                fontsize=8.5, ha="center", va="bottom", fontweight="bold")

    # 剖切符号
    ax.plot([px + 5, D.HALL["x_rear"] + 8], [D.AXIS_Y, D.AXIS_Y], color=C["red"],
            lw=0.8, ls=(0, (11, 3, 2, 3)), zorder=12)
    ax.plot([-440, -440], [y0 + 6, y1 - 6], color=C["red"], lw=0.8,
            ls=(0, (11, 3, 2, 3)), zorder=12)
    txt(ax, px + 6, D.AXIS_Y - 6, "A", fs=9, color=C["red"], weight="bold")
    txt(ax, -433, -911, "B", fs=9, color=C["red"], weight="bold")

    txt(ax, -292, -896, "① 平面（1:1000）", fs=10.5, ha="right", va="top",
        weight="bold")


# ------------------------------------------------------------------ 纵剖面
def draw_long(ax):
    ax.set_xlim(-548, -302)
    ax.set_ylim(-4.0, 46)
    ax.set_aspect("equal")
    clean(ax)
    y = D.AXIS_Y
    xr = D.HALL["x_rear"]

    ax.plot([-548, -302], [0, 0], color=C["wall"], lw=1.6, zorder=5)
    ax.plot([-548, -302], [-2.8, -2.8], color=C["grid"], lw=0.6, zorder=2)

    def surface(tier):
        x0 = FX + tier["r0"]
        pts = [(x0, tier["z0"])]
        rows = D.tier_rows(tier)
        for row in rows:
            pts.append((FX + row["r"], row["z"]))
        pts.append((xr, rows[-1]["z"]))
        return pts

    # 池座
    pts = surface(D.TIERS[0])
    ax.fill_between([p[0] for p in pts], [p[1] for p in pts], -2.8, color=C["pit"],
                    alpha=0.35, zorder=3)
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color=C["wall"], lw=1.4, zorder=7)

    # 二层 / 三层挑台
    for t, nm in ((D.TIERS[1], "二层挑台"), (D.TIERS[2], "三层挑台")):
        pts = surface(t)
        xf = FX + t["r0"]
        # 楼板：前缘厚 1.8 m，向后收薄到 0.9 m（挑臂受力）
        ax.add_patch(Polygon([(xf, t["z0"]), (xf, t["z0"] - 1.8),
                              (xr, t["z0"] - 0.9), (xr, t["z0"])], closed=True,
                             facecolor=C["bal1"], edgecolor=C["wall"], lw=0.8,
                             zorder=6))
        # 前缘板（栏板）
        ax.add_patch(Rectangle((xf - 0.8, t["z0"] - 1.8), 1.6,
                               t["z0"] + 0.9 - (t["z0"] - 1.8), facecolor=C["bal1"],
                               edgecolor=C["wall"], lw=0.8, zorder=7))
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color=C["wall"], lw=1.3,
                zorder=7)
        ax.plot([xf - 0.8, xr], [t["z0"] + 0.9] * 2, color=C["wall"], lw=0.7,
                ls=(0, (4, 3)), zorder=6.5)
        txt(ax, xf + 6, t["z0"] + 3.4, f'{nm} +{t["z0"]:.1f} m', fs=6.4,
            color=C["muted"])

    # 主席台
    S = D.STAGE
    ax.add_patch(Rectangle((S["x0"], S["z"] - 1.2), S["x1"] - S["x0"], 1.2,
                           facecolor=C["stagefill"], edgecolor=C["wall"], lw=0.8,
                           zorder=6))
    txt(ax, (S["x0"] + S["x1"]) / 2, S["z"] + 1.8, "主席台 44 × 28 m", fs=6.4,
        ha="center", color=C["muted"])

    # 台口墙
    px = D.PROSCENIUM["x"]
    ax.add_patch(Rectangle((px - 1.7, 0), 3.4, D.PROSCENIUM["h"],
                           facecolor="#E9E2D2", edgecolor=C["wall"], lw=0.9, zorder=8))
    ax.plot([px - 1.7, px + 1.7], [D.PROSCENIUM["h"]] * 2, color=C["gold"], lw=1.8,
            zorder=9)

    # 穹顶
    xs, zs = [], []
    for i in range(241):
        x = D.HALL["x_front"] + (xr - D.HALL["x_front"]) * i / 240.0
        xs.append(x)
        zs.append(D.dome_height(x, y))
    ax.plot(xs, zs, color=C["wall"], lw=1.7, zorder=10)
    ax.fill_between(xs, zs, 46, color="#E7E0CF", alpha=0.85, zorder=2)

    c = D.hall_centroid()
    for rho in (0.86, 0.62, 0.40):
        for xx in (c[0] + rho * (xr - c[0]), c[0] + rho * (D.HALL["x_front"] - c[0])):
            zz = D.dome_height(xx, y)
            ax.plot([xx, xx], [zz - 0.5, zz + 1.1], color=C["gold"], lw=1.7, zorder=11)
    xr40 = c[0] + 0.40 * (xr - c[0])
    txt(ax, xr40 + 2, D.dome_height(xr40, y) - 3.0, "三环水波灯槽", fs=5.4,
        color=C["gold"])
    zc = D.dome_height(c[0], y)
    ax.plot([c[0] - 7.0, c[0] + 7.0], [zc - 0.3] * 2, color=C["red"], lw=2.6, zorder=11)
    txt(ax, c[0] - 8, zc - 2.4, "中央圆盘 · 国徽金龙 · 镏金 72 道光芒", fs=5.4,
        ha="right", color=C["red"])

    # 后厅
    txt(ax, (FX + 88 + xr) / 2, 5.2, "后厅", fs=6.6, ha="center", color=C["muted"])

    # 中央前厅
    F = D.FOYER
    ax.add_patch(Rectangle((F["x0"], 0), F["x1"] - F["x0"], F["beam_z"],
                           facecolor="none", edgecolor=C["wall"], lw=0.9, zorder=8))
    for i in range(7):
        bx = F["x0"] + (F["x1"] - F["x0"]) * (i + 0.5) / 7.0
        ax.plot([bx, bx], [F["beam_z"], F["h"]], color=C["grid"], lw=2.8, zorder=4)
    txt(ax, (F["x0"] + F["x1"]) / 2, 14.0, "中央前厅", fs=8.0, ha="center",
        weight="bold")
    txt(ax, (F["x0"] + F["x1"]) / 2, 10.6, "20 根明柱 · 井字梁 · 5 组水晶吊灯",
        fs=5.8, ha="center", color=C["muted"])
    ax.plot([F["x1"], F["x1"]], [0, 30.0], color=C["wall"], lw=2.4, zorder=8)

    # 后墙
    ax.plot([xr, xr], [0, D.HALL["z_spring"] + 2], color=C["wall"], lw=2.6, zorder=9)

    # 后台
    ax.add_patch(Rectangle((-540, 0), 28, 22.0, facecolor="#EFEBE2",
                           edgecolor=C["wall"], lw=0.9, zorder=3))
    txt(ax, -526, 11, "后台", fs=7.4, ha="center", rot=90, color=C["muted"])

    # 尺寸
    dim_v(ax, 0, D.HALL["z_apex"], -476, f'净高 {D.HALL["z_apex"]:.0f} m', color=C["red"],
          fs=6.0, tick=1.4)
    dim_v(ax, 0, D.PROSCENIUM["h"], -472, "台口 22 m", fs=6.0, tick=1.4)

    txt(ax, -302, 45.4, "② 纵剖面 A—A（沿中轴，1:1000）", fs=10.5, ha="right",
        va="top", weight="bold")


# ------------------------------------------------------------------ 横剖面
def draw_cross(ax, cut=-440.0):
    ax.set_xlim(-62, 62)
    ax.set_ylim(-4.0, 46)
    ax.set_aspect("equal")
    clean(ax)
    ax.axvline(0, color=C["grid"], lw=0.5, ls=(0, (6, 4)), zorder=1)

    t = (cut - D.HALL["x_front"]) / D.HALL["depth"]
    half = D.HALL["w_front"] / 2 + t * (D.HALL["w_rear"] - D.HALL["w_front"]) / 2

    ax.plot([-half, half], [0, 0], color=C["wall"], lw=1.6, zorder=5)
    for s in (1, -1):
        ax.plot([s * half, s * half], [0, D.HALL["z_spring"] + 2], color=C["wall"],
                lw=2.6, zorder=9)

    xs, zs = [], []
    for i in range(401):
        yy = -half + 2 * half * i / 400.0
        xs.append(yy)
        zs.append(D.dome_height(cut, D.AXIS_Y + yy))
    ax.plot(xs, zs, color=C["wall"], lw=1.7, zorder=10)
    ax.fill_between(xs, zs, 46, color="#E7E0CF", alpha=0.85, zorder=2)

    for ti in D.TIERS:
        pts = []
        for i in range(1201):
            yy = -half + 2 * half * i / 1200.0
            z = D.tier_z_at(ti, cut, D.AXIS_Y + yy)
            pts.append((yy, z))
        run = []
        for yy, z in pts + [(None, None)]:
            if z is None:
                if len(run) > 3:
                    ax.fill_between([p[0] for p in run], [p[1] for p in run],
                                    [p[1] - 1.1 for p in run], color=C[ti["key"]],
                                    alpha=0.95, zorder=6)
                    ax.plot([p[0] for p in run], [p[1] for p in run], color=C["wall"],
                            lw=1.3, zorder=7)
                run = []
            else:
                run.append((yy, z))

    # 挑台前缘竖板
    for ti in (D.TIERS[1], D.TIERS[2]):
        for s in (1, -1):
            best = None
            for i in range(1201):
                yy = s * (2 * half * i / 1200.0)
                if D.tier_z_at(ti, cut, D.AXIS_Y + yy) is not None:
                    best = yy
                    break
            if best is not None:
                ax.plot([best, best], [ti["z0"] - 1.9, ti["z0"] + 0.6], color=C["wall"],
                        lw=1.6, zorder=8)

    txt(ax, 0, 34.0, "中央圆盘 · 国徽金龙", fs=6.0, ha="center", color=C["red"])
    txt(ax, 6, 3.6, "池座", fs=6.6, color="#4A3F2C")
    txt(ax, 6, 12.6, "二层挑台", fs=6.6, color="#4A3F2C")
    for s in (1, -1):
        txt(ax, -s * 34.5, 21.4, "三层挑台\n侧翼", fs=6.0, ha="center", va="bottom",
            color="#4A3F2C", rot=0)
    dim_v(ax, 0, D.HALL["z_apex"], -half - 4, "40 m", color=C["red"], fs=6.0, tick=1.2)
    dim_h(ax, -half, half, -2.6, f"{2 * half:.1f} m", color=C["blue"], fs=6.0, tick=1.2)
    txt(ax, 0, -3.9,
        f'观众厅在此站位的净宽（台口 {D.HALL["w_front"]:.0f} m → 后墙 '
        f'{D.HALL["w_rear"]:.0f} m 线性展开）',
        fs=5.8, ha="center", color=C["muted"])

    txt(ax, -58, 45.4, "③ 横剖面 B—B（x = −440，1:900）", fs=10.0, va="top",
        weight="bold")


# ------------------------------------------------------------------ 文本面板
def draw_info(ax):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    clean(ax)
    st = D.seat_stats()

    y = 0.985
    txt(ax, 0.0, y, "座席与尺寸对账", fs=9.4, weight="bold")
    y -= 0.050
    txt(ax, 0.0, y, "层", fs=6.8, color=C["muted"])
    txt(ax, 0.30, y, "排", fs=6.8, color=C["muted"])
    txt(ax, 0.60, y, "席位", fs=6.8, color=C["muted"], ha="right")
    y -= 0.036
    ax.plot([0, 0.60], [y + 0.012] * 2, color=C["grid"], lw=0.6)
    for nm, nr, ns in (("池座", f'{st["pit"]["rows"]} 排', f'{st["pit"]["seats"]:,} 席'),
                       ("二层挑台", f'{st["bal1"]["rows"]} 排', f'{st["bal1"]["seats"]:,} 席'),
                       ("三层挑台", f'{st["bal2"]["rows"]} 排', f'{st["bal2"]["seats"]:,} 席')):
        txt(ax, 0.0, y, nm, fs=7.4)
        txt(ax, 0.30, y, nr, fs=7.4, color=C["muted"])
        txt(ax, 0.60, y, ns, fs=7.4, ha="right")
        y -= 0.038
    ax.plot([0, 0.60], [y + 0.012] * 2, color=C["grid"], lw=0.6)
    txt(ax, 0.0, y, "观众厅合计", fs=7.6, weight="bold")
    txt(ax, 0.60, y, f'{D.total_seats():,} 席', fs=7.6, ha="right", weight="bold",
        color=C["red"])
    y -= 0.034
    txt(ax, 0.0, y, "主席台（不计入万人席）", fs=7.0, color=C["muted"])
    txt(ax, 0.60, y, f'{D.STAGE_SEATS} 席', fs=7.0, ha="right", color=C["muted"])
    y -= 0.034
    txt(ax, 0.0, y, "总容量", fs=7.6, weight="bold")
    txt(ax, 0.60, y, f'{D.total_seats() + D.STAGE_SEATS:,} 人', fs=7.6, ha="right",
        weight="bold")

    y -= 0.056
    txt(ax, 0.0, y, "关键尺寸", fs=9.4, weight="bold")
    y -= 0.044
    kv = [
        ("台口（无立柱开敞）", f'{D.PROSCENIUM["w"]:.0f} × {D.PROSCENIUM["h"]:.0f} m'),
        ("观众厅（前→后）", f'{D.HALL["w_front"]:.0f} → {D.HALL["w_rear"]:.0f} m'),
        ("观众厅进深", f'{D.HALL["depth"]:.0f} m'),
        ("净高（穹顶顶心）", f'{D.HALL["z_apex"]:.0f} m'),
        ("池座／二层／三层地坪",
         f'{D.TIERS[0]["z0"]:.1f}／{D.TIERS[1]["z0"]:.1f}／{D.TIERS[2]["z0"]:.1f} m'),
        ("挑台坡度（池座／二层／三层）",
         f'{D.TIERS[0]["slope"]*100:.1f}%／{D.TIERS[1]["slope"]*100:.0f}%／'
         f'{D.TIERS[2]["slope"]*100:.0f}%'),
        ("座宽 × 排距", f'{D.SEAT["pitch"]:.2f} × {D.SEAT["row"]:.2f} m'),
        ("纵向走道", f'{D.SEAT["aisle"]:.1f} m，弧长约 {D.SEAT["aisle_every"]:.0f} m 一道'),
        ("最远观众至台口", "42.9 m"),
        ("中央前厅", f'{D.FOYER["x1"] - D.FOYER["x0"]:.0f} × 240 m，净高 {D.FOYER["h"]:.0f} m'),
    ]
    for k, v in kv:
        txt(ax, 0.0, y, k, fs=6.8, color=C["muted"])
        txt(ax, 0.62, y, v, fs=6.8, ha="right")
        y -= 0.0325

    y -= 0.020
    txt(ax, 0.0, y, "口径", fs=9.4, weight="bold")
    y -= 0.040
    notes = [
        ("【设定】", "中厅为无立柱万人大礼堂，约 10,000 席（长安城市志卷二、总设定十六编）。"),
        ("【作者】", f'观众厅＋中央前厅；台口 {D.HALL["w_front"]:.0f} m、厅 '
         f'{D.HALL["w_rear"]:.0f} × {D.HALL["depth"]:.0f} m、净高 {D.HALL["z_apex"]:.0f} m；'
         "总量可略超一万席。"),
        ("【参照】", "人民大会堂万人大礼堂：76 × 60 m、净高 33 m、台口 32 × 18 m；"),
        ("", "三层座席 3,693／3,515／2,518；穹顶「水天一色」、三环水波灯槽。"),
        ("【改写】", "红五星→国徽圆盘（长安城墙＋金蟠龙＋稻穗齿轮）；光芒线 72 道；"),
        ("", "旗用红底金龙旗。依《国家象征物（2026）》。"),
        ("【推定】", "挑台为 U 形（侧翼向前包转）；三层后缘逐级退缩成三级后厅。"),
    ]
    for tag, s in notes:
        txt(ax, 0.0, y, tag, fs=6.6, color=C["red"], weight="bold")
        txt(ax, 0.125, y, s, fs=6.6, color=C["muted"])
        y -= 0.0315


# ------------------------------------------------------------------ 图例
def draw_legend(ax):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    clean(ax)
    y = 0.965
    txt(ax, 0.0, y, "图例", fs=9.4, weight="bold")
    y -= 0.095
    items = [
        (C["pit"], "池座 3,960 席（42 排）"),
        (C["bal1"], "二层挑台 3,491 席（40 排，U 形）"),
        (C["bal2"], "三层挑台 2,492 席（26 排，U 形）"),
        (C["stagefill"], "主席台 44 × 28 m，台面 +1.5 m"),
        (C["foyerfill"], "中央前厅 79 × 240 m，净高 24 m"),
        (C["side"], "侧厅 · 休息厅 · 楼梯"),
        (C["red"], "铜门（厅内 3 樘／东立面 5 樘）"),
        (C["gold"], "台口金线脚 · 穹顶灯槽"),
    ]
    for col, s in items:
        ax.add_patch(Rectangle((0.0, y - 0.017), 0.045, 0.034, facecolor=col,
                               edgecolor=C["wall"], lw=0.5))
        txt(ax, 0.068, y, s, fs=6.7)
        y -= 0.068

    y -= 0.035
    txt(ax, 0.0, y, "待作者定", fs=9.4, weight="bold")
    y -= 0.072
    for s in ("① 国徽直径：暂定 6.4 m（参照真实约 6 m）。",
              "② 台口两侧是否设 10 面红底金龙旗。",
              "③ 池座是否设代表席小桌（真实为桌＋椅，本稿按椅排）。",
              "④ 三级后厅是否改为平层＋大楼梯。"):
        txt(ax, 0.0, y, s, fs=6.6, color=C["muted"])
        y -= 0.060


# ------------------------------------------------------------------ 主图
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--out", default=os.path.join(HERE, "..", "..", "docs", "assets"))
    ap.add_argument("--name", default="国家广场(2026)·万人大礼堂·草稿")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    fig = plt.figure(figsize=(16.6, 12.6), dpi=args.dpi, facecolor=C["paper"])
    gs = GridSpec(3, 2, figure=fig, height_ratios=[1.50, 0.50, 0.46],
                  width_ratios=[1.34, 1.0], left=0.030, right=0.978,
                  top=0.922, bottom=0.030, hspace=0.14, wspace=0.07)

    draw_plan(fig.add_subplot(gs[0, 0]))
    draw_info(fig.add_subplot(gs[0, 1]))
    draw_long(fig.add_subplot(gs[1, :]))
    draw_cross(fig.add_subplot(gs[2, 0]))
    draw_legend(fig.add_subplot(gs[2, 1]))

    fig.text(0.030, 0.968, "国家大会堂 · 中厅 · 万人大礼堂",
             fontsize=21, fontweight="bold", color=C["ink"], va="top")
    fig.text(0.030, 0.937,
             f'草稿 · 扇面无立柱 · 池座＋两层 U 形挑台 {D.total_seats():,} 席 ＋ 主席台 '
             f'{D.STAGE_SEATS} 席',
             fontsize=9.0, color=C["muted"], va="top")
    fig.text(0.978, 0.968,
             "国家广场(2026) · 承天门正南 · 广场西侧\n"
             "坐标：宫城中心为原点，+x 东、+y 北，米",
             fontsize=7.6, color=C["muted"], va="top", ha="right", linespacing=1.7)
    fig.text(0.978, 0.030, "tools/grandhall/build_draft.py · hall_data.py",
             fontsize=6.2, color=C["muted"], ha="right")

    for ext, kw in (("webp", dict(pil_kwargs={"quality": 92, "method": 6})),
                    ("svg", {})):
        path = os.path.join(args.out, f"{args.name}.{ext}")
        fig.savefig(path, facecolor=C["paper"], dpi=args.dpi, **kw)
        print("OUT", path, os.path.getsize(path) // 1024, "KB")
    plt.close(fig)


if __name__ == "__main__":
    main()
