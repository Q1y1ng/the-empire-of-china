"""宫城（皇宫）2D 总平面图 —— 由 palace_data.py 驱动，输出 PNG + SVG。

用法：
    python build_plan.py                     # 输出到 ../../docs/assets/
    python build_plan.py --out DIR --dpi 150 # 预览用小图
"""

import argparse
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches  # noqa: F401
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import palace_data as D  # noqa: E402

# ------------------------------------------------------------------ 配色
C = dict(
    paper="#F2EEE4", ground_out="#E5DFD2", ground_in="#FBF8F1",
    water="#A8C8D8", water_edge="#5B8CA6", wall="#9E2B25", wall_edge="#6E1B17",
    hall="#EBC96B", hall_edge="#8A6A1E", base="#DDD7C9", base_edge="#B3AA99",
    garden="#C9D9B6", garden_edge="#7E9468", modern="#8FA9B8", modern_edge="#4E6B7A",
    service="#D9D2C3", service_edge="#B4AB9C",
    zone_edge="#8A8073", ink="#33302B", muted="#6B6257", axis="#B03027",
    path="#EFE7D6",
)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

# 图上只写短名，全名留给 3D 与说明
SHORT = {
    "紫光阁·东配殿": "东配殿", "紫光阁·西配殿": "西配殿",
    "政枢殿·北配殿": "北配殿", "政枢殿·南配殿": "南配殿",
    "紫光阁·现代附楼": "现代附楼",
    "六宫·西一": "西一", "六宫·西二": "西二", "六宫·西三": "西三",
    "六宫·东一": "东一", "六宫·东二": "东二", "六宫·东三": "东三",
}


def rect(ax, x0, y0, w, h, **kw):
    ax.add_patch(Rectangle((x0, y0), w, h, **kw))


# ------------------------------------------------------------------ 图面
def draw_moat(ax, P):
    hw = P["width"] / 2 + P["wall_t"] / 2
    hd = P["depth"] / 2 + P["wall_t"] / 2
    ox, oy = hw + P["moat_w"], hd + P["moat_w"]
    rect(ax, -ox, -oy, 2 * ox, 2 * oy, facecolor=C["water"], edgecolor=C["water_edge"],
         lw=0.9, zorder=1)
    rect(ax, -hw, -hd, 2 * hw, 2 * hd, facecolor=C["ground_in"], edgecolor="none", zorder=1.2)


def draw_walls(ax, P):
    hw, hd, t = P["width"] / 2, P["depth"] / 2, P["wall_t"]
    op = {g["side"]: g["opening"] for g in D.GATES}

    def bar(x0, y0, w, h):
        ax.add_patch(Rectangle((x0, y0), w, h, facecolor=C["wall"],
                               edgecolor=C["wall_edge"], lw=0.6, zorder=4))

    # 南北墙（留门洞）
    for y in (-hd, hd):
        gw = op["S"] if y < 0 else op["N"]
        bar(-hw - t / 2, y - t / 2, hw + t / 2 - gw / 2, t)
        bar(gw / 2, y - t / 2, hw + t / 2 - gw / 2, t)
    # 东西墙
    for x in (-hw, hw):
        gw = op["E"] if x > 0 else op["W"]
        bar(x - t / 2, -hd - t / 2, t, hd + t / 2 - gw / 2)
        bar(x - t / 2, gw / 2, t, hd + t / 2 - gw / 2)

    ct = D.CORNER_TOWER
    for sx in (-1, 1):
        for sy in (-1, 1):
            rect(ax, sx * hw - ct["w"] / 2, sy * hd - ct["d"] / 2, ct["w"], ct["d"],
                 facecolor=C["wall"], edgecolor=C["wall_edge"], lw=0.6, zorder=4.2)


