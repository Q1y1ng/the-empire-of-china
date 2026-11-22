"""国家广场与广场建筑群 —— 2D 总平面（最简稿，第二版）。

第二版按作者 2026-11-22 裁决改：
  · 广场 800 m 全铺装（48 ha），不再切 50 m 仪典台区；
  · 阅兵台并入承天门城台，广场内不再单设阅兵台；
  · 承天门前新设东西向主干道「承天门大街」100 m，关系类似长安街与天安门广场；
  · 三座建筑放大：降为两层、加大面宽进深，建筑面积仍落 20 / 8 / 12 ha。

只画「格局」：大街、广场、三组建筑体块、承天门接口、中轴、四至尺寸。
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
from matplotlib.patches import Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import plaza_data as D  # noqa: E402

C = dict(
    paper="#F2EEE4", ground="#E7E1D4", road="#D8D1C2", road_edge="#BDB4A2",
    walk="#E6DDC9", walk_edge="#C9BFA8", median="#C9C0AE",
    plaza="#F0E9D7", plaza_edge="#C8BBA0",
    axis="#DFD0AE", water="#A8C8D8", water_edge="#5B8CA6",
    wall="#9E2B25", wall_edge="#6E1B17", stone="#D9D2C0", stone_edge="#B3A88F",
    hall="#D9C08C", hall_edge="#7E6A42", chamber="#C9A868", chamber_edge="#7A5C22",
    portico="#E8DCC0", portico_edge="#A99772",
    council="#D3B981", museum="#D8C391", site_edge="#6B5B45",
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


# ------------------------------------------------------------------ 承天门大街
def draw_avenue(ax):
    A = D.AVENUE
    # 人行道
    rect(ax, A["x0"], A["y_north"] - A["sidewalk"], A["x1"] - A["x0"], A["sidewalk"],
         facecolor=C["walk"], edgecolor=C["walk_edge"], lw=0.4, zorder=1.6)
    rect(ax, A["x0"], A["y_south"], A["x1"] - A["x0"], A["sidewalk"],
         facecolor=C["walk"], edgecolor=C["walk_edge"], lw=0.4, zorder=1.6)
    # 车行道
    rect(ax, A["x0"], A["y_south"] + A["sidewalk"], A["x1"] - A["x0"],
         A["width"] - 2 * A["sidewalk"], facecolor=C["road"],
         edgecolor=C["road_edge"], lw=0.5, zorder=1.5)
    # 中央分隔带
    yc = (A["y_north"] + A["y_south"]) / 2
    rect(ax, A["x0"], yc - A["median"] / 2, A["x1"] - A["x0"], A["median"],
         facecolor=C["median"], edgecolor="none", zorder=1.7)
    # 车道虚线（每侧两条）
    for dy in (-24.0, -10.5, 10.5, 24.0):
        ax.plot([A["x0"], A["x1"]], [yc + dy, yc + dy], color="#F4EFE3", lw=0.9,
                ls=(0, (14, 12)), zorder=1.8, alpha=0.9)
    # 轴线过街（承天门桥—广场的仪典过街）
    rect(ax, -20.0, A["y_south"], 40.0, A["width"], facecolor=C["stone"],
         edgecolor=C["stone_edge"], lw=0.5, zorder=1.9, alpha=0.95)
    # 两端去向
    ax.text(A["x0"] + 8, yc, "西往安定门", ha="left", va="center", fontsize=6.8,
            color=C["muted"], zorder=8,
            bbox=dict(boxstyle="round,pad=0.18", fc=C["paper"], ec="none", alpha=0.8))
    ax.text(A["x1"] - 8, yc, "东往长乐门", ha="right", va="center", fontsize=6.8,
            color=C["muted"], zorder=8,
            bbox=dict(boxstyle="round,pad=0.18", fc=C["paper"], ec="none", alpha=0.8))
    label(ax, -430, yc, f'承天门大街 {A["width"]:.0f} m（新设）', fs=9.4, color=C["ink"])


# ------------------------------------------------------------------ 底图
def draw_context(ax):
    # 宫城地坪：只留墙内 40 m 的一条
    P = D.PALACE
    hw = P["width"] / 2
    rect(ax, -hw - 3, -477.5, 2 * (hw + 3), 70,
         facecolor="#EFE7D6", edgecolor="none", zorder=1.0)
    # 护城河南带
    mo = P["south_wall_outer"]
    bank = P["moat_bank_south"]
    rect(ax, -hw - 55, bank, 2 * (hw + 55), mo - bank,
         facecolor=C["water"], edgecolor=C["water_edge"], lw=0.7, zorder=2.2)
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
    # 城台上的阅兵台
    r = D.FEATURES["review"]
    rect(ax, r["x0"], r["y0"], r["x1"] - r["x0"], r["y1"] - r["y0"],
         facecolor="#7A1D18", edgecolor=C["wall_edge"], lw=0.5, zorder=3.6)
    # 跨护城河石桥（压在大街北侧人行道上）
    b = D.FEATURES["bridge"]
    rect(ax, b["x0"], b["y0"], b["x1"] - b["x0"], b["y1"] - b["y0"],
         facecolor=C["stone"], edgecolor=C["stone_edge"], lw=0.6, zorder=2.8)
    for x in (-34, 34):
        ax.plot([x, x], [b["y0"], b["y1"]], color=C["stone_edge"], lw=0.5, zorder=2.9)

    ax.text(0, -443, "承天门 · 阅兵台", ha="center", va="bottom", fontsize=10.2,
            color=C["ink"], zorder=9,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))
    ax.text(-262, -440, "宫城（皇宫）南墙", ha="center", va="bottom", fontsize=8.0,
            color=C["muted"], zorder=9,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.8))


def draw_roads(ax):
    for r in D.ROADS:
        rect(ax, r["x0"], r["y0"], r["x1"] - r["x0"], r["y1"] - r["y0"],
             facecolor=C["road"], edgecolor=C["road_edge"], lw=0.45, zorder=1.5)


def draw_plaza(ax):
    P = D.PLAZA
    rect(ax, P["x0"], P["y_south"], P["width"], P["depth"],
         facecolor=C["plaza"], edgecolor=C["plaza_edge"], lw=0.7, zorder=2.0)
    # 50 m 铺装网格（极淡）
    y = P["y_south"] + 50
    while y < P["y_north"] - 1:
        ax.plot([P["x0"], P["x1"]], [y, y], color=C["plaza_edge"], lw=0.25,
                alpha=0.30, zorder=2.1)
        y += 50
    for x in range(-250, 300, 50):
        ax.plot([x, x], [P["y_south"], P["y_north"]],
                color=C["plaza_edge"], lw=0.25, alpha=0.30, zorder=2.1)

    a = D.FEATURES["axis_road"]
    rect(ax, a["x0"], a["y0"], a["x1"] - a["x0"], a["y1"] - a["y0"],
         facecolor=C["axis"], edgecolor="none", zorder=2.2)
    e = D.FEATURES["east_road"]
    rect(ax, e["x0"], e["y0"], e["x1"] - e["x0"], e["y1"] - e["y0"],
         facecolor="#E3D8BF", edgecolor="none", zorder=2.2)


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
        fill = {"hall": "#F5EFE1", "council": "#F4EEDF", "museum": "#F5EFE1"}[s["key"]]
        rect(ax, s["x0"], s["y0"], s["x1"] - s["x0"], s["y1"] - s["y0"],
             facecolor=fill, edgecolor="none", zorder=1.8)
        wall_ring(ax, s, D.GATES.get(s["key"], []))


def _shadow(ax, x0, x1, y0, y1):
    rect(ax, x0 + 3, y0 - 3, x1 - x0, y1 - y0, facecolor="#7A6E58",
         edgecolor="none", alpha=0.10, zorder=4.4)


def draw_masses(ax):
    # 大会堂：230 × 600 m 三段式，南北镜像
    x0, x1, y0, y1 = -540.0, -310.0, -1335.5, -735.5
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
    for yy in (-1155.5, -915.5):
        ax.plot([x0, x1], [yy, yy], color=C["hall_edge"], lw=0.7,
                ls=(0, (5, 3)), zorder=5.0)

    # 议事大楼：同尺寸 230 × 600 m 三段式，与大会堂隔广场镜像
    x0, x1 = 310.0, 540.0
    _shadow(ax, x0, x1, y0, y1)
    for m in D.MASSES:
        if m["parent"] != "council":
            continue
        fc, ec = ((C["council"], C["hall_edge"]) if m["kind"] == "wing"
                  else (C["chamber"], C["chamber_edge"]) if m["kind"] == "chamber"
                  else (C["portico"], C["portico_edge"]))
        rect(ax, m["x0"], m["y0"], m["x1"] - m["x0"], m["y1"] - m["y0"],
             facecolor=fc, edgecolor=ec, lw=0.35 if m["kind"] == "portico" else 0.5,
             zorder=4.6)
    rect(ax, x0, y0, x1 - x0, y1 - y0, fill=False, edgecolor=C["hall_edge"],
         lw=1.4, zorder=5.0)
    for yy in (-1155.5, -915.5):
        ax.plot([x0, x1], [yy, yy], color=C["hall_edge"], lw=0.7,
                ls=(0, (5, 3)), zorder=5.0)

    # 博物馆：560 × 170 m，一整块，门廊居中
    _shadow(ax, -280.0, 280.0, -1620.5, -1450.5)
    rect(ax, -280.0, -1620.5, 560.0, 170.0, facecolor=C["museum"],
         edgecolor=C["hall_edge"], lw=1.2, zorder=4.6)
    rect(ax, -70.0, -1450.5, 140.0, 15.0, facecolor=C["portico"],
         edgecolor=C["portico_edge"], lw=0.6, zorder=4.7)


def draw_labels(ax):
    P = D.PLAZA
    label(ax, 0, -700, "国 家 广 场", fs=16.5, color=C["ink"], box=False)
    label(ax, 0, -732, f'{P["width"]:.0f} × {P["depth"]:.0f} m　│　{P["area_ha"]:.0f} ha 全铺装',
          fs=8.2, color=C["muted"], box=False)

    label(ax, 32, -1180, "中轴御道 40 m", fs=7.2, color=C["muted"], rot=90, box=False)
    label(ax, 282, -1180, "广场东侧道 12 m", fs=7.0, color=C["muted"], rot=90, box=False)
    label(ax, 0, -1422, "南端（博物馆前）", fs=7.2, color=C["muted"])

    # 大会堂（西，230×600）
    label(ax, -425, -724, "国家大会堂", fs=11.8, box=True)
    label(ax, -425, -825.5, "右厅\n宴会厅 3,000 席", fs=8.0)
    label(ax, -425, -1035.5, "中厅\n万人大礼堂 10,000 席", fs=8.2)
    label(ax, -425, -1245.5, "左厅\n八州厅＋宣政厅", fs=8.0)

    # 议事大楼（东，与大会堂镜像同大）
    label(ax, 425, -724, "国家议会议事大楼", fs=9.8, box=True)
    label(ax, 425, -825.5, "北翼", fs=8.0)
    label(ax, 425, -1035.5, "议事厅\n1,100 席", fs=8.2)
    label(ax, 425, -1245.5, "南翼", fs=8.0)

    # 博物馆
    label(ax, 0, -1535, "国家政治博物馆", fs=11.5)
    label(ax, 0, -1558, "560 × 170 m · 两层", fs=7.6, color=C["muted"])
    label(ax, 195, -1535, "大革命\n主题馆", fs=6.8, rot=90)


def draw_axis(ax):
    y0, y1 = -443.0, -1435.5
    ax.plot([0, 0], [y0, y1], color=C["axis_red"], lw=0.9,
            ls=(0, (8, 3, 1.5, 3)), zorder=5.5, alpha=0.8)
    ax.annotate("", xy=(0, -1435.5), xytext=(0, -1395.5),
                arrowprops=dict(arrowstyle="-|>", color=C["axis_red"], lw=1.1), zorder=5.6)


def draw_dims(ax):
    # 底边：250 / 600 / 250
    y = -1700
    for xa, xb, txt in ((-550, -300, "250"), (-300, 300, "600"), (300, 550, "250")):
        ax.annotate("", xy=(xa, y), xytext=(xb, y),
                    arrowprops=dict(arrowstyle="<|-|>", color=C["ink"], lw=0.9,
                                    shrinkA=0, shrinkB=0), zorder=6)
        ax.plot([xa, xa], [y - 6, y + 6], color=C["ink"], lw=0.8, zorder=6)
        ax.text((xa + xb) / 2, y + 9, f"{txt} m", ha="center", va="bottom",
                fontsize=7.6, color=C["ink"], zorder=6)
    ax.plot([550, 550], [y - 6, y + 6], color=C["ink"], lw=0.8, zorder=6)

    # 右侧：广场 800
    x = 600
    ax.annotate("", xy=(x, -635.5), xytext=(x, -1435.5),
                arrowprops=dict(arrowstyle="<|-|>", color=C["ink"], lw=0.9,
                                shrinkA=0, shrinkB=0), zorder=6)
    for yy in (-635.5, -1435.5):
        ax.plot([x - 6, x + 6], [yy, yy], color=C["ink"], lw=0.8, zorder=6)
        ax.plot([550, x + 6], [yy, yy], color=C["ink"], lw=0.35,
                ls=(0, (2, 3)), zorder=5.6)
    ax.text(x + 13, -1035.5, "800 m", rotation=90, ha="center", va="center",
            fontsize=8.6, color=C["ink"])

    # 左侧：博物馆进深 200
    x = -620
    ax.annotate("", xy=(x, -1435.5), xytext=(x, -1635.5),
                arrowprops=dict(arrowstyle="<|-|>", color=C["ink"], lw=0.9,
                                shrinkA=0, shrinkB=0), zorder=6)
    for yy in (-1435.5, -1635.5):
        ax.plot([x - 6, x + 6], [yy, yy], color=C["ink"], lw=0.8, zorder=6)
    ax.text(x - 12, -1535.5, "200 m", rotation=90, ha="center", va="center",
            fontsize=7.8, color=C["ink"])


def draw_north(ax):
    x, y = 520, -470
    ax.annotate("", xy=(x, y + 62), xytext=(x, y),
                arrowprops=dict(arrowstyle="-|>", color=C["ink"], lw=1.4), zorder=9)
    ax.text(x, y + 70, "N", ha="center", va="bottom", fontsize=12,
            color=C["ink"], fontweight="bold", zorder=9)


def draw_scalebar(ax):
    x, y = -690, -1755
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

    def head(text, y):
        ax.text(0, y, text, fontsize=11.0, color=C["ink"], fontweight="bold", va="top")
        return y - 0.034

    # ── 图例
    y = head("图　例", 0.99)
    items = [
        ("广场铺装（48 ha）", C["plaza"], C["plaza_edge"]),
        ("承天门大街（新设）", C["road"], C["road_edge"]),
        ("大街人行道 / 中央分隔带", C["walk"], C["walk_edge"]),
        ("御道 · 广场东侧道", C["axis"], "#C9B891"),
        ("国家大会堂", C["hall"], C["hall_edge"]),
        ("国家议会议事大楼", C["council"], C["hall_edge"]),
        ("国家政治博物馆", C["museum"], C["hall_edge"]),
        ("建筑群外墙", C["site_edge"], None),
        ("宫城城墙 / 城门", C["wall"], C["wall_edge"]),
        ("护城河", C["water"], C["water_edge"]),
    ]
    for txt, fc, ec in items:
        ax.add_patch(Rectangle((0.0, y - 0.008), 0.070, 0.016, facecolor=fc,
                               edgecolor=ec or fc, lw=0.6, clip_on=False))
        ax.text(0.095, y, txt, fontsize=7.8, va="center", color=C["ink"])
        y -= 0.0238

    # ── 占地
    y = head("占地（本图实测）", y - 0.014)
    rows = [
        ("广场铺装", f'{st["plaza_ha"]:.1f} ha'),
        ("大会堂（用地 / 建筑）", f'{st["sites"]["hall"]:.1f} / {st["floor_ha"]["hall"]:.1f} ha'),
        ("议事大楼（用地 / 建筑）", f'{st["sites"]["council"]:.1f} / {st["floor_ha"]["council"]:.1f} ha'),
        ("政治博物馆（用地 / 建筑）", f'{st["sites"]["museum"]:.1f} / {st["floor_ha"]["museum"]:.1f} ha'),
        ("承天门大街", f'{D.AVENUE["width"]:.0f} m 宽'),
    ]
    for name, val in rows:
        ax.text(0.0, y, name, fontsize=7.8, va="center", color=C["ink"])
        ax.text(1.0, y, val, fontsize=7.8, va="center", ha="right", color=C["muted"])
        y -= 0.0225
    ax.text(0.0, y, "两楼同 230 × 600 m、镜像对称；原设定 20 / 8 / 12 ha 待重定。",
            fontsize=6.8, color=C["muted"], va="center")
    y -= 0.0225

    # ── 三厅与两馆
    y = head("三厅与两馆", y - 0.014)
    for name, val in [
        ("左厅", "八州厅 8 间 · 宣政厅 140 席"),
        ("中厅", "无立柱万人大礼堂 10,000 席"),
        ("右厅", "无立柱宴会厅 3,000 席"),
        ("议事大楼", "议事厅 1,100 席（与大会堂同大）"),
        ("政治博物馆", "大革命主题馆（东段）"),
    ]:
        ax.text(0.0, y, name, fontsize=7.8, va="center", color=C["ink"])
        ax.text(0.30, y, val, fontsize=7.6, va="center", color=C["muted"])
        y -= 0.0225

    # ── 口径
    y = head("口径", y - 0.014)
    lh = 0.0132
    blocks = [
        ("【设定】", [
            "广场 600 × 800 m；大会堂三厅；议事大楼约 1,100 席；",
            "政治博物馆 12 ha、内设大革命主题馆；表列广场 45 ha。",
        ]),
        ("【作者】", [
            "2026-11-22 裁决：800 m 全铺装（48 ha）；阅兵台并入承天门；",
            "门前新设 100 m 大街；两楼对称同大、三座主体占满区块。",
        ]),
        ("【判读】", [
            "两楼同为 230 × 600 m（占地 13.8 ha，两层）；博物馆 560 × 170 m；",
            "原 20 / 8 / 12 ha 建筑面积控制随「对称」调整，待重定。",
        ]),
        ("【推定】", [
            "门廊、围墙、道路、大街断面（8 m 人行道＋84 m 车行道）为推定。",
        ]),
    ]
    for tag, lines in blocks:
        ax.text(0.0, y, tag, fontsize=7.3, color=C["axis_red"], va="top", fontweight="bold")
        for ln in lines:
            ax.text(0.105, y, ln, fontsize=7.1, color=C["muted"], va="top")
            y -= lh
        y -= 0.006

    # ── 待定
    y = head("待　定", y - 0.012)
    for ln in [
        "① 对称后两楼同大：原设定大会堂 20 ha、议事 8 ha 不再适用，",
        "   两楼占地 13.8 ha、建筑约 27.6 ha；是否按此改设定表。",
        "② 广场 45 ha → 48 ha：是否同步改《长安城市志》内城表。",
        "③ 国旗杆：阅兵 09:05 升旗，设定未给位置；本图暂不画。",
        "④ 大街名称：暂作「承天门大街」，是否另有正式地名。",
        "⑤ 内城 2,700 m：广场 800 m＋博物馆 200 m 已 1,000 m，加皇城",
        "   1,950 m 超过 2,700 m；本模型不含内城城墙与永宁门。",
    ]:
        ax.text(0.0, y, ln, fontsize=7.0, color=C["muted"], va="top")
        y -= lh

    ax.text(0.0, y - 0.012,
            "本图只定格局；立面、屋顶、铺装与构件见后续白模、精模。",
            fontsize=6.9, color=C["muted"], va="top")


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

    fig = plt.figure(figsize=(15.6, 16.2), dpi=args.dpi, facecolor=C["paper"])
    ax = fig.add_axes([0.010, 0.043, 0.665, 0.878])
    ax.set_facecolor(C["ground"])
    ax.set_aspect("equal")
    ax.set_xlim(-720, 640)
    ax.set_ylim(-1775, -405)
    ax.axis("off")

    draw_roads(ax)
    draw_plaza(ax)
    draw_sites(ax)
    draw_masses(ax)
    draw_context(ax)
    draw_avenue(ax)
    draw_labels(ax)
    draw_axis(ax)
    draw_dims(ax)
    draw_north(ax)
    draw_scalebar(ax)

    panel = fig.add_axes([0.694, 0.043, 0.296, 0.878])
    draw_panel(panel)

    fig.text(0.33, 0.972, "国家广场与广场建筑群 · 总平面", ha="center", va="center",
             fontsize=24, color=C["ink"], fontweight="bold")
    fig.text(0.33, 0.950,
             "长安 · 2026　│　广场 600 × 800 m（48 ha）　│　承天门大街 100 m（新设）　│　"
             "大会堂 · 议事大楼 230 × 600 m（对称）　│　博物馆 560 × 170 m　│　最简稿",
             ha="center", va="center", fontsize=8.2, color=C["muted"])

    fig.text(0.010, 0.015,
             "数据：《长安城市志》卷三·内城表（广场、大会堂、议事、博物馆、中轴里程）·"
             "《总设定》第十六编（600×800 m、三厅、1,100 席）·《继位大典与宫城启闭（草案）》（阅兵、检阅车东侧道）。\n"
             "2026-11-22 作者裁决：800 m 全铺装（48 ha）；阅兵台并入承天门城台；承天门前新设 100 m 东西向大街；两楼对称同大、三座主体占满区块。"
             "宫城接口（承天门、护城河、城墙）取自 tools/palace/palace_data.py。",
             ha="left", va="bottom", fontsize=6.6, color=C["muted"], linespacing=1.6)
    fig.text(0.980, 0.015, "中华帝国设定集 · 图版", ha="right", va="bottom",
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
