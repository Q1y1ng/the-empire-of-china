"""大会堂·中厅 与 万人大礼堂 套合 —— 2D 图：平面（+5 m 剖）、纵剖 A—A（y = AXIS_Y）。

    "$TEMP/plaza-build/Scripts/python.exe" build_fit_draft.py --dpi 300
    "$TEMP/plaza-build/Scripts/python.exe" build_fit_draft.py --dpi 110 --out "$TEMP/out"

产物：<out>/国家广场(2026)·大会堂套合·平面剖面.png / .svg
数字全部取自 hall_data（内胆）与 plaza_data 的中厅体块（外壳），不另立口径。
"""

from __future__ import annotations

import argparse
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hall_data as D  # noqa: E402

C = {
    "paper": "#F6F4EF", "ink": "#232220", "muted": "#6E6A61", "grid": "#D9D4C8",
    "wall": "#3B382F", "shell": "#B9B3A2", "gap": "#FFFFFF",
    "hallfill": "#F2EEE3", "stagefill": "#E6DCC6", "foyerfill": "#F3EFE5",
    "backfill": "#E8E2D2", "red": "#A8322A", "gold": "#B08A22", "blue": "#3D5A73",
}
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

AX = D.AXIS_Y
B = D.BUILD                       # 外壳 230 × 240 × 50
SZ = D.SHELL                      # t = 2.0, gap = 0.5
F = D.FOYER
DB = D.DOORBAY
PODIUM = 2.3                      # 台基面

IX0, IX1 = B["x0"] + SZ["t"] + SZ["gap"], B["x1"] - SZ["t"] - SZ["gap"]
IY0, IY1 = B["y0"] + SZ["t"] + SZ["gap"], B["y1"] - SZ["t"] - SZ["gap"]


def txt(ax, x, y, s, fs=7.0, color=None, ha="left", va="center", rot=0, weight="normal"):
    ax.text(x, y, s, fontsize=fs, color=color or C["ink"], ha=ha, va=va,
            rotation=rot, zorder=14, fontweight=weight)


def dim(ax, p0, p1, label, off=0.0, fs=6.4, color=None):
    col = color or C["muted"]
    x0, y0 = p0
    x1, y1 = p1
    ax.annotate("", (x1, y1), (x0, y0),
                arrowprops=dict(arrowstyle="<|-|>", color=col, lw=0.7, shrinkA=0, shrinkB=0),
                zorder=12)
    ax.text((x0 + x1) / 2 + off, (y0 + y1) / 2, label, fontsize=fs, color=col,
            ha="center", va="center", zorder=15,
            bbox=dict(fc=C["paper"], ec="none", pad=1.2))


def leader(ax, xy, xytext, s, fs=6.4):
    ax.annotate(s, xy=xy, xytext=xytext, fontsize=fs, color=C["ink"],
                ha="left", va="center", zorder=15,
                arrowprops=dict(arrowstyle="-", color=C["muted"], lw=0.6),
                bbox=dict(fc=C["paper"], ec="none", pad=1.0))


