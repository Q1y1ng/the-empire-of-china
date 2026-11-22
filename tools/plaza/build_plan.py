"""国家广场与广场建筑群 —— 2D 总平面（最简稿）。

只画「格局」：广场、三组建筑体块、承天门接口、中轴与阅兵台、四至尺寸。
不做铺装纹理、树木、灯柱、台阶、立面细节——这些留给白模与精模。

用法：
    python build_plan.py                          # 200 dpi → ../../docs/assets
    python build_plan.py --dpi 300 --out <目录>
    python build_plan.py --check                  # 只打印数字对账
"""

import argparse
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import plaza_data as D  # noqa: E402

C = dict(
    paper="#F2EEE4", ground="#E7E1D4", road="#DDD6C7", road_edge="#C9C0AE",
    plaza="#F0E9D7", plaza_edge="#C8BBA0", terrace="#E8DCC2",
    axis="#DFD0AE", water="#A8C8D8", water_edge="#5B8CA6",
    wall="#9E2B25", wall_edge="#6E1B17", stone="#D9D2C0", stone_edge="#B3A88F",
    hall="#DCC9A2", hall_edge="#8A7752", chamber="#D3BC8A", chamber_edge="#8A7440",
    portico="#E7DABC", portico_edge="#A99772",
    council="#D6C49E", museum="#DACAA6", site_edge="#6B5B45",
    ink="#33302B", muted="#6B6257", axis_red="#B03027",
)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False


def rect(ax, x0, y0, w, h, **kw):
    ax.add_patch(Rectangle((x0, y0), w, h, **kw))


def label(ax, x, y, text, fs=8.0, color=None, ha="center", va="center", box=True, rot=0):
    color = color or C["ink"]
    kw = dict(fontsize=fs, color=color, ha=ha, va=va, zorder=8, rotation=rot)
    if box:
        kw["bbox"] = dict(boxstyle="round,pad=0.22", fc=C["paper"], ec="none", alpha=0.82)
    ax.text(x, y, text, **kw)


# ------------------------------------------------------------------ 底图
def draw_context(ax):
    # 宫城地坪：只留墙内 40 m 的一条，避免上方出现整块色带
    P = D.PALACE
    hw = P["width"] / 2
    rect(ax, -hw - 3, -477.5, 2 * (hw + 3), 70,
         facecolor="#EFE7D6", edgecolor="none", zorder=1.0)
    # 护城河南带
    mo = P["south_wall_outer"]
    bank = P["moat_bank_south"]
    rect(ax, -hw - 55, bank, 2 * (hw + 55), mo - bank,
         facecolor=C["water"], edgecolor=C["water_edge"], lw=0.7, zorder=1.2)
    # 城墙南带（墙心在 -480.5，厚 6）
    rect(ax, -hw - 3, mo, 2 * (hw + 3), 6,
         facecolor=C["wall"], edgecolor=C["wall_edge"], lw=0.6, zorder=3.0)
    # 承天门城台 + 两雁翅楼
    g = P["gate"]
    rect(ax, -g["w"] / 2, g["cy"] - g["d"] / 2, g["w"], g["d"],
         facecolor=C["wall"], edgecolor=C["wall_edge"], lw=0.7, zorder=3.4)
    for sx in (-1, 1):
        rect(ax, sx * 62 - 19, -507, 38, 20,
             facecolor=C["wall"], edgecolor=C["wall_edge"], lw=0.6, zorder=3.3)
    # 跨护城河石桥
    b = D.FEATURES["bridge"]
    rect(ax, b["x0"], b["y0"], b["x1"] - b["x0"], b["y1"] - b["y0"],
         facecolor=C["stone"], edgecolor=C["stone_edge"], lw=0.6, zorder=2.6)
    for x in (-34, 34):
        ax.plot([x, x], [b["y0"], b["y1"]], color=C["stone_edge"], lw=0.5, zorder=2.7)

    ax.text(0, -493, "承天门", ha="center", va="bottom", fontsize=10.5,
            color=C["ink"], zorder=9,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))
    ax.text(0, -433, "宫城（皇宫）南墙", ha="center", va="bottom", fontsize=8.2,
            color=C["muted"], zorder=9,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.8))


