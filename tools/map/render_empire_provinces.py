# -*- coding: utf-8 -*-
"""Render the 45-province atlas plate (v2: auto label placement)."""
import pickle
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import numpy as np
from matplotlib.font_manager import FontProperties
from matplotlib.patches import PathPatch, Rectangle, Polygon as MplPolygon
from matplotlib.path import Path
from shapely.geometry import LineString, MultiLineString, MultiPolygon, Point, Polygon
from shapely.ops import polylabel, unary_union

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from prep_empire_map import TR  # noqa: E402
from prep_empire_provinces import PROV  # noqa: E402
from pyproj import Transformer  # noqa: E402

INV = Transformer.from_crs(
    "+proj=aea +lat_1=25 +lat_2=47 +lat_0=35 +lon_0=105 "
    "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs", "EPSG:4326", always_xy=True)
DEBUG = os.environ.get("MAP_DEBUG") == "1"

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
    "Range/mtn": ("#6F5338", 0.08),
    "Desert": ("#D2B36B", 0.12),
    "Basin": ("#6F7F5C", 0.04),
}

# 省名锚点（经纬度）：缺省用 polylabel
NAME_POS = {
    "长安市": (108.30, 34.05),
    "陕西省": (109.90, 37.30),
    "成都省": (104.30, 31.30),
    "重庆省": (107.90, 30.10),
    "中原省": (111.40, 33.10),
    "辽宁": (123.00, 42.40),
    "吉林": (126.30, 44.20),
    "黑龙江": (127.80, 47.90),
    "滨海": (134.20, 47.60),
    "朝鲜": (127.60, 38.40),
    "漠南": (114.80, 42.90),
    "河套": (108.60, 40.30),
    "漠北": (104.80, 46.60),
    "科布多": (93.20, 49.40),
    "阿尔泰": (89.70, 46.45),
    "河西": (99.00, 39.50),
    "甘宁": (105.40, 35.50),
    "新疆": (84.00, 43.40),
    "帕米尔": (78.60, 38.20),
    "河北": (115.00, 38.70),
    "山西": (112.20, 37.70),
    "山东": (118.40, 36.30),
    "河南": (114.80, 33.90),
    "辽南": (122.35, 39.95),
    "北海": (118.05, 38.15),
    "上海": (122.90, 31.30),
    "江苏": (119.70, 33.20),
    "浙江": (120.30, 28.90),
    "安徽": (117.00, 31.20),
    "江西": (115.40, 27.60),
    "福建": (117.60, 26.20),
    "台湾": (121.10, 23.80),
    "岭南": (113.20, 23.80),
    "云南": (101.30, 25.10),
    "贵州": (107.40, 26.40),
    "广西": (109.40, 24.50),
    "南宁": (107.50, 22.60),
    "河内": (106.10, 20.60),
    "澜沧": (102.60, 18.90),
    "北部湾": (109.80, 19.50),
    "青海": (96.20, 35.60),
    "西藏": (87.00, 31.60),
    "藏南": (94.40, 29.35),
    "康巴": (98.90, 30.40),
    "喜马拉雅": (85.80, 28.70),
}

GEO = [
    ("贝加尔湖", 106.6, 54.1, 7.6),
    ("巴尔喀什湖", 73.6, 46.3, 7.4),
    ("天山", 81.6, 42.3, 7.6),
    ("昆仑山", 86.0, 36.4, 7.4),
    ("喜马拉雅山", 87.0, 27.7, 7.2),
    ("帕米尔高原", 73.4, 39.1, 7.0),
    ("兴都库什山", 69.8, 35.9, 7.0),
    ("阿尔泰山", 91.4, 49.7, 7.0),
    ("大兴安岭", 121.6, 50.6, 7.0),
    ("外兴安岭", 127.8, 56.6, 7.0),
    ("塔里木盆地", 84.4, 38.7, 7.0),
    ("准噶尔盆地", 86.2, 45.4, 7.0),
    ("河西走廊", 100.3, 39.0, 6.6),
    ("朝鲜半岛", 126.0, 36.6, 7.0),
    ("库页岛", 143.0, 51.2, 7.2),
    ("琉球群岛", 127.4, 26.6, 6.6),
    ("曾母暗沙", 112.3, 4.6, 6.6),
    ("西沙群岛", 112.3, 16.4, 6.6),
    ("南沙群岛", 114.6, 9.6, 6.6),
]
SEA = [
    ("渤　海", 120.0, 38.5, 8.0),
    ("黄　海", 123.8, 34.4, 9.4),
    ("东　海", 126.0, 28.2, 9.4),
    ("南　海", 113.6, 14.4, 10.4),
    ("日本海", 135.6, 41.4, 8.6),
    ("鄂霍次克海", 146.6, 53.4, 7.8),
]
FAR = [("苏联共同体", 99.0, 61.0), ("印　度", 76.0, 21.0), ("日　本", 139.6, 37.4)]


