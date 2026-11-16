# -*- coding: utf-8 -*-
"""Render the 45-province atlas plate (v1)."""
import pickle
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import numpy as np
from matplotlib.font_manager import FontProperties
from matplotlib.patches import PathPatch, Rectangle, Polygon as MplPolygon
from matplotlib.path import Path
from shapely.geometry import MultiLineString, MultiPolygon, Polygon, LineString
from shapely.ops import polylabel, unary_union

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from prep_empire_map import TR  # noqa: E402
from prep_empire_provinces import PROV  # noqa: E402

PICKLE = r"C:\Users\s3431\AppData\Local\Temp\empire-map\prepared_provinces.pkl"
OUT = r"C:\Users\s3431\AppData\Local\Temp\empire-map\empire_provinces.png"

F_KAI = FontProperties(fname=r"C:\Windows\Fonts\simkai.ttf")
F_HEI = FontProperties(fname=r"C:\Windows\Fonts\simhei.ttf")
F_SONG = FontProperties(fname=r"C:\Windows\Fonts\simsun.ttc")
F_STK = FontProperties(fname=r"C:\Windows\Fonts\STKAITI.TTF")

PAPER = "#E8DDC4"
INK = "#33261A"
OCEAN = "#1E4A63"
NEIGH = "#D2C7AC"
NEIGH_EDGE = "#BFB094"

COLORS = {
    "京畿": "#BE5A4E",
    "华北": "#D0AC5C",
    "东北": "#7C9966",
    "蒙古": "#C4A87C",
    "西北": "#9277A8",
    "江南": "#5D8AA3",
    "云贵": "#5C9C88",
    "青藏": "#AEC0CD",
}
LABELS = {
    "京畿": "京畿直隶州",
    "华北": "华北州",
    "东北": "东北州",
    "蒙古": "蒙古州",
    "西北": "西北州",
    "江南": "江南州",
    "云贵": "云贵州",
    "青藏": "青藏州",
}
TERRAIN_COLORS = {
    "Range/mtn": ("#6F5338", 0.09),
    "Desert": ("#D2B36B", 0.13),
    "Basin": ("#6F7F5C", 0.04),
}

# 省会标注偏移（点）：名称太长或地物太密的手工微调
CAP_OFF = {
    "长安": (7, 6, "left"),
    "延安": (-7, -4, "right"),
    "成都": (-8, -6, "right"),
    "重庆": (8, -7, "left"),
    "洛阳": (7, 5, "left"),
    "沈阳": (8, 4, "left"),
    "长春": (8, 3, "left"),
    "哈尔滨": (8, 3, "left"),
    "海参崴": (-6, -10, "right"),
    "平壤": (-7, -3, "right"),
    "呼和浩特": (0, 9, "center"),
    "包头": (-6, -8, "right"),
    "乌兰巴托": (7, 3, "left"),
    "科布多": (7, 3, "left"),
    "乌列盖": (6, -4, "left"),
    "肃州": (7, 3, "left"),
    "兰州": (7, -6, "left"),
    "乌鲁木齐": (7, 4, "left"),
    "喀什": (7, 3, "left"),
    "北京": (-8, 4, "right"),
    "太原": (7, 3, "left"),
    "济南": (7, 3, "left"),
    "郑州": (7, -7, "left"),
    "大连": (7, 3, "left"),
    "天津": (8, 2, "left"),
    "上海": (10, -2, "left"),
    "南京": (7, -6, "left"),
    "杭州": (7, -6, "left"),
    "合肥": (-7, 4, "right"),
    "南昌": (7, -5, "left"),
    "福州": (7, -2, "left"),
    "台北": (7, 2, "left"),
    "广州": (7, -4, "left"),
    "昆明": (-7, -5, "right"),
    "贵阳": (6, -5, "left"),
    "桂林": (7, 2, "left"),
    "南宁": (7, -5, "left"),
    "河内": (7, -3, "left"),
    "万象": (6, -4, "left"),
    "海口": (8, 2, "left"),
    "西宁": (7, 3, "left"),
    "拉萨": (-7, -5, "right"),
    "泽当": (6, -6, "left"),
    "昌都": (6, 3, "left"),
    "日喀则": (-6, -6, "right"),
}