def draw_zones(ax):
    for z in D.ZONES:
        if z["key"] == "service":
            continue
        rect(ax, z["x0"], z["y0"], z["x1"] - z["x0"], z["y1"] - z["y0"], facecolor="none",
             edgecolor=C["zone_edge"], lw=0.9, ls=(0, (6, 4)), zorder=2.6)
        if z["key"] in ("east", "west", "court", "mid"):
            tx, ty, va = z["x0"] + 6, z["y0"] + 8, "bottom"
        else:
            tx, ty, va = z["x0"] + 5, z["y1"] - 7, "top"
        ax.text(tx, ty, f'{z["name"]} {z["ha"]} ha', ha="left", va=va,
                fontsize=9, color=C["muted"], zorder=6,
                bbox=dict(boxstyle="square,pad=0.15", fc=C["ground_in"], ec="none", alpha=0.8))

    g = next(z for z in D.ZONES if z["key"] == "garden")
    rect(ax, g["x0"], g["y0"], g["x1"] - g["x0"], g["y1"] - g["y0"],
         facecolor=C["garden"], edgecolor=C["garden_edge"], lw=0.8, zorder=2.2)
    xs = [g["x0"] + 14 + i * 24 for i in range(int((g["x1"] - g["x0"] - 18) / 24))]
    ys = [g["y0"] + 12 + j * 22 for j in range(int((g["y1"] - g["y0"] - 16) / 22))]
    ax.scatter([x for x in xs for _ in ys], [y for _ in xs for y in ys], s=3.0,
               c="#6E8A55", alpha=0.5, zorder=2.3, linewidths=0)


def draw_path_and_service(ax):
    p = D.PATH
    rect(ax, p["x0"], p["y0"], p["x1"] - p["x0"], p["y1"] - p["y0"],
         facecolor=C["path"], edgecolor="#DCD2BE", lw=0.4, zorder=2.1)
    for b in D.BRIDGES:
        rect(ax, b["cx"] - b["w"] / 2, b["cy"] - b["d"] / 2, b["w"], b["d"],
             facecolor=C["base"], edgecolor=C["base_edge"], lw=0.6, zorder=1.8)
    for cx, cy, w, d, _h in D.service_blocks():
        rect(ax, cx - w / 2, cy - d / 2, w, d, facecolor=C["service"],
             edgecolor=C["service_edge"], lw=0.4, zorder=2.9)


def draw_halls(ax):
    for h in D.HALLS:
        if h.get("base"):
            b = h["base"]
            rect(ax, h["cx"] - b["w"] / 2, h["cy"] - b["d"] / 2, b["w"], b["d"],
                 facecolor=C["base"], edgecolor=C["base_edge"], lw=0.7, zorder=3)
        if h.get("terrace"):
            t = h["terrace"]
            rect(ax, h["cx"] - t["w"] / 2, t["cy"] - t["d"] / 2, t["w"], t["d"],
                 facecolor=C["base"], edgecolor=C["base_edge"], lw=0.7, zorder=3, alpha=0.9)
        modern = h["kind"] == "modern"
        gate = h["kind"] == "gate"
        fc = C["modern"] if modern else (C["wall"] if gate else C["hall"])
        ec = C["modern_edge"] if modern else (C["wall_edge"] if gate else C["hall_edge"])
        rect(ax, h["cx"] - h["w"] / 2, h["cy"] - h["d"] / 2, h["w"], h["d"],
             facecolor=fc, edgecolor=ec, lw=0.9, zorder=3.8 if gate else 3.5,
             hatch="////" if modern else None)
        if h.get("tower"):
            t = h["tower"]
            rect(ax, h["cx"] - t["w"] / 2, h["cy"] - t["d"] / 2, t["w"], t["d"],
                 facecolor="#D8A64A", edgecolor=C["hall_edge"], lw=0.8, zorder=3.6)

        if h["name"] in {g["name"] for g in D.GATES}:
            continue
        label = SHORT.get(h["name"], h["name"])
        fs = 8.2 if h["w"] >= 70 and h["d"] >= 40 else 6.6
        if abs(h["cx"]) < 1:      # 中轴殿名放到台基北沿，避开动线编号
            by = h["cy"] + (h["base"]["d"] / 2 + 9 if h.get("base") else h["d"] / 2 + 9)
            ax.text(h["cx"], by, label, ha="center", va="center", fontsize=fs,
                    color=C["ink"], zorder=6,
                    bbox=dict(boxstyle="round,pad=0.14", fc="white", ec="none", alpha=0.8))
        else:
            ax.text(h["cx"], h["cy"], label, ha="center", va="center", fontsize=fs,
                    color=C["ink"], zorder=6,
                    bbox=dict(boxstyle="round,pad=0.14", fc="white", ec="none", alpha=0.72))

    # 六宫整组说明
    ax.text(-250, 250, "六宫（东三／西三）", ha="left", va="bottom", fontsize=7.2,
            color=C["muted"], zorder=6)


