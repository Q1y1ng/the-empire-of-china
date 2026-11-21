"""宫城（皇宫）2D 总平面图 —— 由 palace_data.py 驱动，输出 PNG + SVG。

排布口径：按故宫（紫禁城）院落语法——外朝三殿同台，内廷后三宫，东西六宫各成院落，
值房沿墙成排，内金水河与五桥，四隅角楼。设定里的分区面积只作文档口径，不画分区线。

用法：
    python build_plan.py                      # 300 dpi → ../../docs/assets
    python build_plan.py --dpi 150 --out DIR  # 预览
"""

import argparse
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Polygon, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import palace_data as D  # noqa: E402

C = dict(
    paper="#F2EEE4", ground_out="#E5DFD2", ground_in="#FBF8F1",
    water="#A8C8D8", water_edge="#5B8CA6",
    wall="#9E2B25", wall_edge="#6E1B17", inner_wall="#8C5B52", inner_wall_edge="#6B4038",
    hall="#EBC96B", hall_edge="#8A6A1E", base="#DDD7C9", base_edge="#B3AA99",
    platform="#EDE7D9", platform_edge="#BFB49E",
    corridor="#E8DCC0", corridor_edge="#A79572",
    garden="#C9D9B6", garden_edge="#7E9468", tree="#6E8A55", rock="#B9AE9B",
    modern="#8FA9B8", modern_edge="#4E6B7A", service="#D9D2C3", service_edge="#B4AB9C",
    ink="#33302B", muted="#6B6257", axis="#B03027",
)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False


def rect(ax, x0, y0, w, h, **kw):
    ax.add_patch(Rectangle((x0, y0), w, h, **kw))


def ribbon(points, width):
    pts = np.asarray(points, float)
    norms = []
    for i in range(len(pts)):
        if i == 0:
            d = pts[1] - pts[0]
        elif i == len(pts) - 1:
            d = pts[-1] - pts[-2]
        else:
            d = pts[i + 1] - pts[i - 1]
        n = np.array([-d[1], d[0]])
        L = float(np.hypot(*n)) or 1.0
        norms.append(n / L)
    left = [p + n * width / 2 for p, n in zip(pts, norms)]
    right = [p - n * width / 2 for p, n in zip(pts, norms)]
    return np.array(left + right[::-1])


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

    for y in (-hd, hd):
        gw = op["S"] if y < 0 else op["N"]
        bar(-hw - t / 2, y - t / 2, hw + t / 2 - gw / 2, t)
        bar(gw / 2, y - t / 2, hw + t / 2 - gw / 2, t)
    for x in (-hw, hw):
        gw = op["E"] if x > 0 else op["W"]
        bar(x - t / 2, -hd - t / 2, t, hd + t / 2 - gw / 2)
        bar(x - t / 2, gw / 2, t, hd + t / 2 - gw / 2)

    ct = D.CORNER_TOWER
    for sx in (-1, 1):
        for sy in (-1, 1):
            rect(ax, sx * hw - ct["w"] / 2, sy * hd - ct["d"] / 2, ct["w"], ct["d"],
                 facecolor=C["wall"], edgecolor=C["wall_edge"], lw=0.6, zorder=4.2)


def draw_inner_walls(ax):
    for w in D.inner_line_walls():
        ax.add_patch(Rectangle((w["x0"], w["y0"]), w["x1"] - w["x0"], w["y1"] - w["y0"],
                               facecolor=C["inner_wall"], edgecolor="none", zorder=3.2))
    for c in D.COMPOUNDS:
        for w in D.compound_walls(c):
            ax.add_patch(Rectangle((w["x0"], w["y0"]), w["x1"] - w["x0"],
                                   w["y1"] - w["y0"], facecolor=C["inner_wall"],
                                   edgecolor="none", zorder=3.2))


def draw_ground(ax):
    # 琼苑绿地
    g = next(c for c in D.COMPOUNDS if c["name"] == "琼苑")
    rect(ax, g["x0"] + 2, g["y0"] + 2, g["x1"] - g["x0"] - 4, g["y1"] - g["y0"] - 4,
         facecolor=C["garden"], edgecolor="none", zorder=1.6)
    for x, y in D.trees():
        ax.add_patch(Circle((x, y), 3.4, facecolor=C["tree"], edgecolor="none",
                            alpha=0.75, zorder=1.8))