# 省名标注位置（经纬度）手工覆盖
NAME_POS = {
    "长安市": (108.60, 34.10),
    "陕西省": (109.70, 37.10),
    "成都省": (104.60, 31.60),
    "重庆省": (107.60, 29.90),
    "中原省": (111.60, 33.30),
    "辽宁": (123.20, 42.60),
    "吉林": (126.00, 44.00),
    "黑龙江": (127.60, 47.60),
    "滨海": (133.50, 47.00),
    "朝鲜": (127.30, 38.70),
    "漠南": (114.20, 42.60),
    "河套": (108.80, 40.20),
    "漠北": (105.50, 46.80),
    "科布多": (93.00, 49.20),
    "阿尔泰": (89.60, 47.60),
    "河西": (99.20, 39.60),
    "甘宁": (105.30, 35.60),
    "新疆": (84.50, 43.20),
    "帕米尔": (78.20, 38.60),
    "河北": (115.30, 38.90),
    "山西": (112.30, 37.60),
    "山东": (118.30, 36.40),
    "河南": (114.60, 34.10),
    "辽南": (121.90, 39.30),
    "北海": (118.60, 38.60),
    "上海": (122.60, 31.10),
    "江苏": (119.60, 33.10),
    "浙江": (120.20, 29.10),
    "安徽": (117.40, 31.30),
    "江西": (115.60, 27.60),
    "福建": (117.80, 26.20),
    "台湾": (121.00, 23.90),
    "岭南": (113.60, 23.90),
    "云南": (101.60, 25.20),
    "贵州": (107.20, 26.60),
    "广西": (109.60, 24.60),
    "南宁": (107.60, 22.60),
    "河内": (105.90, 20.40),
    "澜沧": (102.80, 18.80),
    "北部湾": (110.00, 19.60),
    "青海": (96.50, 35.60),
    "西藏": (87.60, 31.60),
    "藏南": (93.60, 28.60),
    "康巴": (98.60, 30.30),
    "喜马拉雅": (86.60, 28.30),
}


def blend(hex_color, other="#FFFFFF", t=0.12):
    a = np.array([int(hex_color[i:i + 2], 16) for i in (1, 3, 5)], float)
    b = np.array([int(other[i:i + 2], 16) for i in (1, 3, 5)], float)
    c = a + (b - a) * t
    return "#%02X%02X%02X" % tuple(int(round(v)) for v in c)


def add_polygon(verts, codes, poly):
    ext = np.asarray(poly.exterior.coords)
    if len(ext) < 3:
        return
    verts.extend(ext.tolist())
    codes.extend([Path.MOVETO] + [Path.LINETO] * (len(ext) - 2) + [Path.CLOSEPOLY])
    for ring in poly.interiors:
        r = np.asarray(ring.coords)
        if len(r) < 3:
            continue
        verts.extend(r.tolist())
        codes.extend([Path.MOVETO] + [Path.LINETO] * (len(r) - 2) + [Path.CLOSEPOLY])


def geom_path(geom):
    verts, codes = [], []
    if isinstance(geom, Polygon):
        add_polygon(verts, codes, geom)
    elif isinstance(geom, MultiPolygon):
        for p in geom.geoms:
            add_polygon(verts, codes, p)
    if not verts:
        return None
    return Path(np.asarray(verts), np.asarray(codes))


def add_geom(ax, geom, **kw):
    path = geom_path(geom)
    if path is None:
        return None
    patch = PathPatch(path, **kw)
    ax.add_patch(patch)
    return patch


def line_segments(geom):
    if isinstance(geom, LineString):
        return [np.asarray(geom.coords)]
    if isinstance(geom, MultiLineString):
        return [np.asarray(g.coords) for g in geom.geoms]
    if hasattr(geom, "geoms"):
        out = []
        for g in geom.geoms:
            out.extend(line_segments(g))
        return out
    return []


def map_xy(lon, lat):
    return TR.transform(lon, lat)


def big_part(g):
    if hasattr(g, "geoms"):
        return max(g.geoms, key=lambda p: p.area)
    return g