def draw_roads(ax):
    for r in D.ROADS:
        rect(ax, r["x0"], r["y0"], r["x1"] - r["x0"], r["y1"] - r["y0"],
             facecolor=C["road"], edgecolor=C["road_edge"], lw=0.45, zorder=1.5)


def draw_plaza(ax):
    P = D.PLAZA
    # 仪典台区
    rect(ax, P["x0"], P["y_north"] - P["terrace_depth"], P["width"], P["terrace_depth"],
         facecolor=C["terrace"], edgecolor=C["plaza_edge"], lw=0.6, zorder=2.0)
    # 铺装
    rect(ax, P["x0"], P["y_south"], P["width"], P["paving_depth"],
         facecolor=C["plaza"], edgecolor=C["plaza_edge"], lw=0.7, zorder=2.0)
    # 50 m 铺装网格（极淡）
    y = P["y_south"] + 50
    while y < P["y_north"] - P["terrace_depth"] - 1:
        ax.plot([P["x0"], P["x1"]], [y, y], color=C["plaza_edge"], lw=0.25,
                alpha=0.30, zorder=2.1)
        y += 50
    for x in range(-250, 300, 50):
        ax.plot([x, x], [P["y_south"], P["y_north"] - P["terrace_depth"]],
                color=C["plaza_edge"], lw=0.25, alpha=0.30, zorder=2.1)

    # 御道、东侧道
    a = D.FEATURES["axis_road"]
    rect(ax, a["x0"], a["y0"], a["x1"] - a["x0"], a["y1"] - a["y0"],
         facecolor=C["axis"], edgecolor="none", zorder=2.2)
    e = D.FEATURES["east_road"]
    rect(ax, e["x0"], e["y0"], e["x1"] - e["x0"], e["y1"] - e["y0"],
         facecolor="#E3D8BF", edgecolor="none", zorder=2.2)

    # 阅兵台
    s = D.FEATURES["review_stand"]
    rect(ax, s["x0"], s["y0"], s["x1"] - s["x0"], s["y1"] - s["y0"],
         facecolor=C["wall"], edgecolor=C["wall_edge"], lw=0.6, zorder=3.6)
    label(ax, 0, -560.5, "阅兵台", fs=7.4, color="white", box=False)


def wall_ring(ax, s, gates):
    """建筑群外墙：按门洞断开。gates = [(side, center, width), ...]"""
    x0, x1, y0, y1 = s["x0"], s["x1"], s["y0"], s["y1"]
    lw = 1.9

    def seg(a, b, c, d):
        ax.plot([a, b], [c, d], color=C["site_edge"], lw=lw,
                solid_capstyle="butt", zorder=4.0)

    def cuts(side, lo, hi):
        spans = sorted((c - w / 2, c + w / 2) for sd, c, w in gates if sd == side)
        out, cur = [], lo
        for a, b in spans:
            if a > cur:
                out.append((cur, min(a, hi)))
            cur = max(cur, b)
        if cur < hi:
            out.append((cur, hi))
        return out

    for a, b in cuts("S", x0, x1):
        seg(a, b, y0, y0)
    for a, b in cuts("N", x0, x1):
        seg(a, b, y1, y1)
    for a, b in cuts("W", y0, y1):
        seg(x0, x0, a, b)
    for a, b in cuts("E", y0, y1):
        seg(x1, x1, a, b)


def draw_sites(ax):
    for s in D.SITES:
        fill = {"hall": "#F3EDDD", "council": "#F1EADA", "museum": "#F2EBDC"}[s["key"]]
        rect(ax, s["x0"], s["y0"], s["x1"] - s["x0"], s["y1"] - s["y0"],
             facecolor=fill, edgecolor="none", zorder=1.8)
        wall_ring(ax, s, D.GATES.get(s["key"], []))