# ------------------------------------------------------------------ 平面
def plan(ax):
    ax.set_facecolor(C["paper"])
    ax.add_patch(Rectangle((B["x0"], B["y0"]), B["x1"] - B["x0"], B["y1"] - B["y0"],
                           fc=C["shell"], ec="none", zorder=1))
    ax.add_patch(Rectangle((IX0, IY0), IX1 - IX0, IY1 - IY0, fc=C["gap"], ec="none",
                           zorder=2))
    # 内胆：后台 / 主席台 / 观众厅 / 前厅
    Z = D.ZONES
    ax.add_patch(Rectangle((IX0, IY0), Z["stage"]["x0"] - IX0, IY1 - IY0,
                           fc=C["backfill"], ec="none", zorder=3))
    ax.add_patch(Rectangle((Z["stage"]["x0"], AX - D.STAGE["half_w"]),
                           Z["stage"]["x1"] - Z["stage"]["x0"], 2 * D.STAGE["half_w"],
                           fc=C["stagefill"], ec="none", zorder=3))
    hp = D.hall_plan()
    ax.add_patch(Polygon([(x, y) for x, y in hp], closed=True, fc=C["hallfill"],
                         ec="none", zorder=3))
    ax.add_patch(Rectangle((Z["hall"]["x1"], IY0), IX1 - Z["hall"]["x1"], IY1 - IY0,
                           fc=C["foyerfill"], ec="none", zorder=3))
    # 墙体轮廓
    for r in ((B["x0"], B["y0"], B["x1"] - B["x0"], B["y1"] - B["y0"]),
              (B["x0"] + SZ["t"], B["y0"] + SZ["t"],
               B["x1"] - B["x0"] - 2 * SZ["t"], B["y1"] - B["y0"] - 2 * SZ["t"])):
        ax.add_patch(Rectangle((r[0], r[1]), r[2], r[3], fc="none", ec=C["wall"],
                               lw=0.8, zorder=5))
    ax.add_patch(Rectangle((IX0, IY0), IX1 - IX0, IY1 - IY0, fc="none", ec=C["blue"],
                           lw=0.9, ls=(0, (4, 2)), zorder=6))
    # 东墙门洞（24 m）
    ax.plot([B["x1"], B["x1"]], [AX - DB["half_w"], AX + DB["half_w"]],
            color=C["paper"], lw=4.0, zorder=7, solid_capstyle="butt")
    # 玻璃门斗
    ax.add_patch(Rectangle((DB["x"], AX - DB["half_w"]), DB["depth"], 2 * DB["half_w"],
                           fc="none", ec=C["blue"], lw=1.1, zorder=8))
    ax.plot([DB["x"], DB["x"] + DB["depth"]], [AX, AX], color=C["blue"], lw=0.6,
            ls=(0, (2, 2)), zorder=8)
    # 观众厅扇形（扇心 FOCUS）
    for t, a in ((D.TIERS[0], 0.5), (D.TIERS[1], 0.0), (D.TIERS[2], 0.0)):
        ax.add_patch(plt.Circle((D.FOCUS["x"], AX), t["r0"], fill=False,
                                ec=C["grid"], lw=0.5, ls=(0, (2, 3)), zorder=4))
    # 标注
    txt(ax, -425, AX + 128, "国家大会堂·中厅（外壳 230 × 240 m，壁厚 2 m）",
        fs=9.0, ha="center", weight="bold")
    txt(ax, (Z["backstage"]["x0"] + Z["backstage"]["x1"]) / 2 if False else (IX0 + Z["stage"]["x0"]) / 2,
        AX, "后台", fs=7.2, ha="center", rot=90)
    txt(ax, (Z["stage"]["x0"] + Z["stage"]["x1"]) / 2, AX + 30, "主席台", fs=7.2,
        ha="center")
    txt(ax, -436, AX, "万人大礼堂\n（观众厅）", fs=7.6, ha="center", va="center")
    txt(ax, (Z["hall"]["x1"] + IX1) / 2, AX, "中央前厅", fs=7.2, ha="center")
    txt(ax, DB["x"] + 4.5, AX - 22, "玻璃门斗\n24 × 2.2 m", fs=6.6, ha="left",
        color=C["blue"])
    leader(ax, (DB["x"] + DB["depth"], AX - 10), (DB["x"] + 4.0, AX - 20), "")
    leader(ax, (B["x0"] + 1.0, IY1 + 1.6), (B["x0"] + 6, IY1 + 7), "外壳壁 2.0 m")
    leader(ax, (IX0 + 0.25, AX - 60), (B["x0"] - 30, AX - 78), "空腔 0.5 m")
    txt(ax, -440, AX - 100, "侧带（空）", fs=6.4, ha="center", color=C["muted"])
    txt(ax, -440, AX + 100, "侧带（空）", fs=6.4, ha="center", color=C["muted"])
    dim(ax, (B["x0"], B["y0"] - 13), (B["x1"], B["y0"] - 13), "230")
    dim(ax, (B["x0"] - 13, B["y0"]), (B["x0"] - 13, B["y1"]), "240", off=0.0)
    dim(ax, (B["x1"] + 7, AX - DB["half_w"]), (B["x1"] + 7, AX + DB["half_w"]), "24")
    txt(ax, B["x1"] + 9, AX - 62, "东立面", fs=7.0, color=C["muted"])
    ax.set_xlim(B["x0"] - 46, B["x1"] + 24)
    ax.set_ylim(B["y0"] - 26, B["y1"] + 26)
    ax.set_aspect("equal")
    ax.axis("off")