def draw_water(ax):
    R = D.RIVER
    ax.add_patch(Polygon(ribbon(R["points"], R["width"]), closed=True,
                         facecolor=C["water"], edgecolor=C["water_edge"], lw=0.6, zorder=1.7))


def draw_platforms(ax):
    ax.add_patch(Polygon(D.PLATFORM_POLY, closed=True, facecolor=C["platform"],
                         edgecolor=C["platform_edge"], lw=0.8, zorder=2.2))
    for p in D.PLATFORMS:
        rect(ax, p["cx"] - p["w"] / 2, p["cy"] - p["d"] / 2, p["w"], p["d"],
             facecolor=C["platform"], edgecolor=C["platform_edge"], lw=0.8, zorder=2.2)


def draw_service(ax):
    for cx, cy, w, d, _h in D.service_blocks():
        rect(ax, cx - w / 2, cy - d / 2, w, d, facecolor=C["service"],
             edgecolor=C["service_edge"], lw=0.35, zorder=2.0)


def draw_structs(ax):
    for s in D.STRUCTS:
        k = s["kind"]
        x0, y0 = s["cx"] - s["w"] / 2, s["cy"] - s["d"] / 2
        if s.get("base"):
            b = s["base"]
            rect(ax, s["cx"] - b["w"] / 2, s["cy"] - b["d"] / 2, b["w"], b["d"],
                 facecolor=C["base"], edgecolor=C["base_edge"], lw=0.6, zorder=2.6)
        if s.get("terrace"):
            t = s["terrace"]
            rect(ax, s["cx"] - t["w"] / 2, t["cy"] - t["d"] / 2, t["w"], t["d"],
                 facecolor=C["base"], edgecolor=C["base_edge"], lw=0.5, zorder=2.5)

        if k == "corridor":
            fc, ec, z = C["corridor"], C["corridor_edge"], 2.8
        elif k == "modern":
            fc, ec, z = C["modern"], C["modern_edge"], 3.0
        elif k == "rock":
            fc, ec, z = C["rock"], "#8C8272", 2.9
        elif k == "bridge":
            fc, ec, z = C["base"], C["base_edge"], 2.4
        elif k == "gate":
            fc, ec, z = C["wall"], C["wall_edge"], 3.6
        else:
            fc, ec, z = C["hall"], C["hall_edge"], 3.4

        hatch = "////" if k == "modern" else None
        if k == "rock":
            ax.add_patch(Polygon([(x0 + 4, y0), (x0 + s["w"] - 2, y0 + 3),
                                  (x0 + s["w"], y0 + s["d"] - 4), (x0 + 12, y0 + s["d"]),
                                  (x0, y0 + 6)], closed=True, facecolor=fc,
                                 edgecolor=ec, lw=0.6, zorder=z))
        else:
            rect(ax, x0, y0, s["w"], s["d"], facecolor=fc, edgecolor=ec, lw=0.8,
                 zorder=z, hatch=hatch)
        if s.get("tower"):
            t = s["tower"]
            rect(ax, s["cx"] - t["w"] / 2, s["cy"] - t["d"] / 2, t["w"], t["d"],
                 facecolor="#D8A64A", edgecolor=C["hall_edge"], lw=0.7, zorder=z + 0.1)

        name = s["name"]
        if k == "corridor" or k in ("bridge",):
            continue
        if name in {g["name"] for g in D.GATES}:
            continue                      # 四门由 draw_gate_labels 统一标注
        if ("雁翅楼" in name or name.startswith("六宫") or "配殿" in name
                or any(k in name for k in ("后罩房", "营房", "器械库", "东厢", "西厢", "宫门", "五所"))):
            continue
        if s["w"] >= 44 and s["d"] >= 26 and abs(s["cx"]) < 1:
            # 中轴大殿：名字放右侧，避开动线编号
            ax.text(s["cx"] + s["w"] / 2 + 8, s["cy"], name, ha="left", va="center",
                    fontsize=8.4, color=C["ink"], zorder=6,
                    bbox=dict(boxstyle="round,pad=0.14", fc="white", ec="none", alpha=0.75))
        elif s["w"] >= 44 and s["d"] >= 26:
            fs = 8.0
            ax.text(s["cx"], s["cy"], name, ha="center", va="center", fontsize=fs,
                    color=C["ink"], zorder=6,
                    bbox=dict(boxstyle="round,pad=0.14", fc="white", ec="none", alpha=0.72))
        elif k not in ("pavilion",) and "配殿" not in name:
            ax.text(s["cx"], s["cy"], name, ha="center", va="center", fontsize=6.0,
                    color=C["ink"], zorder=6)