def _shadow(ax, x0, x1, y0, y1):
    rect(ax, x0 + 3, y0 - 3, x1 - x0, y1 - y0, facecolor="#7A6E58",
         edgecolor="none", alpha=0.10, zorder=4.4)


def draw_masses(ax):
    # 大会堂：三厅共用一个外框，内部分间线用虚线
    x0, x1, y0, y1 = -540.0, -340.0, -1100.5, -770.5
    _shadow(ax, x0, x1, y0, y1)
    for m in D.MASSES:
        if m["parent"] != "hall":
            continue
        fc, ec = ((C["hall"], C["hall_edge"]) if m["kind"] == "wing"
                  else (C["chamber"], C["chamber_edge"]) if m["kind"] == "chamber"
                  else (C["portico"], C["portico_edge"]))
        rect(ax, m["x0"], m["y0"], m["x1"] - m["x0"], m["y1"] - m["y0"],
             facecolor=fc, edgecolor=ec, lw=0.35 if m["kind"] == "portico" else 0.5,
             zorder=4.6)
    rect(ax, x0, y0, x1 - x0, y1 - y0, fill=False, edgecolor=C["hall_edge"],
         lw=1.4, zorder=5.0)
    for yy in (-1000.5, -870.5):
        ax.plot([x0, x1], [yy, yy], color=C["hall_edge"], lw=0.7,
                ls=(0, (5, 3)), zorder=5.0)

    # 议事大楼：主楼外框 + 中部议事厅高体量
    _shadow(ax, 310.0, 390.0, -1100.5, -770.5)
    rect(ax, 310.0, -1100.5, 80.0, 330.0, facecolor=C["council"],
         edgecolor=C["hall_edge"], lw=1.2, zorder=4.6)
    rect(ax, 322.0, -985.5, 56.0, 100.0, facecolor=C["chamber"],
         edgecolor=C["chamber_edge"], lw=0.9, zorder=4.9)
    rect(ax, 300.0, -965.5, 12.0, 60.0, facecolor=C["portico"],
         edgecolor=C["portico_edge"], lw=0.6, zorder=4.8)
    rect(ax, 310.0, -1100.5, 80.0, 330.0, fill=False, edgecolor=C["hall_edge"],
         lw=1.2, zorder=5.0)

    # 博物馆：主楼 + 东翼主题馆
    for m in D.MASSES:
        if m["parent"] != "museum":
            continue
        fc, ec = ((C["museum"], C["hall_edge"]) if m["kind"] in ("main", "wing")
                  else (C["portico"], C["portico_edge"]))
        if m["kind"] in ("main", "wing"):
            _shadow(ax, m["x0"], m["x1"], m["y0"], m["y1"])
        rect(ax, m["x0"], m["y0"], m["x1"] - m["x0"], m["y1"] - m["y0"],
             facecolor=fc, edgecolor=ec, lw=1.0 if m["kind"] == "main" else 0.8,
             zorder=4.7)