# ------------------------------------------------------------------ 纵剖
def section(ax):
    ax.set_facecolor(C["paper"])
    # 台基（礼堂处掏空）
    ax.add_patch(Rectangle((B["x0"] - 4, 0.12), 4, PODIUM - 0.12, fc=C["shell"],
                           ec=C["wall"], lw=0.5, zorder=3))
    ax.add_patch(Rectangle((B["x1"], 0.12), 4, PODIUM - 0.12, fc=C["shell"],
                           ec=C["wall"], lw=0.5, zorder=3))
    # 外壳墙 + 檐口环
    for x0 in (B["x0"], B["x1"] - SZ["t"]):
        ax.add_patch(Rectangle((x0, PODIUM), SZ["t"], B["h"] - PODIUM, fc=C["shell"],
                               ec=C["wall"], lw=0.7, zorder=4))
    for x0 in (B["x0"] - 4.5, B["x1"] - SZ["t"] - 3.5):
        ax.add_patch(Rectangle((x0, 47.8), 8.0, 2.2, fc=C["shell"], ec=C["wall"],
                               lw=0.6, zorder=5))
    # 琉璃顶
    ax.add_patch(Polygon([(B["x0"] - 6.3, 50.15), (B["x1"] + 6.3, 50.15),
                          ((B["x0"] + B["x1"]) / 2, 64.15)], closed=True,
                         fc="#C9D6CD", ec=C["wall"], lw=0.7, zorder=6))
    # 内胆：地坪与各区
    ax.plot([IX0, IX1], [0, 0], color=C["wall"], lw=1.4, zorder=8)
    Z = D.ZONES
    ax.add_patch(Rectangle((IX0, 0), Z["stage"]["x0"] - IX0, 22.0, fc=C["backfill"],
                           ec=C["wall"], lw=0.5, zorder=7))
    ax.add_patch(Rectangle((Z["stage"]["x0"], 0), Z["stage"]["x1"] - Z["stage"]["x0"],
                           D.STAGE["z"], fc=C["stagefill"], ec="none", zorder=7))
    ax.plot([Z["stage"]["x0"], Z["stage"]["x1"]], [D.STAGE["z"], D.STAGE["z"]],
            color=C["wall"], lw=0.8, zorder=8)
    # 舞台顶板
    ax.add_patch(Rectangle((IX0, D.PROSCENIUM["h"]), Z["stage"]["x1"] - IX0, 0.9,
                           fc=C["grid"], ec=C["wall"], lw=0.4, zorder=7))
    # 池座地坪放坡
    pit = D.TIERS[0]
    rows = D.tier_rows(pit)
    ax.plot([Z["hall"]["x0"], Z["hall"]["x1"]], [0, rows[-1]["z"]], color=C["wall"],
            lw=0.8, zorder=8)
    # 弯顶曲线（三点二次插值）
    xs = np.array([Z["hall"]["x1"], -427.0, Z["hall"]["x0"]])
    zs = np.array([D.HALL["z_spring"], D.HALL["z_apex"], D.HALL["z_spring"]])
    co = np.polyfit(xs, zs, 2)
    xx = np.linspace(Z["hall"]["x0"], Z["hall"]["x1"], 120)
    ax.plot(xx, np.polyval(co, xx), color=C["wall"], lw=1.1, zorder=8)
    # 观演厅两侧竖墙
    for x0 in (Z["hall"]["x1"], Z["hall"]["x0"]):
        ax.plot([x0, x0], [0, D.HALL["z_spring"]], color=C["wall"], lw=1.0, zorder=8)
    # 前厅
    ax.add_patch(Rectangle((Z["hall"]["x1"], 0), IX1 - Z["hall"]["x1"], F["h"],
                           fc=C["foyerfill"], ec=C["wall"], lw=0.6, zorder=7))
    # 门斗平台 + 大台阶
    ax.add_patch(Rectangle((DB["x"], PODIUM - 0.35), DB["depth"], 0.35, fc=C["shell"],
                           ec=C["wall"], lw=0.5, zorder=9))
    n = 12
    for i in range(n):
        x0 = DB["x"] - (i + 1) * (4.0 / n)
        ax.add_patch(Rectangle((x0, 0), 4.0 / n + 0.02, PODIUM - (i + 1) * PODIUM / n,
                               fc=C["shell"], ec=C["wall"], lw=0.3, zorder=9))
    # 标注
    txt(ax, (IX0 + IX1) / 2, 70, "纵剖 A—A（y = −1035.5）", fs=9.0, ha="center",
        weight="bold")
    txt(ax, -425, 57, "琉璃顶 50.15—64.15", fs=6.6, ha="center", color=C["muted"])
    txt(ax, -425, 45.5, "穹顶顶 50.0", fs=6.6, ha="center", color=C["muted"])
    txt(ax, -460, 33.5, "起拱 32.0", fs=6.4, ha="center", color=C["muted"])
    txt(ax, -500, 17, "主席台 +1.5\n台口 22.0", fs=6.4, ha="center", color=C["muted"])
    txt(ax, -425, 12, "池座放坡 0—3.07", fs=6.4, ha="center", color=C["muted"])
    txt(ax, -350, 12, "中央前厅\n净高 24.0", fs=6.4, ha="center", color=C["muted"])
    txt(ax, IX0 + 3, 11, "后台 22.0", fs=6.4, ha="left", color=C["muted"])
    leader(ax, (DB["x"] - 1.0, PODIUM), (DB["x"] - 26, 6.5),
           "玻璃门斗平台 +2.30\n12 级大台阶 → 前厅 0.00")
    # 下沉尺寸
    ax.annotate("", (B["x1"] + 8, 0.0), (B["x1"] + 8, PODIUM),
                arrowprops=dict(arrowstyle="<|-|>", color=C["red"], lw=0.9, shrinkA=0,
                                shrinkB=0))
    txt(ax, B["x1"] + 9.5, PODIUM / 2 + 1.2, "下沉 2.30", fs=7.0, color=C["red"])
    # 顶隙（穹顶顶 50.0 ↔ 琉璃顶底 50.15）
    ax.annotate("", (-412, D.HALL["z_apex"]), (-412, 50.15),
                arrowprops=dict(arrowstyle="<|-|>", color=C["gold"], lw=0.8, shrinkA=0,
                                shrinkB=0))
    txt(ax, -406, 51.4, "隙 0.15", fs=6.4, color=C["gold"])
    dim(ax, (B["x0"], -4.5), (B["x1"], -4.5), "230")
    dim(ax, (B["x1"] + 20, 0.12), (B["x1"] + 20, B["h"]), "50.0")
    ax.set_xlim(B["x0"] - 30, B["x1"] + 30)
    ax.set_ylim(-9, 74)
    ax.set_aspect("equal")
    ax.axis("off")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--out", default=os.path.join(HERE, "..", "..", "docs", "assets"))
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)

    fig = plt.figure(figsize=(13.6, 11.0), dpi=a.dpi, facecolor=C["paper"])
    gs = fig.add_gridspec(2, 1, height_ratios=[1.0, 0.52], hspace=0.02,
                          left=0.055, right=0.975, top=0.955, bottom=0.035)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])
    plan(ax1)
    section(ax2)

    note = ("口径：外壳取自 plaza_data 的中厅体块（x −540…−310、y −1155.5…−915.5、檐高 50）；"
            "内胆取自 hall_data。作者 2026-11-25 裁决——中厅不抬高、礼堂下沉 2.3 m、"
            "体块挖空 2 m 壁厚、前厅东墙改玻璃门斗。")
    fig.text(0.055, 0.985, note, fontsize=6.8, color=C["muted"], ha="left", va="top")

    for ext, kw in (("webp", dict(pil_kwargs={"quality": 92, "method": 6})),
                    ("svg", {})):
        p = os.path.join(out, f"国家广场(2026)·大会堂套合·平面剖面.{ext}")
        fig.savefig(p, facecolor=C["paper"], dpi=a.dpi, **kw)
        print("SAVED", p, flush=True)


if __name__ == "__main__":
    main()