def blend(hex_color, other="#FFFFFF", t=0.14):
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


class Placer:
    """Greedy non-overlapping label placement in data coordinates."""

    def __init__(self, ax, fig):
        self.ax = ax
        self.fig = fig
        fig.canvas.draw()
        self.renderer = fig.canvas.get_renderer()
        bb = ax.get_window_extent()
        (ax0, ax1) = ax.get_xlim()
        (ay0, ay1) = ax.get_ylim()
        self.dx = (ax1 - ax0) / bb.width
        self.dy = (ay1 - ay0) / bb.height
        self.xlim = (ax0, ax1)
        self.ylim = (ay0, ay1)
        self.rects = []

    def size(self, text, fp, fs):
        t = self.ax.text(0, 0, text, fontproperties=fp, fontsize=fs)
        bb = t.get_window_extent(self.renderer)
        t.remove()
        return bb.width * self.dx, bb.height * self.dy

    def free(self, x, y, w, h, pad=0.45):
        r = (x - w / 2 - w * pad * 0.2, y - h / 2 - h * pad * 0.35,
             x + w / 2 + w * pad * 0.2, y + h / 2 + h * pad * 0.35)
        if r[0] < self.xlim[0] or r[2] > self.xlim[1]:
            return False
        if r[1] < self.ylim[0] or r[3] > self.ylim[1]:
            return False
        for q in self.rects:
            if r[0] < q[2] and r[2] > q[0] and r[1] < q[3] and r[3] > q[1]:
                return False
        return True

    def overlap(self, x, y, w, h, inside=None):
        r = (x - w / 2, y - h / 2, x + w / 2, y + h / 2)
        tot = 0.0
        if r[0] < self.xlim[0] or r[2] > self.xlim[1]:
            tot += w * h
        if r[1] < self.ylim[0] or r[3] > self.ylim[1]:
            tot += w * h
        if inside is not None and not inside.contains(Point(x, y)):
            tot += w * h * 2.5
        for q in self.rects:
            dx = min(r[2], q[2]) - max(r[0], q[0])
            dy = min(r[3], q[3]) - max(r[1], q[1])
            if dx > 0 and dy > 0:
                tot += dx * dy
        return tot

    def place_in_polygon(self, poly, ax_x, ax_y, w, h, n=14, leader=True,
                         leader_lw=0.45):
        minx, miny, maxx, maxy = poly.bounds
        best = None
        cands = [(ax_x, ax_y)]
        for i in range(n):
            for j in range(n):
                x = minx + (maxx - minx) * (i + 0.5) / n
                y = miny + (maxy - miny) * (j + 0.5) / n
                cands.append((x, y))
        for x, y in cands:
            if not poly.contains(Point(x, y)):
                continue
            ov = self.overlap(x, y, w, h)
            # 距离惩罚：越靠近原锚点越好
            dist = ((x - ax_x) ** 2 + (y - ax_y) ** 2) ** 0.5
            score = ov / (w * h) + 0.55 * dist / max(w, h)
            if best is None or score < best[0]:
                best = (score, x, y)
        if best is None:
            return ax_x, ax_y
        _, x, y = best
        if leader and ((x - ax_x) ** 2 + (y - ax_y) ** 2) ** 0.5 > 0.9 * w:
            self.ax.plot([ax_x, x], [ax_y, y], color="#4A3A28", lw=leader_lw,
                         alpha=0.5, zorder=11.4)
        self.rects.append((x - w / 2, y - h / 2, x + w / 2, y + h / 2))
        return x, y

    def place(self, ax_x, ax_y, w, h, steps=((0, 0),), leader=False, leader_lw=0.45,
              inside=None):
        best = None
        for k, (ox, oy) in enumerate(steps):
            x, y = ax_x + ox * w, ax_y + oy * h
            ov = self.overlap(x, y, w, h, inside)
            if ov <= 0:
                if leader and k > 0:
                    self.ax.plot([ax_x, x], [ax_y, y], color="#4A3A28", lw=leader_lw,
                                 alpha=0.55, zorder=11.4)
                self.rects.append((x - w / 2, y - h / 2, x + w / 2, y + h / 2))
                return x, y
            if best is None or ov < best[0]:
                best = (ov, x, y, k)
        ov, x, y, k = best
        if leader and k > 0:
            self.ax.plot([ax_x, x], [ax_y, y], color="#4A3A28", lw=leader_lw,
                         alpha=0.55, zorder=11.4)
        self.rects.append((x - w / 2, y - h / 2, x + w / 2, y + h / 2))
        return x, y


