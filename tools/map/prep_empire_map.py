# -*- coding: utf-8 -*-
"""Build projected geometries for the empire map (v4).

NW: enlarged to the Balkhash–Tian Shan–Pamir line (Qing or larger).
NE: natural Amur boundary, Khabarovsk clipped along a short Uda-like line.
"""
import json
import os
import pickle
import time

import numpy as np
import shapefile
import shapely
from pyproj import Transformer
from shapely.geometry import MultiPolygon, Polygon, shape
from shapely.ops import transform, unary_union

BASE = r"C:\Users\s3431\AppData\Local\Temp\empire-map-data"
DATAV = os.path.join(BASE, "datav")
NE = os.path.join(BASE, "ne10m")
OUT = r"C:\Users\s3431\AppData\Local\Temp\empire-map\prepared.pkl"

PROJ = ("+proj=aea +lat_1=25 +lat_2=47 +lat_0=35 +lon_0=105 "
        "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs")
TR = Transformer.from_crs("EPSG:4326", PROJ, always_xy=True)

STATES = ["京畿", "华北", "东北", "蒙古", "西北", "江南", "云贵", "青藏"]

PROV_DEFAULT = {
    110000: "华北", 120000: "华北", 130000: "华北", 140000: "华北", 150000: "蒙古",
    210000: "东北", 220000: "东北", 230000: "东北",
    310000: "江南", 320000: "江南", 330000: "江南", 340000: "江南",
    350000: "江南", 360000: "江南", 370000: "华北",
    410000: "华北", 420000: "江南", 430000: "江南", 440000: "江南",
    450000: "云贵", 460000: "云贵",
    500000: "京畿", 510000: "京畿", 520000: "云贵", 530000: "云贵",
    540000: "青藏", 610000: "京畿", 620000: "西北", 630000: "青藏",
    640000: "西北", 650000: "西北", 710000: "江南", 810000: "江南",
    820000: "江南",
}
MUNI = {110000, 120000, 310000, 500000}
OVERRIDE = {
    210200: "华北", 210800: "华北",
    320300: "华北",
    410300: "京畿", 411200: "京畿", 411300: "京畿", 411500: "京畿", 411700: "京畿",
    420300: "京畿", 420600: "京畿", 421300: "京畿", 420800: "京畿",
    420500: "云贵", 422800: "云贵",
    430800: "云贵", 431200: "云贵", 433100: "云贵",
    450400: "江南", 450800: "江南", 450900: "江南",
    510400: "云贵", 513400: "云贵",
    513200: "青藏", 513300: "青藏",
    623000: "青藏",
}
VN_REGIONS = {"Đông Nam Bộ", "Đông Bắc", "Đồng Bằng Sông Hồng"}