def draw_compound_labels(ax):
    for c in D.COMPOUNDS:
        nm = c["name"]
        if nm.startswith("六宫·"):
            continue
        elif nm == "琼苑":
            ax.text(c["x0"] + 6, c["y1"] - 6, "琼苑（御花园）", ha="left", va="top",
                    fontsize=7.2, color=C["muted"], zorder=5.5,
                    bbox=dict(boxstyle="square,pad=0.12", fc=C["ground_in"], ec="none", alpha=0.75))
        else:
            ax.text(c["x0"] + 4, c["y1"] - 4, nm, ha="left", va="top", fontsize=6.8,
                    color=C["muted"], zorder=5.5,
                    bbox=dict(boxstyle="square,pad=0.12", fc=C["ground_in"], ec="none", alpha=0.7))


def draw_court_group_labels(ax):
    for x, name in ((322, "东六宫"), (-322, "西六宫")):
        ax.text(x, 200, name, rotation=90, ha="center", va="center", fontsize=8.2,
                color=C["muted"], zorder=5.5)



def draw_gate_labels(ax, P):
    hw, hd = P["width"] / 2, P["depth"] / 2
    off = P["moat_w"] + 16
    ax.text(0, -hd - off, "承天门", ha="center", va="top", fontsize=10.5, color=C["ink"],
            zorder=6.5, bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))
    ax.text(0, hd + off, "玄武门", ha="center", va="bottom", fontsize=10.5, color=C["ink"],
            zorder=6.5, bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))
    for x, name in ((-hw - 28, "西华门"), (hw + 28, "东华门")):
        ax.text(x, -90, name, ha="center", va="center", fontsize=9.0, color=C["ink"],
                rotation=90, zorder=6.5,
                bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.85))


def draw_axis_and_route(ax, P):
    hd = P["depth"] / 2
    ax.plot([0, 0], [-hd + 10, hd - 10], color=C["axis"], lw=0.9, ls=(0, (7, 3, 1, 3)),
            zorder=5, alpha=0.7)
    ax.annotate("", xy=(0, hd - 12), xytext=(0, hd - 60),
                arrowprops=dict(arrowstyle="-|>", color=C["axis"], lw=1.2), zorder=5)
    ax.text(-14, -330, D.AXIS_LABEL, rotation=90, ha="center", va="center", fontsize=7.2,
            color=C["axis"], zorder=5)

    for num, _name, _x, y in D.ROUTE:
        ax.scatter([0], [y], s=88, c=C["axis"], edgecolors="white", linewidths=1.1, zorder=6.2)
        ax.text(0, y, str(num), ha="center", va="center", fontsize=5.8, color="white", zorder=6.3)


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
    ("殿宇（庑殿/攒尖）", dict(facecolor=C["hall"], edgecolor=C["hall_edge"])),
    ("台基 / 月台", dict(facecolor=C["base"], edgecolor=C["base_edge"])),
    ("三台", dict(facecolor=C["platform"], edgecolor=C["platform_edge"])),
    ("廊庑", dict(facecolor=C["corridor"], edgecolor=C["corridor_edge"])),
    ("宫墙（院内）", dict(facecolor=C["inner_wall"], edgecolor=C["inner_wall_edge"])),
    ("城墙 / 城门", dict(facecolor=C["wall"], edgecolor=C["wall_edge"])),
    ("水面 / 内金水河", dict(facecolor=C["water"], edgecolor=C["water_edge"])),
    ("琼苑绿地", dict(facecolor=C["garden"], edgecolor=C["garden_edge"])),
    ("值房（沿墙成排）", dict(facecolor=C["service"], edgecolor=C["service_edge"])),
    ("现代附楼（推定）", dict(facecolor=C["modern"], edgecolor=C["modern_edge"], hatch="////")),
]


