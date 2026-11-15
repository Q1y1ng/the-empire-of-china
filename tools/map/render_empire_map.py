# -*- coding: utf-8 -*-
"""Render the eight-province empire map, atlas-plate layout (v3)."""
import pickle

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import numpy as np
from matplotlib.path import Path
from matplotlib.patches import PathPatch, Rectangle, Polygon as MplPolygon
from matplotlib.font_manager import FontProperties
from shapely.geometry import Polygon, MultiPolygon, LineString, MultiLineString
from pyproj import Transformer

PICKLE = r"C:\Users\s3431\AppData\Local\Temp\empire-map\prepared.pkl"
OUT = r"C:\Users\s3431\AppData\Local\Temp\empire-map\empire_map_v2.png"

PROJ = ("+proj=aea +lat_1=25 +lat_2=47 +lat_0=35 +lon_0=105 "
        "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs")
TR = Transformer.from_crs("EPSG:4326", PROJ, always_xy=True)

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
CAPITALS = {
    "京畿": ("长安", 108.94, 34.34, "首都", 12, -15, "left"),
    "华北": ("北京", 116.40, 39.90, "", 10, -9, "left"),
    "东北": ("沈阳", 123.43, 41.80, "", 10, 6, "left"),
    "蒙古": ("呼和浩特", 111.75, 40.84, "", -10, 7, "right"),
    "西北": ("乌鲁木齐", 87.62, 43.82, "", 7, 10, "left"),
    "江南": ("上海", 121.47, 31.23, "", 10, -9, "left"),
    "云贵": ("南宁", 108.37, 22.82, "", 9, -11, "left"),
    "青藏": ("拉萨", 91.14, 29.65, "", -10, -11, "right"),
}
TERRAIN_COLORS = {
    "Range/mtn": ("#6F5338", 0.10),
    "Desert": ("#D2B36B", 0.15),
    "Basin": ("#6F7F5C", 0.05),
}


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
    return []


def map_xy(lon, lat):
    return TR.transform(lon, lat)