def draw_gate_labels(ax, P):
    hw, hd = P["width"] / 2, P["depth"] / 2
    off = P["moat_w"] + 18
    ax.text(0, -hd - off, "承天门", ha="center", va="top", fontsize=10.5, color=C["ink"],
            zorder=6.5, bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))
    ax.text(0, hd + off, "玄武门", ha="center", va="bottom", fontsize=10.5, color=C["ink"],
            zorder=6.5, bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))
    for x, name in ((-hw - 26, "西华门"), (hw + 26, "东华门")):
        ax.text(x, 0, name, ha="center", va="center", fontsize=9.2, color=C["ink"],
                rotation=90, zorder=6.5,
                bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.85))


def draw_axis_and_route(ax, P):
    hd = P["depth"] / 2
    ax.plot([0, 0], [-hd, hd], color=C["axis"], lw=1.0, ls=(0, (7, 3, 1, 3)),
            zorder=5, alpha=0.8)
    ax.annotate("", xy=(0, hd - 6), xytext=(0, hd - 64),
                arrowprops=dict(arrowstyle="-|>", color=C["axis"], lw=1.3), zorder=5)
    ax.text(-16, -395, "中轴 961 m", rotation=90, ha="center", va="center", fontsize=7.4,
            color=C["axis"], zorder=5)

    for num, _name, _x, y in D.ROUTE:
        ax.scatter([20], [y], s=86, c=C["axis"], edgecolors="white", linewidths=1.1, zorder=6.2)
        ax.text(20, y, str(num), ha="center", va="center", fontsize=6.0, color="white", zorder=6.3)


def draw_dimensions(ax, P):
    hw, hd = P["width"] / 2, P["depth"] / 2
    y = -hd - P["moat_w"] - 62
    ax.annotate("", xy=(-hw, y), xytext=(hw, y),
                arrowprops=dict(arrowstyle="<|-|>", color=C["ink"], lw=0.9,
                                shrinkA=0, shrinkB=0), zorder=6)
    for x in (-hw, hw):
        ax.plot([x, x], [y - 7, y + 7], color=C["ink"], lw=0.8, zorder=6)
        ax.plot([x, x], [-hd - 4, y + 6], color=C["ink"], lw=0.4, ls=(0, (2, 3)), zorder=5.5)
    ax.text(0, y - 10, f'{P["width"]:.0f} m', ha="center", va="top", fontsize=8.4, color=C["ink"])

    x = hw + P["moat_w"] + 34
    ax.annotate("", xy=(x, -hd), xytext=(x, hd),
                arrowprops=dict(arrowstyle="<|-|>", color=C["ink"], lw=0.9,
                                shrinkA=0, shrinkB=0), zorder=6)
    for yy in (-hd, hd):
        ax.plot([x - 7, x + 7], [yy, yy], color=C["ink"], lw=0.8, zorder=6)
        ax.plot([hw + 4, x + 6], [yy, yy], color=C["ink"], lw=0.4, ls=(0, (2, 3)), zorder=5.5)
    ax.text(x + 11, 0, f'{P["depth"]:.0f} m', rotation=90, ha="center", va="center",
            fontsize=8.4, color=C["ink"])


# ------------------------------------------------------------------ 侧栏
SWATCHES = [
    ("殿宇（庑殿顶）", dict(facecolor=C["hall"], edgecolor=C["hall_edge"])),
    ("台基 / 月台", dict(facecolor=C["base"], edgecolor=C["base_edge"])),
    ("城墙 / 门楼", dict(facecolor=C["wall"], edgecolor=C["wall_edge"])),
    ("护城河", dict(facecolor=C["water"], edgecolor=C["water_edge"])),
    ("琼苑", dict(facecolor=C["garden"], edgecolor=C["garden_edge"])),
    ("值房（示意）", dict(facecolor=C["service"], edgecolor=C["service_edge"])),
    ("现代附楼（推定）", dict(facecolor=C["modern"], edgecolor=C["modern_edge"], hatch="////")),
]