def draw_labels(ax):
    P = D.PLAZA
    label(ax, 0, -648, "国 家 广 场", fs=16.5, color=C["ink"], box=False)
    label(ax, 0, -680, f'{P["width"]:.0f} × {P["depth"]:.0f} m　│　铺装 {P["paving_ha"]:.0f} ha',
          fs=8.0, color=C["muted"], box=False)
    label(ax, -210, -560, "仪典台区", fs=7.4, color=C["muted"], box=False)

    label(ax, 0, -790, "中轴御道 40 m", fs=7.2, color=C["muted"], rot=90, box=False)
    label(ax, 282, -1160, "广场东侧道 12 m", fs=7.0, color=C["muted"], rot=90, box=False)
    label(ax, 0, -1320, "南端（博物馆前）", fs=7.4, color=C["muted"])

    # 大会堂三厅
    label(ax, -440, -913, "国家大会堂", fs=12.0, box=True)
    label(ax, -440, -935, "20 ha · 三厅", fs=7.8, color=C["muted"])
    label(ax, -440, -962, "中厅", fs=8.6)
    label(ax, -440, -980, "万人大礼堂 10,000 席", fs=7.2)
    label(ax, -440, -1052, "左厅\n八州厅＋宣政厅", fs=7.6)
    label(ax, -440, -818, "右厅\n宴会厅 3,000 席", fs=7.6)

    # 议事大楼
    label(ax, 350, -918, "国家议会\n议事大楼", fs=10.2, box=True)
    label(ax, 350, -948, "8 ha · 1,100 席", fs=7.4, color=C["muted"])
    label(ax, 350, -972, "议事厅", fs=7.4)

    # 博物馆
    label(ax, 0, -1452, "国家政治博物馆", fs=11.5)
    label(ax, 0, -1475, "12 ha · 大革命主题馆", fs=7.8, color=C["muted"])
    label(ax, 202, -1443.5, "大革命\n主题馆", fs=6.8, rot=90)


def draw_axis(ax):
    y0, y1 = D.PLAZA["y_north"], -1372.5
    ax.plot([0, 0], [y0, y1], color=C["axis_red"], lw=0.9,
            ls=(0, (8, 3, 1.5, 3)), zorder=5.5, alpha=0.8)
    ax.annotate("", xy=(0, y1), xytext=(0, y1 + 40),
                arrowprops=dict(arrowstyle="-|>", color=C["axis_red"], lw=1.1), zorder=5.6)


def draw_dims(ax):
    # 底边：250 / 600 / 100
    y = -1595
    for xa, xb, txt in ((-550, -300, "250"), (-300, 300, "600"), (300, 400, "100")):
        ax.annotate("", xy=(xa, y), xytext=(xb, y),
                    arrowprops=dict(arrowstyle="<|-|>", color=C["ink"], lw=0.9,
                                    shrinkA=0, shrinkB=0), zorder=6)
        ax.plot([xa, xa], [y - 6, y + 6], color=C["ink"], lw=0.8, zorder=6)
        ax.text((xa + xb) / 2, y + 9, f"{txt} m", ha="center", va="bottom",
                fontsize=7.6, color=C["ink"], zorder=6)
    ax.plot([400, 400], [y - 6, y + 6], color=C["ink"], lw=0.8, zorder=6)

    # 右侧：800
    x = 455
    ax.annotate("", xy=(x, -535.5), xytext=(x, -1335.5),
                arrowprops=dict(arrowstyle="<|-|>", color=C["ink"], lw=0.9,
                                shrinkA=0, shrinkB=0), zorder=6)
    for yy in (-535.5, -1335.5):
        ax.plot([x - 6, x + 6], [yy, yy], color=C["ink"], lw=0.8, zorder=6)
        ax.plot([400, x + 6], [yy, yy], color=C["ink"], lw=0.35,
                ls=(0, (2, 3)), zorder=5.6)
    ax.text(x + 13, -935.5, "800 m", rotation=90, ha="center", va="center",
            fontsize=8.6, color=C["ink"])

    # 左侧：200（博物馆进深）
    x = -585
    ax.annotate("", xy=(x, -1335.5), xytext=(x, -1535.5),
                arrowprops=dict(arrowstyle="<|-|>", color=C["ink"], lw=0.9,
                                shrinkA=0, shrinkB=0), zorder=6)
    for yy in (-1335.5, -1535.5):
        ax.plot([x - 6, x + 6], [yy, yy], color=C["ink"], lw=0.8, zorder=6)
    ax.text(x - 12, -1435.5, "200 m", rotation=90, ha="center", va="center",
            fontsize=7.8, color=C["ink"])