def main():
    d = pickle.load(open(PICKLE, "rb"))
    fig = plt.figure(figsize=(15, 10), dpi=300)
    fig.patch.set_facecolor(PAPER)

    ax = fig.add_axes([0.012, 0.018, 0.712, 0.964])
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

    from shapely.ops import unary_union
    scs = unary_union([g for nm, zh, g in d["islands"]
                       if nm in ("Paracel Islands", "Spratly Islands")]).buffer(15000)
    neigh = d["neighbours"].difference(scs)
    add_geom(ax, neigh, facecolor=NEIGH, edgecolor=NEIGH_EDGE,
             linewidth=0.35, zorder=2)

    for st, g in d["states"].items():
        add_geom(ax, g, facecolor=COLORS[st], edgecolor=COLORS[st],
                 linewidth=0.35, zorder=3)

    for cls, name, g in d["terrain"]:
        if cls not in TERRAIN_COLORS:
            continue
        col, alpha = TERRAIN_COLORS[cls]
        add_geom(ax, g, facecolor=col, edgecolor="none", alpha=alpha, zorder=4)

    # lakes: only sizeable ones
    n_lakes = 0
    empire = d["empire"]
    for name, g in d["lakes"]:
        if g.area < 800e6 or not g.intersects(empire):
            continue
        add_geom(ax, g, facecolor="#2E6A86", edgecolor="#1B4257",
                 linewidth=0.3, zorder=5)
        n_lakes += 1
    # rivers: only long ones
    n_riv = 0
    for name, g in d["rivers"]:
        if g.length < 500e3 or not g.intersects(empire):
            continue
        for seg in line_segments(g):
            ax.plot(seg[:, 0], seg[:, 1], color="#2E6C8A", lw=0.4,
                    alpha=0.6, zorder=5)
        n_riv += 1
    print("lakes drawn", n_lakes, "rivers drawn", n_riv)

    # state borders: only the internal lines, simplified
    empire_inner = d["empire"].buffer(-2500)
    for st, g in d["states"].items():
        b = g.boundary.intersection(empire_inner).simplify(2500)
        for seg in line_segments(b):
            ax.plot(seg[:, 0], seg[:, 1], color="#43301F", lw=0.8,
                    ls=(0, (4, 2)), zorder=7, alpha=0.9)

    # national border
    for seg in line_segments(d["empire"].boundary):
        ax.plot(seg[:, 0], seg[:, 1], color="#F2E7CE", lw=4.5,
                alpha=0.18, zorder=7)
        ax.plot(seg[:, 0], seg[:, 1], color=INK, lw=1.8, zorder=8)

    for g in d["okinawa"]:
        add_geom(ax, g, facecolor="#DDD2B8", edgecolor="#8A7A60",
                 linewidth=0.35, zorder=6)

    # island groups: only the largest few islets per group
    for nm, zh, g in d["islands"]:
        if nm not in ("Paracel Islands", "Spratly Islands"):
            continue
        polys = list(g.geoms) if hasattr(g, "geoms") else [g]
        polys.sort(key=lambda p: p.area, reverse=True)
        for p in polys[:3]:
            c = p.centroid
            ax.scatter([c.x], [c.y], s=14, c="#2F4A3C", edgecolors="#F0E5CC",
                       linewidths=0.4, zorder=9)
        if nm == "Paracel Islands":
            x, y = map_xy(112.3, 16.4)
            ax.text(x, y, "西沙群岛", fontproperties=F_SONG, fontsize=7,
                    color="#3E3122", ha="center", va="center", zorder=10,
                    path_effects=[pe.withStroke(linewidth=2.2, foreground="#EFE5CF",
                                                alpha=0.85)])
        else:
            x, y = map_xy(114.0, 9.8)
            ax.text(x, y, "南沙群岛", fontproperties=F_SONG, fontsize=7,
                    color="#3E3122", ha="center", va="center", zorder=10,
                    path_effects=[pe.withStroke(linewidth=2.2, foreground="#EFE5CF",
                                                alpha=0.85)])

    # state labels
    pos = {
        "京畿": (105.3, 30.4),
        "华北": (118.7, 35.2),
        "东北": (129.8, 47.0),
        "蒙古": (103.0, 46.2),
        "西北": (84.2, 41.2),
        "江南": (118.1, 26.2),
        "云贵": (103.2, 21.0),
        "青藏": (86.6, 32.4),
    }
    for st, (lon, lat) in pos.items():
        x, y = map_xy(lon, lat)
        fs = 15 if st == "京畿" else 21
        ax.text(x, y, LABELS[st], fontproperties=F_KAI, fontsize=fs,
                color="#2A1D12", ha="center", va="center", zorder=12,
                path_effects=[pe.withStroke(linewidth=3.2, foreground="#F3E9D3",
                                            alpha=0.85)])

    # capitals
    for st, (name, lon, lat, note, dx, dy, ha) in CAPITALS.items():
        x, y = map_xy(lon, lat)
        if st == "京畿":
            ax.scatter([x], [y], marker="*", s=320, c="#A61C26",
                       edgecolors="white", linewidths=0.8, zorder=13)
        else:
            ax.scatter([x], [y], marker="o", s=42, c="#A61C26",
                       edgecolors="white", linewidths=0.6, zorder=13)
        ax.annotate(name, (x, y), xytext=(dx, dy), textcoords="offset points",
                    fontproperties=F_HEI, fontsize=9.2, color="#241A12",
                    ha=ha, va="center", zorder=14,
                    path_effects=[pe.withStroke(linewidth=2.8, foreground="#F3E9D3",
                                                alpha=0.9)])
        if note:
            ax.annotate(note, (x, y), xytext=(dx, dy - 12), textcoords="offset points",
                        fontproperties=F_SONG, fontsize=7.5, color="#6B3A2A",
                        ha=ha, va="center", zorder=14,
                        path_effects=[pe.withStroke(linewidth=2.6, foreground="#F3E9D3",
                                                    alpha=0.9)])

    geo = [
        ("贝加尔湖", 106.8, 54.0, 8.0),
        ("巴尔喀什湖", 74.6, 46.4, 8.0),
        ("天山", 82.0, 42.2, 8.0),
        ("昆仑山", 86.0, 36.5, 7.8),
        ("喜马拉雅山", 87.0, 27.9, 8.0),
        ("帕米尔高原", 73.8, 38.9, 7.8),
        ("兴都库什山", 69.6, 35.9, 7.8),
        ("阿尔泰山", 90.0, 47.9, 7.8),
        ("大兴安岭", 122.0, 50.2, 7.8),
        ("外兴安岭", 127.5, 56.2, 7.8),
        ("塔里木盆地", 84.6, 38.3, 7.6),
        ("准噶尔盆地", 86.0, 45.3, 7.8),
        ("河西走廊", 100.5, 39.8, 7.2),
        ("朝鲜半岛", 127.3, 38.6, 7.8),
        ("台湾岛", 121.0, 23.4, 7.8),
        ("海南岛", 109.8, 18.9, 7.8),
        ("库页岛", 143.0, 51.0, 7.8),
        ("琉球群岛", 127.6, 27.0, 7.2),
        ("曾母暗沙", 112.3, 4.6, 7.2),
    ]
    for txt, lon, lat, fs in geo:
        x, y = map_xy(lon, lat)
        ax.text(x, y, txt, fontproperties=F_SONG, fontsize=fs, color="#3E3122",
                ha="center", va="center", zorder=11, alpha=0.95,
                path_effects=[pe.withStroke(linewidth=2.4, foreground="#EFE5CF",
                                            alpha=0.85)])

    seas = [
        ("渤　海", 119.6, 38.3, 8.8),
        ("黄　海", 123.6, 35.0, 10.5),
        ("东　海", 125.6, 28.0, 10.5),
        ("南　海", 113.5, 15.2, 11.5),
        ("日本海", 135.4, 41.6, 9.5),
        ("鄂霍次克海", 147.0, 53.6, 8.5),
    ]
    for txt, lon, lat, fs in seas:
        x, y = map_xy(lon, lat)
        ax.text(x, y, txt, fontproperties=F_KAI, fontsize=fs, color="#9FC3D6",
                ha="center", va="center", zorder=10, alpha=0.85)

    for txt, lon, lat in [("苏联共同体", 100.0, 60.5), ("印度", 78.0, 22.0),
                          ("日　本", 139.5, 37.0)]:
        x, y = map_xy(lon, lat)
        ax.text(x, y, txt, fontproperties=F_SONG, fontsize=8.2, color="#8B7E68",
                ha="center", va="center", zorder=9, alpha=0.9)

    # scale bar (bottom-left, Indian Ocean)
    sx, sy = -4020e3, -3310e3
    seg = 400e3
    for i in range(3):
        ax.add_patch(Rectangle((sx + i * seg, sy), seg, 42e3,
                               facecolor=INK if i % 2 == 0 else "#EFE4CC",
                               edgecolor=INK, lw=0.5, zorder=15))
    for i, lab in enumerate(["0", "400", "800", "1200"]):
        ax.text(sx + i * seg, sy + 55e3, lab, fontproperties=F_SONG, fontsize=7.5,
                color=INK, ha="center", va="bottom", zorder=15)
    ax.text(sx + 1.5 * seg, sy - 48e3, "公里", fontproperties=F_SONG, fontsize=6.8,
            color=INK, ha="center", va="top", zorder=15)

    # compass (top-right)
    cx, cy = 3860e3, 3340e3
    ax.add_patch(MplPolygon([[cx, cy + 240e3], [cx - 70e3, cy - 90e3],
                             [cx, cy - 22e3], [cx + 70e3, cy - 90e3]],
                            closed=True, facecolor="#A61C26", edgecolor=INK,
                            lw=0.7, zorder=15))
    ax.add_patch(MplPolygon([[cx, cy + 240e3], [cx, cy - 22e3], [cx - 70e3, cy - 90e3]],
                            closed=True, facecolor="#6E1A1E", edgecolor=INK,
                            lw=0.7, zorder=15))
    ax.text(cx, cy + 300e3, "北", fontproperties=F_KAI, fontsize=9.5,
            color=INK, ha="center", va="bottom", zorder=15)

    # ----- panel -----
    panel = fig.add_axes([0.738, 0.018, 0.25, 0.964])
    panel.set_xlim(0, 1)
    panel.set_ylim(0, 1)
    panel.set_xticks([])
    panel.set_yticks([])
    panel.set_facecolor(PAPER)
    for s in panel.spines.values():
        s.set_color(INK)
        s.set_linewidth(1.2)
    panel.add_patch(Rectangle((0.02, 0.02), 0.96, 0.96, fill=False,
                              edgecolor="#8A7454", lw=0.5))

    panel.text(0.5, 0.958, "中华帝国全图", fontproperties=F_STK, fontsize=25,
               color="#5A1E1E", ha="center", va="top")
    panel.text(0.5, 0.906, "八州行政区划与国境总图", fontproperties=F_SONG,
               fontsize=10, color="#3B2B1C", ha="center", va="top")
    panel.plot([0.10, 0.90], [0.889, 0.889], color="#8A7454", lw=0.6)
    panel.text(0.5, 0.873, "继文十一年（2026）　八州 · 四十五省级", fontproperties=F_SONG,
               fontsize=7.4, color="#6B5B45", ha="center", va="top")

    # seal (top-right, clear of the title)
    sw = 0.085
    sx0, sy0 = 0.885, 0.952
    panel.add_patch(Rectangle((sx0, sy0 - sw), sw, sw,
                              facecolor="#A61C26", edgecolor="#7E1218", lw=0.5))
    panel.text(sx0 + sw / 2, sy0 - sw * 0.28, "金瓯", fontproperties=F_KAI,
               fontsize=8.5, color="white", ha="center", va="center")
    panel.text(sx0 + sw / 2, sy0 - sw * 0.72, "永固", fontproperties=F_KAI,
               fontsize=8.5, color="white", ha="center", va="center")

    panel.text(0.5, 0.840, "八 州 与 州 府", fontproperties=F_HEI, fontsize=8.2,
               color="#5A4630", ha="center", va="top")

    rows = [
        ("京畿", "京畿直隶州", "长安", "首都"),
        ("华北", "华北州", "北京", "北方门户"),
        ("东北", "东北州", "沈阳", "重工军工"),
        ("蒙古", "蒙古州", "呼和浩特", "草原稀土"),
        ("西北", "西北州", "乌鲁木齐", "中亚通道"),
        ("江南", "江南州", "上海", "金融航运"),
        ("云贵", "云贵州", "南宁", "半岛门户"),
        ("青藏", "青藏州", "拉萨", "高原治理"),
    ]
    top = 0.808
    step = 0.055
    for i, (key, name, cap, note) in enumerate(rows):
        yy = top - i * step
        panel.add_patch(Rectangle((0.055, yy - 0.011), 0.033, 0.022,
                                  facecolor=COLORS[key], edgecolor="#6B5B45", lw=0.4))
        panel.text(0.105, yy, name, fontproperties=F_HEI, fontsize=9.0,
                   color="#2B1F15", ha="left", va="center")
        panel.text(0.535, yy, cap, fontproperties=F_SONG, fontsize=8.4,
                   color="#3B2B1C", ha="left", va="center")
        panel.text(0.955, yy, note, fontproperties=F_SONG, fontsize=6.6,
                   color="#7A6A52", ha="right", va="center")

    # legend
    ly = 0.372
    panel.text(0.5, ly, "图 例", fontproperties=F_HEI, fontsize=8.2,
               color="#5A4630", ha="center", va="top")
    items = [
        ("国界", "line", INK, 1.7, "solid"),
        ("州界", "line", "#43301F", 0.8, (0, (3, 2))),
        ("首都", "star", "#A61C26", 0, ""),
        ("州府", "dot", "#A61C26", 0, ""),
        ("河流", "line", "#2E6C8A", 0.9, "solid"),
        ("山脉", "patch", "#8A6A48", 0, ""),
    ]
    y = ly - 0.033
    for label, kind, col, lw, ls in items:
        if kind == "line":
            panel.plot([0.09, 0.19], [y, y], color=col, lw=lw, ls=ls)
        elif kind == "star":
            panel.scatter([0.14], [y], marker="*", s=62, c=col,
                          edgecolors="white", linewidths=0.5)
        elif kind == "dot":
            panel.scatter([0.14], [y], marker="o", s=20, c=col,
                          edgecolors="white", linewidths=0.5)
        else:
            panel.add_patch(Rectangle((0.095, y - 0.008), 0.09, 0.016,
                                      facecolor=col, edgecolor="#6B5B45", lw=0.4,
                                      alpha=0.55))
        panel.text(0.215, y, label, fontproperties=F_SONG, fontsize=7.8,
                   color="#3B2B1C", ha="left", va="center")
        y -= 0.033

    panel.text(0.5, 0.075, "本图为设定示意图：八州边界按地理单元归并，\n省界从略；国界以《疆域与省界表》文字为准。",
               fontproperties=F_SONG, fontsize=6.8, color="#7A6A52",
               ha="center", va="center", linespacing=1.7)

    fig.add_artist(Rectangle((0.004, 0.006), 0.992, 0.988, fill=False,
                             edgecolor="#7A5C3A", lw=2.2, transform=fig.transFigure))
    fig.add_artist(Rectangle((0.008, 0.010), 0.984, 0.980, fill=False,
                             edgecolor="#B39A72", lw=0.6, transform=fig.transFigure))

    rng = np.random.default_rng(7)
    noise = rng.normal(0.5, 0.16, (700, 500))
    ax.imshow(noise, extent=(x0, x1, y0, y1), origin="lower", cmap="gray",
              alpha=0.03, zorder=20, aspect="auto")

    fig.savefig(OUT, dpi=300, facecolor=fig.get_facecolor())
    print("saved", OUT)


if __name__ == "__main__":
    main()