def label_steps(scale=1.0):
    d = [(0, 0)]
    r = 1.0
    d += [(r, 0), (-r, 0), (0, r), (0, -r),
          (0.8 * r, 0.8 * r), (-0.8 * r, 0.8 * r),
          (0.8 * r, -0.8 * r), (-0.8 * r, -0.8 * r)]
    return [(x * scale, y * scale) for x, y in d]


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

    order = {}
    for name, (st, _c, _x, _y) in PROV.items():
        order.setdefault(st, []).append(name)
    shade = {}
    for st, names in order.items():
        names.sort(key=lambda n: -provs[n].area)
        for i, n in enumerate(names):
            shade[n] = COLORS[st] if i % 2 == 0 else blend(COLORS[st], t=0.26)
        for n in names:
            add_geom(ax, provs[n], facecolor=shade[n], edgecolor="none", zorder=3)

    for cls, name, g in d["terrain"]:
        if cls not in TERRAIN_COLORS:
            continue
        col, alpha = TERRAIN_COLORS[cls]
        add_geom(ax, g, facecolor=col, edgecolor="none", alpha=alpha, zorder=4)

    empire = d["empire"]
    for name, g in d["lakes"]:
        if g.area < 800e6 or not g.intersects(empire):
            continue
        add_geom(ax, g, facecolor="#2E6A86", edgecolor="#2A5B72", linewidth=0.25, zorder=6.05)
    for name, g in d["rivers"]:
        if g.length < 500e3 or not g.intersects(empire):
            continue
        for seg in line_segments(g):
            ax.plot(seg[:, 0], seg[:, 1], color="#2E6C8A", lw=0.35, alpha=0.42, zorder=5.4)

    for name, g in provs.items():
        b = g.boundary.intersection(empire.buffer(-2000)).simplify(1800)
        for seg in line_segments(b):
            ax.plot(seg[:, 0], seg[:, 1], color="#FAF2DF", lw=0.85, alpha=0.9, zorder=5.6)

    for st, g in d["states"].items():
        b = g.boundary.intersection(empire.buffer(-2500)).simplify(2200)
        for seg in line_segments(b):
            ax.plot(seg[:, 0], seg[:, 1], color="#F6ECD6", lw=2.6, alpha=0.35, zorder=6.6)
            ax.plot(seg[:, 0], seg[:, 1], color="#3A2A1A", lw=1.15,
                    ls=(0, (5, 2.2)), zorder=6.8, alpha=0.92)

    for seg in line_segments(empire.boundary):
        pass
    # 国界：主体轮廓简化后绘制；碎小岛屿另作点状，避免“珊瑚礁”状叠线
    parts = list(empire.geoms) if hasattr(empire, "geoms") else [empire]
    big = unary_union([p for p in parts if p.area > 300e6])
    small = [p for p in parts if p.area <= 300e6]
    for seg in line_segments(big.boundary.simplify(1200)):
        ax.plot(seg[:, 0], seg[:, 1], color="#EFE3C8", lw=2.6, alpha=0.12, zorder=7)
        ax.plot(seg[:, 0], seg[:, 1], color=INK, lw=1.45, zorder=8)
    for p in small:
        if p.area < 2e6:
            continue
        c = p.representative_point()
        ax.scatter([c.x], [c.y], s=3.2, c="#4A6B52", edgecolors="none",
                   alpha=0.95, zorder=8)

    for g in d["okinawa"]:
        add_geom(ax, g, facecolor="#DDD2B8", edgecolor="#8A7A60", linewidth=0.35, zorder=6)

    for nm, zh, g in d["islands"]:
        if nm not in ("Paracel Islands", "Spratly Islands"):
            continue
        polys = list(g.geoms) if hasattr(g, "geoms") else [g]
        polys.sort(key=lambda p: p.area, reverse=True)
        for p in polys[:4]:
            c = p.centroid
            ax.scatter([c.x], [c.y], s=12, c="#2F4A3C", edgecolors="#F0E5CC",
                       linewidths=0.35, zorder=9)

    # ---------------- labels ----------------
    pl = Placer(ax, fig)
    names_by_area = sorted(PROV, key=lambda n: -provs[n].area)

    # capitals first: they pin the atlas reading order
    # 先落全部点位并登记为障碍，再排文字
    for n in names_by_area:
        st, cap, lon, lat = PROV[n]
        x, y = map_xy(lon, lat)
        if n == "长安市":
            ax.scatter([x], [y], marker="*", s=340, c="#A61C26", edgecolors="white",
                       linewidths=0.8, zorder=13)
        else:
            ax.scatter([x], [y], marker="o", s=26, c="#A61C26", edgecolors="white",
                       linewidths=0.5, zorder=13)
        r = 7 * pl.dx
        pl.rects.append((x - r, y - r, x + r, y + r))

    for n in names_by_area:
        st, cap, lon, lat = PROV[n]
        x, y = map_xy(lon, lat)
        big = n in ("上海", "长安市")
        fs = 8.4 if big else 7.4
        w, h = pl.size(cap, F_SONG, fs)
        # 文字框边缘与圆点保持固定间距，避免描边盖住点位
        sx0 = 0.5 + 12 * pl.dx / w
        sy0 = 0.5 + 9 * pl.dy / h
        steps = [(sx0, sy0), (-sx0, sy0), (sx0, -sy0), (-sx0, -sy0),
                 (0, 1.9 * sy0), (0, -1.9 * sy0),
                 (1.9 * sx0, sy0), (-1.9 * sx0, sy0),
                 (1.9 * sx0, -sy0), (-1.9 * sx0, -sy0),
                 (1.9 * sx0, 0), (-1.9 * sx0, 0)]
        cx, cy = pl.place(x, y, w, h, steps, leader=False)
        gx, gy = sx0 * w, sy0 * h
        if ((cx - x) ** 2 + (cy - y) ** 2) ** 0.5 > 1.35 * (gx * gx + gy * gy) ** 0.5:
            ex = cx - np.sign(cx - x) * (0.5 * w + 2 * pl.dx)
            ey = cy - np.sign(cy - y) * (0.5 * h + 2 * pl.dy)
            ax.plot([x, ex], [y, ey], color="#4A3A28", lw=0.4, alpha=0.5, zorder=11.4)
        ax.text(cx, cy, cap, fontproperties=F_SONG, fontsize=fs, color="#241A12",
                ha="center", va="center", zorder=14,
                path_effects=[pe.withStroke(linewidth=2.4, foreground="#F7EEDB",
                                            alpha=0.92)])

    # province names second (leaders when pushed away from the polygon centre)
    prov_size = {}
    for n in PROV:
        fs = 7.2 if n in ("上海", "长安市", "辽南", "台湾", "北海", "阿尔泰") else 9.4
        prov_size[n] = (fs,) + pl.size(n, F_KAI, fs)

    for n in names_by_area:
        if n in ("上海", "长安市") or PROV[n][1] == n:
            continue
        st, cap, _x, _y = PROV[n]
        if n in NAME_POS:
            lon, lat = NAME_POS[n]
        else:
            lon, lat = polylabel(big_part(provs[n]), tolerance=6000).coords[0]
        px, py = map_xy(lon, lat)
        fs, w, h = prov_size[n]
        x, y = pl.place_in_polygon(provs[n], px, py, w, h, n=16)
        if DEBUG:
            glon, glat = INV.transform(x, y)
            inside = provs[n].contains(Point(x, y))
            print("LBL %-5s %.2f,%.2f -> %.2f,%.2f inside=%s"
                  % (n, lon, lat, glon, glat, inside))
        ax.text(x, y, n, fontproperties=F_KAI, fontsize=fs, color="#241A10",
                ha="center", va="center", zorder=12,
                path_effects=[pe.withStroke(linewidth=2.4, foreground="#F7EEDB", alpha=0.88)])
    # geographic notes (placed last, may be dropped)
    for txt, lon, lat, fs in GEO:
        x, y = map_xy(lon, lat)
        w, h = pl.size(txt, F_SONG, fs)
        if not pl.free(x, y, w, h):
            continue
        pl.rects.append((x - w / 2, y - h / 2, x + w / 2, y + h / 2))
        ax.text(x, y, txt, fontproperties=F_SONG, fontsize=fs, color="#5B4B39",
                ha="center", va="center", zorder=11, alpha=0.8,
                path_effects=[pe.withStroke(linewidth=1.6, foreground="#EFE5CF", alpha=0.6)])

    for txt, lon, lat, fs in SEA:
        x, y = map_xy(lon, lat)
        w, h = pl.size(txt, F_KAI, fs)
        if not pl.free(x, y, w, h):
            continue
        pl.rects.append((x - w / 2, y - h / 2, x + w / 2, y + h / 2))
        ax.text(x, y, txt, fontproperties=F_KAI, fontsize=fs, color="#9FC3D6",
                ha="center", va="center", zorder=10, alpha=0.85)

    for txt, lon, lat in FAR:
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

    cx, cy = 3860e3, 3340e3
    ax.add_patch(MplPolygon([[cx, cy + 240e3], [cx - 70e3, cy - 90e3],
                             [cx, cy - 22e3], [cx + 70e3, cy - 90e3]],
                            closed=True, facecolor="#A61C26", edgecolor=INK, lw=0.7, zorder=15))
    ax.add_patch(MplPolygon([[cx, cy + 240e3], [cx, cy - 22e3], [cx - 70e3, cy - 90e3]],
                            closed=True, facecolor="#6E1A1E", edgecolor=INK, lw=0.7, zorder=15))
    ax.text(cx, cy + 300e3, "北", fontproperties=F_KAI, fontsize=9.2, color=INK,
            ha="center", va="bottom", zorder=15)

    # ---------------- panel ----------------
    panel = fig.add_axes([0.750, 0.014, 0.242, 0.972])
    panel.set_xlim(0, 1)
    panel.set_ylim(0, 1)
    panel.set_xticks([])
    panel.set_yticks([])
    panel.set_facecolor(PAPER)
    for s in panel.spines.values():
        s.set_color(INK)
        s.set_linewidth(1.2)
    panel.add_patch(Rectangle((0.02, 0.012), 0.96, 0.976, fill=False,
                              edgecolor="#8A7454", lw=0.5))

    # figure is 18x12 in; panel axes 4.36 x 11.66 in -> y/x = 0.374
    AR = (0.242 * 18.0) / (0.972 * 12.0)

    panel.text(0.44, 0.978, "中华帝国全图", fontproperties=F_STK, fontsize=21,
               color="#5A1E1E", ha="center", va="top")
    panel.text(0.44, 0.940, "四十五省级行政区划图", fontproperties=F_SONG, fontsize=10.2,
               color="#3B2B1C", ha="center", va="top")
    panel.plot([0.08, 0.86], [0.926, 0.926], color="#8A7454", lw=0.6)
    panel.text(0.44, 0.912, "继文十一年（2026）　八州 · 四十三省 · 二市",
               fontproperties=F_SONG, fontsize=7.2, color="#6B5B45",
               ha="center", va="top")

    sw = 0.115
    sh = sw * AR
    sx0, sy0 = 0.915 - sw, 0.982
    panel.add_patch(Rectangle((sx0, sy0 - sh), sw, sh, facecolor="#A61C26",
                              edgecolor="#7E1218", lw=0.5))
    panel.text(sx0 + sw / 2, sy0 - sh * 0.28, "金瓯", fontproperties=F_KAI, fontsize=6.6,
               color="white", ha="center", va="center")
    panel.text(sx0 + sw / 2, sy0 - sh * 0.72, "永固", fontproperties=F_KAI, fontsize=6.6,
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

    y = 0.888
    panel.text(0.5, y, "四 十 五 省 级 与 省 会", fontproperties=F_HEI, fontsize=8.0,
               color="#5A4630", ha="center", va="top")
    y -= 0.028
    for key, title, items in groups:
        panel.add_patch(Rectangle((0.040, y - 0.0055), 0.031, 0.011,
                                  facecolor=COLORS[key], edgecolor="#6B5B45", lw=0.5))
        panel.text(0.082, y, "%s（%d）" % (title, len(items)), fontproperties=F_HEI,
                   fontsize=7.8, color="#2B1F15", ha="left", va="center")
        y -= 0.0175
        chunks = ["%s·%s" % (n, c) for n, c in items]
        rows, cur = [], ""
        for ch in chunks:
            if len(cur) + len(ch) > 14 and cur:
                rows.append(cur)
                cur = ch
            else:
                cur = (cur + "　" + ch) if cur else ch
        if cur:
            rows.append(cur)
        for r in rows:
            panel.text(0.058, y, r, fontproperties=F_SONG, fontsize=6.7,
                       color="#332618", ha="left", va="center")
            y -= 0.0165
        y -= 0.0035

    # legend
    ly = 0.263
    panel.text(0.5, ly, "图 例", fontproperties=F_HEI, fontsize=8.0,
               color="#5A4630", ha="center", va="top")
    items = [
        ("国界", "line", INK, 1.5, "solid"),
        ("州界", "line", "#3A2A1A", 1.1, (0, (4, 2))),
        ("省界", "chip", "#7C9966", 0, ""),
        ("首都", "star", "#A61C26", 0, ""),
        ("省会", "dot", "#A61C26", 0, ""),
        ("河流", "line", "#2E6C8A", 0.9, "solid"),
        ("湖泊", "lake", "#2E6A86", 0, ""),
    ]
    yy = ly - 0.028
    for label, kind, col, lw, ls in items:
        if kind == "line":
            panel.plot([0.075, 0.175], [yy, yy], color=col, lw=lw, ls=ls)
        elif kind == "chip":
            panel.add_patch(Rectangle((0.093, yy - 0.0055), 0.031, 0.011,
                                      facecolor="#6E8F5A", edgecolor="none"))
            panel.add_patch(Rectangle((0.124, yy - 0.0055), 0.031, 0.011,
                                      facecolor="#9CB489", edgecolor="none"))
            panel.plot([0.124, 0.124], [yy - 0.0055, yy + 0.0055],
                       color="#FAF2DF", lw=1.4)
        elif kind == "star":
            panel.scatter([0.125], [yy], marker="*", s=52, c=col, edgecolors="white",
                          linewidths=0.5)
        elif kind == "dot":
            panel.scatter([0.125], [yy], marker="o", s=15, c=col, edgecolors="white",
                          linewidths=0.5)
        else:
            panel.add_patch(Rectangle((0.105, yy - 0.005), 0.05, 0.010, facecolor=col,
                                      edgecolor="#2A5B72", lw=0.4))
        panel.text(0.200, yy, label, fontproperties=F_SONG, fontsize=7.4,
                   color="#3B2B1C", ha="left", va="center")
        yy -= 0.0245

    panel.text(0.5, 0.062, "本图为设定示意图：省界依《疆域与省界表》所定犬牙交错，",
               fontproperties=F_SONG, fontsize=6.2, color="#7A6A52",
               ha="center", va="center")
    panel.text(0.5, 0.044, "按地级界归并；面积、人口以表为准。",
               fontproperties=F_SONG, fontsize=6.2, color="#7A6A52",
               ha="center", va="center")

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