def draw_panel(ax, P):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0, 0.985, "图　例", fontsize=12, color=C["ink"], fontweight="bold",
            va="top", transform=ax.transAxes)

    y = 0.935
    for label, kw in SWATCHES:
        ax.add_patch(Rectangle((0.0, y - 0.012), 0.09, 0.024, lw=0.7, clip_on=False, **kw))
        ax.text(0.13, y, label, fontsize=8.6, va="center", color=C["ink"])
        y -= 0.042

    y -= 0.012
    ax.text(0, y, "启门日动线", fontsize=10.5, color=C["ink"], fontweight="bold", va="top")
    y -= 0.032
    ax.text(0, y, "《法律要目·三》第五条", fontsize=7.6, color=C["muted"], va="top")
    y -= 0.030
    for num, name, _x, _yy in D.ROUTE:
        ax.text(0.0, y, f"{num}", fontsize=7.6, color="white", va="center", ha="center",
                bbox=dict(boxstyle="circle,pad=0.28", fc=C["axis"], ec="none"))
        ax.text(0.075, y, name, fontsize=8.4, va="center", color=C["ink"])
        y -= 0.030

    y -= 0.020
    ax.text(0, y, "分区面积（实际 / 设定）", fontsize=10.5, color=C["ink"],
            fontweight="bold", va="top")
    y -= 0.030
    ax.text(0.80, y, "实际", fontsize=7.2, va="center", ha="right", color=C["muted"])
    ax.text(1.0, y, "设定", fontsize=7.2, va="center", ha="right", color=C["muted"])
    y -= 0.026
    for name, actual, want, dev in D.check():
        if name.startswith("宫城总面积"):
            y -= 0.012
        ax.text(0.0, y, name, fontsize=7.9, va="center", color=C["ink"])
        ax.text(0.80, y, f"{actual:.2f}", fontsize=7.9, va="center", ha="right",
                color=C["ink"])
        ax.text(1.0, y, f"{want:.1f} ha", fontsize=7.9, va="center", ha="right",
                color=C["muted"])
        y -= 0.0285
        if y < 0.10:
            break


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "..", "..", "docs", "assets"))
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--name", default="皇宫宫城(2026)·总平面图")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    P = D.PALACE
    fig = plt.figure(figsize=(14.0, 16.0), dpi=args.dpi, facecolor=C["paper"])
    ax = fig.add_axes([0.012, 0.045, 0.655, 0.885])
    ax.set_facecolor(C["ground_out"])
    ax.set_aspect("equal")
    ax.set_xlim(-470, 470)
    ax.set_ylim(-690, 600)
    ax.axis("off")

    draw_moat(ax, P)
    draw_path_and_service(ax)
    draw_zones(ax)
    draw_halls(ax)
    draw_walls(ax, P)
    draw_gate_labels(ax, P)
    draw_axis_and_route(ax, P)
    draw_dimensions(ax, P)

    panel = fig.add_axes([0.688, 0.045, 0.295, 0.885])
    draw_panel(panel, P)

    fig.text(0.34, 0.968, "宫城（皇宫）总平面", ha="center", va="center",
             fontsize=25, color=C["ink"], fontweight="bold")
    fig.text(0.34, 0.948,
             f'长安 · 2026　│　{P["width"]:.0f} × {P["depth"]:.0f} m　│　0.72 km²　│　'
             f'墙高 {P["wall_h"]:.0f} m · 护城河宽 {P["moat_w"]:.0f} m',
             ha="center", va="center", fontsize=9.8, color=C["muted"])

    fig.text(0.012, 0.018,
             "数据：《长安城市志》卷三（城垣、四门、分区占地、中轴里程）·《总设定》第十六编（殿宇名与用途）·"
             "《法律要目·三》第五条（动线）。\n"
             "四至、单体面阔进深与值房排布为按占地反推的推定值（明官式为骨，不作考据复原）；现代附楼属架空混合改造。",
             ha="left", va="bottom", fontsize=7.0, color=C["muted"], linespacing=1.55)
    fig.text(0.978, 0.018, "中华帝国设定集 · 图版", ha="right", va="bottom",
             fontsize=8, color=C["muted"])

    png = os.path.join(args.out, f"{args.name}.png")
    svg = os.path.join(args.out, f"{args.name}.svg")
    fig.savefig(png, dpi=args.dpi, facecolor=C["paper"])
    fig.savefig(svg, facecolor=C["paper"])
    plt.close(fig)
    print(f"[ok] {os.path.abspath(png)}")
    print(f"[ok] {os.path.abspath(svg)}")


if __name__ == "__main__":
    main()