def draw_panel(ax, P):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0, 0.99, "图　例", fontsize=12, color=C["ink"], fontweight="bold", va="top")

    y = 0.952
    for label, kw in SWATCHES:
        ax.add_patch(Rectangle((0.0, y - 0.010), 0.08, 0.020, lw=0.7, clip_on=False, **kw))
        ax.text(0.115, y, label, fontsize=7.9, va="center", color=C["ink"])
        y -= 0.0325

    y -= 0.012
    ax.text(0, y, "启门日动线", fontsize=10.0, color=C["ink"], fontweight="bold", va="top")
    y -= 0.024
    ax.text(0, y, "《法律要目·三》第五条", fontsize=7.0, color=C["muted"], va="top")
    y -= 0.028
    for num, name, _x, _yy in D.ROUTE:
        ax.text(0.012, y, f"{num}", fontsize=6.8, color="white", va="center", ha="center",
                bbox=dict(boxstyle="circle,pad=0.25", fc=C["axis"], ec="none"))
        ax.text(0.058, y, name, fontsize=7.9, va="center", color=C["ink"])
        y -= 0.0265

    y -= 0.016
    ax.text(0, y, "分区口径（设定）", fontsize=10.0, color=C["ink"], fontweight="bold", va="top")
    y -= 0.026
    for z in D.ZONES:
        ax.text(0.0, y, z["name"], fontsize=7.6, va="center", color=C["ink"])
        ax.text(1.0, y, f'{z["ha"]} ha', fontsize=7.6, va="center", ha="right", color=C["muted"])
        y -= 0.0245

    y -= 0.012
    ax.text(0, y, "基底统计（本图实测）", fontsize=10.0, color=C["ink"], fontweight="bold", va="top")
    y -= 0.024
    s = D.stats()
    lines = [
        f'殿宇 {s["hall_ha"]:.2f}　廊庑 {s["corridor_ha"]:.2f}　值房 {s["service_ha"]:.2f} ha',
        f'水面 {s["water_ha"]:.2f}　绿地 {s["garden_ha"]:.2f} ha　建筑密度 {s["density_pct"]:.1f}%',
        f'院落 {s["courtyards"]}　单体 {s["structs"]}　墙段 {s["walls"]}',
    ]
    for line in lines:
        ax.text(0, y, line, fontsize=7.2, color=C["ink"], va="center")
        y -= 0.022

    y -= 0.014
    ax.text(0, y, "注", fontsize=9.2, color=C["ink"], fontweight="bold", va="top")
    y -= 0.022
    for line in ("分区面积（8/6/7/7/16/4/24 ha）是设定口径，按文案切；",
                 "本图按故宫院落语法排布（外朝三殿同台、内廷后三宫、",
                 "东西六宫各成院落、值房沿墙、内金水河五桥），两者",
                 "不是同一套切分，故图上不画分区线。"):
        ax.text(0, y, line, fontsize=6.9, color=C["muted"], va="center")
        y -= 0.019


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
    draw_ground(ax)
    draw_water(ax)
    draw_platforms(ax)
    draw_service(ax)
    draw_inner_walls(ax)
    draw_structs(ax)
    draw_compound_labels(ax)
    draw_court_group_labels(ax)
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
             f'墙高 {P["wall_h"]:.0f} m · 护城河宽 {P["moat_w"]:.0f} m　│　'
             f'外朝三殿同台 · 内廷后三宫 · 东西六宫 · 内金水河',
             ha="center", va="center", fontsize=8.8, color=C["muted"])

    fig.text(0.012, 0.018,
             "数据：《长安城市志》卷三（城垣、四门、分区占地、中轴里程）·《总设定》第十六编（殿宇名与用途）·"
             "《法律要目·三》第五条（动线）。\n"
             "院落语法参照故宫（紫禁城）：外朝三殿同台、内廷后三宫、东西六宫各六院（两行三列，每院宫门—前殿—后殿—配殿）、"
             "值房沿墙、内金水河五桥、四隅角楼；单体面阔进深与殿身高度为推定值。",
             ha="left", va="bottom", fontsize=6.8, color=C["muted"], linespacing=1.55)
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