def main():
    d = pickle.load(open(PICKLE, "rb"))
    provs = d["provinces"]
    fig = plt.figure(figsize=(18, 12), dpi=300)
    fig.patch.set_facecolor(PAPER)

    ax = fig.add_axes([0.008, 0.014, 0.734, 0.972])
    ax.set_facecolor(OCEAN)
    ax.set_xticks([])
    ax.set_yticks([])
    x0, x1 = -4250e3, 4360e3
    y0, y1 = -3800e3, 3970e3
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal", adjustable="box")
    for s in ax.spines.values():
        s.set_color(INK)
        s.set_linewidth(1.8)

    for lon in range(50, 181, 10):
        lats = np.linspace(-10, 75, 260)
        xs, ys = TR.transform(np.full_like(lats, lon), lats)
        ax.plot(xs, ys, color="#5D8499", lw=0.25, alpha=0.12, zorder=1)
    for lat in range(0, 71, 10):
        lons = np.linspace(30, 190, 360)
        xs, ys = TR.transform(lons, np.full_like(lons, lat))
        ax.plot(xs, ys, color="#5D8499", lw=0.25, alpha=0.12, zorder=1)

    scs = unary_union([g for nm, zh, g in d["islands"]
                       if nm in ("Paracel Islands", "Spratly Islands")]).buffer(15000)
    add_geom(ax, d["neighbours"].difference(scs), facecolor=NEIGH,
             edgecolor=NEIGH_EDGE, linewidth=0.35, zorder=2)

    # provinces: state colour, alternate tint so neighbours separate
    order = {}
    for name, (st, _c, _x, _y) in PROV.items():
        order.setdefault(st, []).append(name)
    shade = {}
    for st, names in order.items():
        names.sort(key=lambda n: -provs[n].area)
        for i, n in enumerate(names):
            shade[n] = COLORS[st] if i % 2 == 0 else blend(COLORS[st], t=0.16)
        for n in names:
            add_geom(ax, provs[n], facecolor=shade[n], edgecolor="none", zorder=3)

    for cls, name, g in d["terrain"]:
        if cls not in TERRAIN_COLORS:
            continue
        col, alpha = TERRAIN_COLORS[cls]
        add_geom(ax, g, facecolor=col, edgecolor="none", alpha=alpha, zorder=4)

    empire = d["empire"]
    n_lakes = n_riv = 0
    for name, g in d["lakes"]:
        if g.area < 800e6 or not g.intersects(empire):
            continue
        add_geom(ax, g, facecolor="#2E6A86", edgecolor="#1B4257", linewidth=0.3, zorder=5)
        n_lakes += 1
    for name, g in d["rivers"]:
        if g.length < 500e3 or not g.intersects(empire):
            continue
        for seg in line_segments(g):
            ax.plot(seg[:, 0], seg[:, 1], color="#2E6C8A", lw=0.35, alpha=0.45, zorder=5)
        n_riv += 1
    print("lakes", n_lakes, "rivers", n_riv)

    # province borders (paper-coloured hairlines)
    for name, g in provs.items():
        b = g.boundary.intersection(empire.buffer(-2000)).simplify(2000)
        for seg in line_segments(b):
            ax.plot(seg[:, 0], seg[:, 1], color="#F7EEDA", lw=0.85, alpha=0.95, zorder=6)

    # state borders dashed
    for st, g in d["states"].items():
        b = g.boundary.intersection(empire.buffer(-2500)).simplify(2500)
        for seg in line_segments(b):
            ax.plot(seg[:, 0], seg[:, 1], color="#3A2A1A", lw=0.9,
                    ls=(0, (4, 2)), zorder=7, alpha=0.85)

    for seg in line_segments(empire.boundary):
        ax.plot(seg[:, 0], seg[:, 1], color="#F2E7CE", lw=4.5, alpha=0.18, zorder=7)
        ax.plot(seg[:, 0], seg[:, 1], color=INK, lw=1.9, zorder=8)

    for g in d["okinawa"]:
        add_geom(ax, g, facecolor="#DDD2B8", edgecolor="#8A7A60", linewidth=0.35, zorder=6)

    for nm, zh, g in d["islands"]:
        if nm not in ("Paracel Islands", "Spratly Islands"):
            continue
        polys = list(g.geoms) if hasattr(g, "geoms") else [g]
        polys.sort(key=lambda p: p.area, reverse=True)
        for p in polys[:3]:
            c = p.centroid
            ax.scatter([c.x], [c.y], s=12, c="#2F4A3C", edgecolors="#F0E5CC",
                       linewidths=0.35, zorder=9)
        x, y = map_xy(112.3, 16.4) if nm == "Paracel Islands" else map_xy(114.6, 9.6)
        ax.text(x, y, "西沙群岛" if nm == "Paracel Islands" else "南沙群岛",
                fontproperties=F_SONG, fontsize=7, color="#3E3122", ha="center",
                va="center", zorder=10,
                path_effects=[pe.withStroke(linewidth=2.2, foreground="#EFE5CF", alpha=0.85)])

    # province labels
    for name, (st, cap, _x, _y) in PROV.items():
        if name in NAME_POS:
            lon, lat = NAME_POS[name]
        else:
            p = big_part(provs[name])
            lon, lat = polylabel(p, tolerance=8000).coords[0]
        x, y = map_xy(lon, lat)
        fs = 6.2 if name in ("上海", "长安市", "辽南", "台湾") else 9.6
        ax.text(x, y, name, fontproperties=F_KAI, fontsize=fs, color="#241A10",
                ha="center", va="center", zorder=12,
                path_effects=[pe.withStroke(linewidth=3.0, foreground="#F6ECD6", alpha=0.92)])

    # capitals
    for name, (st, cap, lon, lat) in PROV.items():
        x, y = map_xy(lon, lat)
        if name == "长安市":
            ax.scatter([x], [y], marker="*", s=340, c="#A61C26", edgecolors="white",
                       linewidths=0.8, zorder=13)
        else:
            ax.scatter([x], [y], marker="o", s=26, c="#A61C26", edgecolors="white",
                       linewidths=0.5, zorder=13)
        dx, dy, ha = CAP_OFF.get(cap, (6, 4, "left"))
        ax.annotate(cap, (x, y), xytext=(dx, dy), textcoords="offset points",
                    fontproperties=F_SONG, fontsize=7.6, color="#241A12", ha=ha,
                    va="center", zorder=14,
                    path_effects=[pe.withStroke(linewidth=2.4, foreground="#F6ECD6", alpha=0.92)])

    geo = [
        ("贝加尔湖", 106.8, 54.0, 7.6),
        ("巴尔喀什湖", 73.8, 46.4, 7.6),
        ("天山", 82.0, 42.2, 7.6),
        ("昆仑山", 86.0, 36.5, 7.4),
        ("喜马拉雅山", 87.0, 27.9, 7.4),
        ("帕米尔高原", 73.6, 38.9, 7.2),
        ("兴都库什山", 69.6, 35.9, 7.2),
        ("阿尔泰山", 90.6, 47.9, 7.2),
        ("大兴安岭", 122.0, 50.2, 7.2),
        ("外兴安岭", 127.5, 56.4, 7.2),
        ("塔里木盆地", 84.6, 38.6, 7.2),
        ("准噶尔盆地", 86.0, 45.0, 7.2),
        ("河西走廊", 100.5, 39.2, 6.8),
        ("朝鲜半岛", 126.2, 37.0, 7.2),
        ("库页岛", 143.0, 51.0, 7.4),
        ("琉球群岛", 127.6, 27.0, 6.8),
        ("曾母暗沙", 112.3, 4.6, 6.8),
    ]
    for txt, lon, lat, fs in geo:
        x, y = map_xy(lon, lat)
        ax.text(x, y, txt, fontproperties=F_SONG, fontsize=fs, color="#3E3122",
                ha="center", va="center", zorder=11, alpha=0.95,
                path_effects=[pe.withStroke(linewidth=2.2, foreground="#EFE5CF", alpha=0.8)])

    seas = [
        ("渤　海", 119.8, 38.4, 8.2),
        ("黄　海", 123.8, 34.6, 9.6),
        ("东　海", 125.8, 28.0, 9.6),
        ("南　海", 113.5, 14.6, 10.6),
        ("日本海", 135.4, 41.6, 8.8),
        ("鄂霍次克海", 147.0, 53.6, 8.0),
    ]
    for txt, lon, lat, fs in seas:
        x, y = map_xy(lon, lat)
        ax.text(x, y, txt, fontproperties=F_KAI, fontsize=fs, color="#9FC3D6",
                ha="center", va="center", zorder=10, alpha=0.85)

    for txt, lon, lat in [("苏联共同体", 99.0, 61.0), ("印　度", 76.5, 21.0),
                          ("日　本", 139.5, 37.0), ("蒙　古", 0, 0)]:
        if txt == "蒙　古":
            continue
        x, y = map_xy(lon, lat)
        ax.text(x, y, txt, fontproperties=F_SONG, fontsize=8.0, color="#8B7E68",
                ha="center", va="center", zorder=9, alpha=0.9)

    # scale bar
    sx, sy = -4020e3, -3310e3
    seg = 400e3
    for i in range(3):
        ax.add_patch(Rectangle((sx + i * seg, sy), seg, 42e3,
                               facecolor=INK if i % 2 == 0 else "#EFE4CC",
                               edgecolor=INK, lw=0.5, zorder=15))
    for i, lab in enumerate(["0", "400", "800", "1200"]):
        ax.text(sx + i * seg, sy + 55e3, lab, fontproperties=F_SONG, fontsize=7.2,
                color=INK, ha="center", va="bottom", zorder=15)
    ax.text(sx + 1.5 * seg, sy - 48e3, "公里", fontproperties=F_SONG, fontsize=6.6,
            color=INK, ha="center", va="top", zorder=15)

    # compass
    cx, cy = 3860e3, 3340e3
    ax.add_patch(MplPolygon([[cx, cy + 240e3], [cx - 70e3, cy - 90e3],
                             [cx, cy - 22e3], [cx + 70e3, cy - 90e3]],
                            closed=True, facecolor="#A61C26", edgecolor=INK, lw=0.7, zorder=15))
    ax.add_patch(MplPolygon([[cx, cy + 240e3], [cx, cy - 22e3], [cx - 70e3, cy - 90e3]],
                            closed=True, facecolor="#6E1A1E", edgecolor=INK, lw=0.7, zorder=15))
    ax.text(cx, cy + 300e3, "北", fontproperties=F_KAI, fontsize=9.2, color=INK,
            ha="center", va="bottom", zorder=15)

    # ---------- panel ----------
    panel = fig.add_axes([0.750, 0.014, 0.242, 0.972])
    panel.set_xlim(0, 1)
    panel.set_ylim(0, 1)
    panel.set_xticks([])
    panel.set_yticks([])
    panel.set_facecolor(PAPER)
    for s in panel.spines.values():
        s.set_color(INK)
        s.set_linewidth(1.2)
    panel.add_patch(Rectangle((0.02, 0.015), 0.96, 0.97, fill=False,
                              edgecolor="#8A7454", lw=0.5))

    panel.text(0.5, 0.972, "中华帝国全图", fontproperties=F_STK, fontsize=26,
               color="#5A1E1E", ha="center", va="top")
    panel.text(0.5, 0.928, "四十五省级行政区划图", fontproperties=F_SONG, fontsize=10.5,
               color="#3B2B1C", ha="center", va="top")
    panel.plot([0.10, 0.90], [0.912, 0.912], color="#8A7454", lw=0.6)
    panel.text(0.5, 0.898, "继文十一年（2026）　八州 · 四十三省 · 二市", fontproperties=F_SONG,
               fontsize=7.2, color="#6B5B45", ha="center", va="top")

    sw = 0.078
    sx0, sy0 = 0.898, 0.968
    panel.add_patch(Rectangle((sx0, sy0 - sw), sw, sw, facecolor="#A61C26",
                              edgecolor="#7E1218", lw=0.5))
    panel.text(sx0 + sw / 2, sy0 - sw * 0.28, "金瓯", fontproperties=F_KAI, fontsize=7.6,
               color="white", ha="center", va="center")
    panel.text(sx0 + sw / 2, sy0 - sw * 0.72, "永固", fontproperties=F_KAI, fontsize=7.6,
               color="white", ha="center", va="center")

    groups = [
        ("京畿", "京畿直隶州", [("长安市", "长安"), ("陕西省", "延安"), ("成都省", "成都"),
                           ("重庆省", "重庆"), ("中原省", "洛阳")]),
        ("东北", "东北州", [("辽宁", "沈阳"), ("吉林", "长春"), ("黑龙江", "哈尔滨"),
                         ("滨海", "海参崴"), ("朝鲜", "平壤")]),
        ("蒙古", "蒙古州", [("漠南", "呼和浩特"), ("河套", "包头"), ("漠北", "乌兰巴托"),
                         ("科布多", "科布多"), ("阿尔泰", "乌列盖")]),
        ("西北", "西北州", [("河西", "肃州"), ("甘宁", "兰州"), ("新疆", "乌鲁木齐"),
                         ("帕米尔", "喀什")]),
        ("华北", "华北州", [("河北", "北京"), ("山西", "太原"), ("山东", "济南"),
                         ("河南", "郑州"), ("辽南", "大连"), ("北海", "天津")]),
        ("江南", "江南州", [("上海", "上海"), ("江苏", "南京"), ("浙江", "杭州"),
                         ("安徽", "合肥"), ("江西", "南昌"), ("福建", "福州"),
                         ("台湾", "台北"), ("岭南", "广州")]),
        ("云贵", "云贵州", [("云南", "昆明"), ("贵州", "贵阳"), ("广西", "桂林"),
                         ("南宁", "南宁"), ("河内", "河内"), ("澜沧", "万象"),
                         ("北部湾", "海口")]),
        ("青藏", "青藏州", [("青海", "西宁"), ("西藏", "拉萨"), ("藏南", "泽当"),
                         ("康巴", "昌都"), ("喜马拉雅", "日喀则")]),
    ]

    y = 0.872
    panel.text(0.5, y, "四 十 五 省 级 与 省 会", fontproperties=F_HEI, fontsize=8.0,
               color="#5A4630", ha="center", va="top")
    y -= 0.030
    for key, title, items in groups:
        panel.add_patch(Rectangle((0.038, y - 0.008), 0.028, 0.016,
                                  facecolor=COLORS[key], edgecolor="#6B5B45", lw=0.5))
        panel.text(0.078, y, "%s（%d）" % (title, len(items)), fontproperties=F_HEI,
                   fontsize=7.8, color="#2B1F15", ha="left", va="center")
        y -= 0.0195
        line = "　".join("%s·%s" % (n, c) for n, c in items)
        # 手工折行：优先在“　”处分两行
        chunks = line.split("　")
        rows, cur = [], ""
        for ch in chunks:
            if len(cur) + len(ch) > 15 and cur:
                rows.append(cur)
                cur = ch
            else:
                cur = (cur + "　" + ch) if cur else ch
        if cur:
            rows.append(cur)
        for r in rows:
            panel.text(0.062, y, r, fontproperties=F_SONG, fontsize=6.6,
                       color="#332618", ha="left", va="center")
            y -= 0.0175
        y -= 0.004

    # legend
    ly = min(y - 0.012, 0.212)
    panel.text(0.5, ly, "图 例", fontproperties=F_HEI, fontsize=8.0,
               color="#5A4630", ha="center", va="top")
    items = [
        ("国界", "line", INK, 1.8, "solid"),
        ("州界", "line", "#3A2A1A", 0.9, (0, (3, 2))),
        ("省界", "line", "#F7EEDA", 1.4, "solid"),
        ("首都", "star", "#A61C26", 0, ""),
        ("省会", "dot", "#A61C26", 0, ""),
        ("河流", "line", "#2E6C8A", 0.9, "solid"),
        ("湖泊", "lake", "#2E6A86", 0, ""),
    ]
    yy = ly - 0.030
    for label, kind, col, lw, ls in items:
        if kind == "line":
            panel.plot([0.085, 0.185], [yy, yy], color=col, lw=lw, ls=ls)
        elif kind == "star":
            panel.scatter([0.135], [yy], marker="*", s=56, c=col, edgecolors="white",
                          linewidths=0.5)
        elif kind == "dot":
            panel.scatter([0.135], [yy], marker="o", s=16, c=col, edgecolors="white",
                          linewidths=0.5)
        else:
            panel.add_patch(Rectangle((0.105, yy - 0.006), 0.06, 0.012, facecolor=col,
                                      edgecolor="#1B4257", lw=0.4))
        panel.text(0.210, yy, label, fontproperties=F_SONG, fontsize=7.4,
                   color="#3B2B1C", ha="left", va="center")
        yy -= 0.0265

    panel.text(0.5, 0.045, "本图为设定示意图：省界依《疆域与省界表》"
                          "所定犬牙交错，按地级界归并；面积、人口以表为准。",
               fontproperties=F_SONG, fontsize=6.4, color="#7A6A52",
               ha="center", va="center", linespacing=1.6)

    fig.add_artist(Rectangle((0.003, 0.004), 0.994, 0.992, fill=False,
                             edgecolor="#7A5C3A", lw=2.2, transform=fig.transFigure))
    fig.add_artist(Rectangle((0.007, 0.008), 0.986, 0.984, fill=False,
                             edgecolor="#B39A72", lw=0.6, transform=fig.transFigure))

    rng = np.random.default_rng(7)
    noise = rng.normal(0.5, 0.16, (700, 500))
    ax.imshow(noise, extent=(x0, x1, y0, y1), origin="lower", cmap="gray",
              alpha=0.03, zorder=20, aspect="auto")

    fig.savefig(OUT, dpi=300, facecolor=fig.get_facecolor())
    print("saved", OUT)


if __name__ == "__main__":
    main()