def smooth_line(points, samples=9):
    pts = [points[0]] + list(points) + [points[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = [np.array(p, float) for p in
                          (pts[i - 1], pts[i], pts[i + 1], pts[i + 2])]
        for t in np.linspace(0, 1, samples, endpoint=False):
            t2, t3 = t * t, t * t * t
            q = 0.5 * ((2 * p1) + (-p0 + p2) * t
                       + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                       + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)
            out.append((float(q[0]), float(q[1])))
    out.append(tuple(points[-1]))
    return out


def noisy_line(points, amp=0.12, seed=11):
    rng = np.random.default_rng(seed)
    jittered = [(x + rng.uniform(-amp, amp), y + rng.uniform(-amp, amp))
                for x, y in points]
    return smooth_line(jittered, 9)


# 西北：巴尔喀什湖—天山—帕米尔—兴都库什
# 只裁北缘（阿尔泰—巴尔喀什—楚河一线），西、南两侧保留真实边界，避免帕米尔出现 V 形
NW_LINE = [(86.2, 49.4), (85.0, 48.8), (83.5, 48.3), (82.0, 47.7),
           (80.5, 47.4), (79.0, 47.6), (77.0, 47.6), (75.0, 47.5),
           (73.0, 47.4), (71.5, 46.5)]
NW_NOISY = noisy_line(NW_LINE, amp=0.05, seed=11)
NW_KEEP = Polygon(NW_NOISY + [(60, 45.8), (60, 30), (110, 30), (110, 60), (60, 60)])

# 东北：逐段采样外兴安岭山体南缘（0.25° 一格），不再用均匀控制点
def _stanovoy_foot():
    path = os.path.join(NE, "regions", "ne_10m_geography_regions_polys.shp")
    rr = shapefile.Reader(path, encoding="utf-8")
    poly = None
    for sr in rr.iterShapeRecords():
        if sr.record.as_dict().get("NAME") == "STANOVOY RANGE":
            poly = shape(sr.shape.__geo_interface__)
            break
    if poly is None:
        return []
    from shapely.geometry import LineString

    out = []
    for lon in np.arange(123.0, 135.26, 0.25):
        inter = poly.boundary.intersection(LineString([(lon, 50), (lon, 60)]))
        ys = []
        if not inter.is_empty:
            for g in (inter.geoms if hasattr(inter, "geoms") else [inter]):
                ys.extend([p[1] for p in g.coords])
        if ys:
            out.append((float(lon), float(min(ys))))
    # 中值滤波：去掉个别断点造成的尖刺
    vals = [y for _, y in out]
    smooth = []
    for i in range(len(vals)):
        w = sorted(vals[max(0, i - 2):i + 3])
        smooth.append(w[len(w) // 2])
    return [(x, y) for (x, _), y in zip(out, smooth)]


NE_LINE = ([(118.0, 56.2), (120.0, 55.9), (121.5, 55.7)]
           + _stanovoy_foot()
           + [(135.5, 54.5), (136.5, 54.3)])
NE_SMOOTH = smooth_line(NE_LINE, 3)
NE_SOUTH = Polygon(NE_SMOOTH + [(150, 55.0), (150, 25), (115, 25), (115, 60)])


def proj(geom):
    g = transform(TR.transform, geom)
    if not g.is_valid:
        g = shapely.make_valid(g)
    return g


def clean(geom, simplify_m=700):
    g = shapely.make_valid(geom).buffer(0)
    if simplify_m:
        g = g.simplify(simplify_m, preserve_topology=True)
    return g


def drop_holes(geom):
    polys = list(geom.geoms) if hasattr(geom, "geoms") else [geom]
    out = [Polygon(p.exterior) for p in polys if p.area > 0]
    if not out:
        return geom
    return MultiPolygon(out) if len(out) > 1 else out[0]


def add(bucket, key, geom):
    bucket.setdefault(key, []).append(geom)


def main():
    t0 = time.time()
    states = {s: [] for s in STATES}
    extra = {"琉球": []}

    # ---------- China ----------
    top = json.load(open(os.path.join(DATAV, "100000_full.json"), encoding="utf-8"))
    prov_geoms = {}
    for f in top["features"]:
        code = str(f["properties"].get("adcode"))
        if code.isdigit():
            prov_geoms[int(code)] = f["geometry"]

    n_cn = 0
    for pcode, geom in prov_geoms.items():
        if pcode not in PROV_DEFAULT:
            continue
        state = PROV_DEFAULT[pcode]
        if pcode in MUNI or pcode in (710000, 810000, 820000):
            add(states, state, proj(shape(geom)))
            n_cn += 1
            continue
        fn = os.path.join(DATAV, "%06d_full.json" % pcode)
        if not os.path.exists(fn):
            add(states, state, proj(shape(geom)))
            n_cn += 1
            continue
        d = json.load(open(fn, encoding="utf-8"))
        for feat in d["features"]:
            code = feat["properties"].get("adcode")
            if code is None:
                continue
            try:
                code_i = int(code)
            except (TypeError, ValueError):
                continue
            add(states, OVERRIDE.get(code_i, state), proj(shape(feat["geometry"])))
            n_cn += 1

    # ---------- Natural Earth admin-1 ----------
    r1 = shapefile.Reader(os.path.join(NE, "admin1", "ne_10m_admin_1_states_provinces.shp"),
                          encoding="utf-8")
    ne_assign = {}
    for admin in ("Mongolia", "North Korea", "South Korea", "Laos"):
        ne_assign[admin] = "*"
    for nm in ("Amur", "Yevrey", "Khabarovsk", "Primor'ye", "Sakhalin"):
        ne_assign[("Russia", nm)] = "东北"
    for nm in ("Gorno-Altay", "Tuva", "Buryat", "Chita"):
        ne_assign[("Russia", nm)] = "蒙古"
    for nm in ("Almaty", "Almaty City", "Zhambyl", "East Kazakhstan", "Qaraghandy", "South Kazakhstan", "Kyzylorda"):
        ne_assign[("Kazakhstan", nm)] = "西北"
    ne_assign[("Tajikistan", "Gorno-Badakhshan")] = "西北"
    ne_assign[("India", "Arunachal Pradesh")] = "青藏"
    ne_assign[("Japan", "Okinawa")] = "琉球"

    n_ne = 0
    for sr in r1.iterShapeRecords():
        rec = sr.record.as_dict()
        admin, name = rec.get("admin"), rec.get("name")
        st = None
        if ne_assign.get(admin) == "*" and admin != "Laos":
            st = {"Mongolia": "蒙古", "North Korea": "东北",
                  "South Korea": "东北"}.get(admin)
        if admin == "Laos":
            st = "云贵"
        if admin == "Kyrgyzstan":
            st = "西北"
        if (admin, name) in ne_assign:
            st = ne_assign[(admin, name)]
        if admin == "Vietnam" and name not in VN_REGIONS:
            if shape(sr.shape.__geo_interface__).centroid.y >= 12.0:
                st = "云贵"
        if st == "琉球":
            add(extra, "琉球", proj(shape(sr.shape.__geo_interface__)))
            n_ne += 1
        elif st:
            g = shape(sr.shape.__geo_interface__)

            if not g.is_empty:
                add(states, st, proj(g))
                n_ne += 1

    print("china", n_cn, "ne", n_ne, "elapsed", round(time.time() - t0, 1))

    # ---------- assemble ----------
    state_geoms = {}
    for s in STATES:
        g = unary_union([clean(x) for x in states[s]])
        state_geoms[s] = drop_holes(clean(g))
        print(s, "area km2", round(state_geoms[s].area / 1e6))

    # 东北按外兴安岭南麓裁切
    state_geoms["东北"] = drop_holes(clean(
        state_geoms["东北"].intersection(proj(NE_SOUTH))))
    # 近岸小岛：从俄国 admin0 多边形里取鄂霍次克海岸外的独立小岛（不取半岛/大陆）
    shan_parts = []
    rr0 = shapefile.Reader(os.path.join(NE, "admin0",
                                        "ne_10m_admin_0_countries.shp"),
                           encoding="utf-8")
    for sr in rr0.iterShapeRecords():
        if sr.record.as_dict().get("ADMIN") != "Russia":
            continue
        g = shape(sr.shape.__geo_interface__)
        for p in (g.geoms if hasattr(g, "geoms") else [g]):
            c = p.centroid
            if 136.0 < c.x < 141.5 and 53.5 < c.y < 56.0:
                shan_parts.append(proj(p))
    if shan_parts:
        shan = unary_union(shan_parts)
        state_geoms["东北"] = drop_holes(clean(
            state_geoms["东北"].union(shan)))

    # 西北按设定西界裁切（巴尔喀什湖—天山—帕米尔）

    state_geoms["西北"] = drop_holes(clean(
        state_geoms["西北"].buffer(50000, join_style=1).buffer(-50000, join_style=1)))
    state_geoms["西北"] = drop_holes(clean(
        state_geoms["西北"].buffer(-15000, join_style=1).buffer(15000, join_style=1)))

    empire = unary_union(list(state_geoms.values()))
    empire = drop_holes(clean(empire))
    print("empire area km2", round(empire.area / 1e6))

    # ---------- neighbours ----------
    r0 = shapefile.Reader(os.path.join(NE, "admin0", "ne_10m_admin_0_countries.shp"),
                          encoding="utf-8")
    bbox = Polygon([(15, -30), (210, -30), (210, 88), (15, 88)])
    neigh = []
    for sr in r0.iterShapeRecords():
        g = shape(sr.shape.__geo_interface__)
        if not g.intersects(bbox):
            continue
        g = g.intersection(bbox)
        if not g.is_empty:
            neigh.append(proj(g))
    neighbours = clean(unary_union(neigh), simplify_m=1200)
    neighbours = neighbours.difference(empire.buffer(1500))
    print("neighbours", round(time.time() - t0, 1))

    # ---------- lakes & rivers ----------
    def read_lines(path, max_rank):
        rr = shapefile.Reader(path, encoding="utf-8")
        out = []
        for sr in rr.iterShapeRecords():
            d = sr.record.as_dict()
            if d.get("scalerank", 99) > max_rank:
                continue
            g = shape(sr.shape.__geo_interface__)
            if not g.is_empty:
                out.append((d.get("name_zh") or d.get("name") or "", proj(g)))
        return out

    lakes = read_lines(os.path.join(NE, "lakes", "ne_10m_lakes.shp"), 8)
    rivers = read_lines(os.path.join(NE, "rivers", "ne_10m_rivers_lake_centerlines.shp"), 6)

    # ---------- terrain ----------
    rt = shapefile.Reader(os.path.join(NE, "regions", "ne_10m_geography_regions_polys.shp"),
                          encoding="utf-8")
    terrain = []
    keep_cls = {"Range/mtn", "Plateau", "Desert", "Basin", "Plain", "Lowland",
                "Geoarea", "Valley", "Gorge", "Pen/cape"}
    for sr in rt.iterShapeRecords():
        rec = sr.record.as_dict()
        if rec.get("REGION") != "Asia" or rec.get("FEATURECLA") not in keep_cls:
            continue
        g = shape(sr.shape.__geo_interface__)
        if not g.intersects(bbox):
            continue
        g = proj(g.intersection(bbox))
        clipped = g.intersection(empire)
        try:
            clipped = clipped.difference(shan.buffer(5000))
        except NameError:
            pass
        if not clipped.is_empty:
            terrain.append((rec["FEATURECLA"], rec.get("NAME_ZH") or rec.get("NAME") or "",
                            clean(clipped, 1500)))

    islands = []
    for sr in rt.iterShapeRecords():
        rec = sr.record.as_dict()
        if rec.get("NAME") in ("Paracel Islands", "Spratly Islands",
                               "RYÜKYÜ ISLANDS", "Okinawa"):
            islands.append((rec.get("NAME"), rec.get("NAME_ZH") or "",
                            proj(shape(sr.shape.__geo_interface__))))

    data = {
        "states": state_geoms,
        "empire": empire,
        "neighbours": neighbours,
        "lakes": lakes,
        "rivers": rivers,
        "okinawa": extra["琉球"],
        "terrain": terrain,
        "islands": islands,
    }
    with open(OUT, "wb") as fh:
        pickle.dump(data, fh)
    print("saved", OUT, os.path.getsize(OUT), "bytes", round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    main()