def draw_north(ax):
    x, y = 395, -470
    ax.annotate("", xy=(x, y + 62), xytext=(x, y),
                arrowprops=dict(arrowstyle="-|>", color=C["ink"], lw=1.4), zorder=9)
    ax.text(x, y + 70, "N", ha="center", va="bottom", fontsize=12,
            color=C["ink"], fontweight="bold", zorder=9)


def draw_scalebar(ax):
    x, y = -600, -1638
    for i in range(4):
        rect(ax, x + i * 50, y, 50, 7,
             facecolor=C["ink"] if i % 2 == 0 else C["paper"],
             edgecolor=C["ink"], lw=0.6, zorder=9)
    for i, t in ((0, "0"), (2, "100"), (4, "200 m")):
        ax.text(x + i * 50, y + 12, t, ha="center", va="bottom", fontsize=6.8,
                color=C["ink"], zorder=9)


# ------------------------------------------------------------------ 侧栏
def draw_panel(ax):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    st = D.stats()

    y = 0.99
    ax.text(0, y, "图　例", fontsize=12.5, color=C["ink"], fontweight="bold", va="top")
    y -= 0.042
    items = [
        ("广场铺装（45 ha）", C["plaza"], C["plaza_edge"]),
        ("仪典台区 / 阅兵台", C["terrace"], C["plaza_edge"]),
        ("御道 · 广场东侧道", C["axis"], "#C9B891"),
        ("国家大会堂（主体 / 中部大礼堂 / 门廊）", C["hall"], C["hall_edge"]),
        ("国家议会议事大楼", C["council"], C["hall_edge"]),
        ("国家政治博物馆", C["museum"], C["hall_edge"]),
        ("建筑群外墙", C["site_edge"], None),
        ("宫城城墙 / 城门", C["wall"], C["wall_edge"]),
        ("护城河", C["water"], C["water_edge"]),
    ]
    for txt, fc, ec in items:
        ax.add_patch(Rectangle((0.0, y - 0.011), 0.085, 0.021, facecolor=fc,
                               edgecolor=ec or fc, lw=0.7, clip_on=False))
        ax.text(0.115, y, txt, fontsize=7.6, va="center", color=C["ink"])
        y -= 0.030

    y -= 0.012
    ax.text(0, y, "占地（本图实测）", fontsize=11.2, color=C["ink"],
            fontweight="bold", va="top")
    y -= 0.030
    rows = [
        ("广场铺装", f'{st["paving_ha"]:.1f} ha'),
        ("仪典台区", f'{st["terrace_ha"]:.1f} ha'),
        ("大会堂（用地 / 建筑）", f'{st["sites"]["hall"]:.1f} / {st["floor_ha"]["hall"]:.1f} ha'),
        ("议事大楼（用地 / 建筑）", f'{st["sites"]["council"]:.1f} / {st["floor_ha"]["council"]:.1f} ha'),
        ("政治博物馆（用地 / 建筑）", f'{st["sites"]["museum"]:.1f} / {st["floor_ha"]["museum"]:.1f} ha'),
    ]
    for name, val in rows:
        ax.text(0.0, y, name, fontsize=7.5, va="center", color=C["ink"])
        ax.text(1.0, y, val, fontsize=7.5, va="center", ha="right", color=C["muted"])
        y -= 0.0255

    y -= 0.014
    ax.text(0, y, "口径", fontsize=11.2, color=C["ink"], fontweight="bold", va="top")
    y -= 0.028
    notes = [
        ("【设定】", "广场东西 600 m、南北 800 m；大会堂三厅（左厅八州厅＋宣政厅、中厅万人\n"
                    "大礼堂、右厅宴会厅）；议事大楼 8 ha、约 1,100 席；博物馆 12 ha。"),
        ("【判读】", "表列广场 45 ha ＝ 600 × 750；北端 50 m（600 × 50＝3 ha）读作仪典台区，\n"
                    "阅兵台设于承天门外。45＋3＝48 ha，与 600 × 800 相合。"),
        ("【推定】", "三块建筑占地（20 / 8 / 12 ha）按「广场两侧带状用地」反推：西 250 m、\n"
                    "东 100 m、南 200 m；单体面宽进深、层数、门廊、外墙、周边道路均为推定。"),
    ]
    for tag, txt in notes:
        ax.text(0.0, y, tag, fontsize=7.2, color=C["axis_red"], va="top", fontweight="bold")
        ax.text(0.11, y, txt, fontsize=6.8, color=C["muted"], va="top", linespacing=1.55)
        y -= 0.038 + 0.028 * txt.count("\n")

    y -= 0.012
    ax.text(0, y, "待　定", fontsize=11.2, color=C["ink"], fontweight="bold", va="top")
    y -= 0.028
    todo = [
        "① 大会堂三厅：设定写「贴靠在中厅东西两侧」，与「面东朝广场」的三厅南北排不合；\n"
        "   本图按面东立面读作右厅（北）—中厅—左厅（南），待作者定。",
        "② 国旗杆：阅兵 09:05 升旗，但设定未给位置；本图暂不画。",
        "③ 内城 2,700 m：广场 800 m＋博物馆 200 m 已 1,000 m，加上皇城 1,950 m 超过 2,700 m；\n"
        "   本模型只做广场建筑群，内城城墙与永宁门不在范围内，口径另核。",
    ]
    for txt in todo:
        ax.text(0.0, y, txt, fontsize=6.7, color=C["muted"], va="top", linespacing=1.55)
        y -= 0.036 + 0.026 * txt.count("\n")


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "..", "..", "docs", "assets"))
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--name", default="国家广场(2026)·总平面图")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if args.check:
        print(D.check())
        return
    os.makedirs(args.out, exist_ok=True)

    fig = plt.figure(figsize=(15.0, 15.6), dpi=args.dpi, facecolor=C["paper"])
    ax = fig.add_axes([0.012, 0.045, 0.665, 0.875])
    ax.set_facecolor(C["ground"])
    ax.set_aspect("equal")
    ax.set_xlim(-650, 480)
    ax.set_ylim(-1665, -405)
    ax.axis("off")

    draw_roads(ax)
    draw_context(ax)
    draw_plaza(ax)
    draw_sites(ax)
    draw_masses(ax)
    draw_labels(ax)
    draw_axis(ax)
    draw_dims(ax)
    draw_north(ax)
    draw_scalebar(ax)

    panel = fig.add_axes([0.696, 0.045, 0.294, 0.875])
    draw_panel(panel)

    fig.text(0.33, 0.972, "国家广场与广场建筑群 · 总平面", ha="center", va="center",
             fontsize=24, color=C["ink"], fontweight="bold")
    fig.text(0.33, 0.950,
             "长安 · 2026　│　广场 600 × 800 m（铺装 45 ha）　│　"
             "大会堂 20 ha · 议事大楼 8 ha · 政治博物馆 12 ha　│　最简稿",
             ha="center", va="center", fontsize=8.6, color=C["muted"])

    fig.text(0.012, 0.016,
             "数据：《长安城市志》卷三·内城表（广场 45 ha、大会堂 20 ha、议事 8 ha、博物馆 12 ha、中轴里程）·"
             "《总设定》第十六编（600 × 800 m、三厅构成、1,100 席）·\n"
             "《继位大典与宫城启闭（草案）》（阅兵台设于承天门外、检阅车走广场东侧道）。"
             "宫城接口（承天门、护城河、城墙）取自 tools/palace/palace_data.py。",
             ha="left", va="bottom", fontsize=6.6, color=C["muted"], linespacing=1.6)
    fig.text(0.978, 0.016, "中华帝国设定集 · 图版", ha="right", va="bottom",
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
