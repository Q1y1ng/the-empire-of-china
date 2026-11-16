# -*- coding: utf-8 -*-
"""Build the 45-province (省级) geometries for the 2026 empire map.

Reuses the 八州 base module for projection, cleaning and the NE/NW border
clipping so both maps share exactly the same national outline.

Province = union of whole prefecture-level units (China, DataV) or whole
admin-1 units (Natural Earth 10m).  The split follows the 犬牙交错 rules in
《疆域与省界表(2026)》.
"""
import json
import os
import pickle
import time

import shapely
from shapely.geometry import MultiPolygon, Polygon, shape
from shapely.ops import unary_union

import prep_empire_map as base

BASE = base.BASE
DATAV = base.DATAV
NE = base.NE
OUT = os.path.join(os.path.dirname(base.OUT), "prepared_provinces.pkl")
OLD = base.OUT

proj = base.proj
clean = base.clean
drop_holes = base.drop_holes

# name: (州, 省会/市府, lon, lat)
PROV = {
    "长安市": ("京畿", "长安", 108.94, 34.34),
    "陕西省": ("京畿", "延安", 109.49, 36.60),
    "成都省": ("京畿", "成都", 104.07, 30.67),
    "重庆省": ("京畿", "重庆", 106.55, 29.56),
    "中原省": ("京畿", "洛阳", 112.45, 34.62),

    "辽宁": ("东北", "沈阳", 123.43, 41.80),
    "吉林": ("东北", "长春", 125.32, 43.82),
    "黑龙江": ("东北", "哈尔滨", 126.53, 45.80),
    "滨海": ("东北", "海参崴", 131.89, 43.12),
    "朝鲜": ("东北", "平壤", 125.75, 39.03),

    "漠南": ("蒙古", "呼和浩特", 111.75, 40.84),
    "河套": ("蒙古", "包头", 109.84, 40.66),
    "漠北": ("蒙古", "乌兰巴托", 106.92, 47.92),
    "科布多": ("蒙古", "科布多", 91.64, 48.01),
    "阿尔泰": ("蒙古", "乌列盖", 90.05, 48.97),

    "河西": ("西北", "肃州", 98.49, 39.73),
    "甘宁": ("西北", "兰州", 103.82, 36.06),
    "新疆": ("西北", "乌鲁木齐", 87.62, 43.82),
    "帕米尔": ("西北", "喀什", 75.99, 39.47),

    "河北": ("华北", "北京", 116.40, 39.90),
    "山西": ("华北", "太原", 112.55, 37.87),
    "山东": ("华北", "济南", 117.12, 36.65),
    "河南": ("华北", "郑州", 113.63, 34.75),
    "辽南": ("华北", "大连", 121.62, 38.92),
    "北海": ("华北", "天津", 117.20, 39.13),

    "上海": ("江南", "上海", 121.47, 31.23),
    "江苏": ("江南", "南京", 118.80, 32.06),
    "浙江": ("江南", "杭州", 120.15, 30.27),
    "安徽": ("江南", "合肥", 117.28, 31.86),
    "江西": ("江南", "南昌", 115.89, 28.68),
    "福建": ("江南", "福州", 119.30, 26.08),
    "台湾": ("江南", "台北", 121.52, 25.03),
    "岭南": ("江南", "广州", 113.26, 23.13),

    "云南": ("云贵", "昆明", 102.83, 24.88),
    "贵州": ("云贵", "贵阳", 106.63, 26.65),
    "广西": ("云贵", "桂林", 110.29, 25.27),
    "南宁": ("云贵", "南宁", 108.37, 22.82),
    "河内": ("云贵", "河内", 105.85, 21.03),
    "澜沧": ("云贵", "万象", 102.63, 17.97),
    "北部湾": ("云贵", "海口", 110.20, 20.04),

    "青海": ("青藏", "西宁", 101.78, 36.62),
    "西藏": ("青藏", "拉萨", 91.14, 29.65),
    "藏南": ("青藏", "泽当", 91.77, 29.24),
    "康巴": ("青藏", "昌都", 97.17, 31.14),
    "喜马拉雅": ("青藏", "日喀则", 88.88, 29.27),
}

CN = {
    # 京畿：陕北归陕西，关中西部归陕西，汉中安康归成都
    "长安市": [610100, 610400],
    "陕西省": [610200, 610300, 610500, 610600, 610800, 611000],
    "成都省": [510100, 510300, 510500, 510600, 510700, 510800, 510900, 511000,
            511100, 511300, 511400, 511500, 511600, 511700, 511800, 511900,
            512000, 610700, 610900],
    "重庆省": [500000],
    "中原省": [410300, 410400, 411200, 411300, 411500, 411700, 419001,
            420300, 420600, 420800, 421300, 429021],

    # 东北
    "辽宁": [210100, 210300, 210400, 210500, 210600, 210700, 210900, 211000,
           211100, 211200, 211300, 211400],
    "辽南": [210200, 210800],
    "吉林": [220100, 220200, 220300, 220400, 220500, 220600, 220700, 220800, 222400],
    "黑龙江": [230100, 230200, 230300, 230400, 230500, 230600, 230700, 230800,
            230900, 231000, 231100, 231200, 232700],

    # 蒙古（国内部分）
    "漠南": [150100, 150400, 150500, 150900, 152200, 152500],
    "河套": [150200, 150300, 150600, 150800, 152900],
    "漠北": [150700],

    # 西北
    "河西": [620200, 620300, 620600, 620700, 620900],
    "甘宁": [620100, 620400, 620500, 620800, 621000, 621100, 621200, 622900,
            640100, 640200, 640300, 640400, 640500],
    "新疆": [650100, 650200, 650400, 650500, 652300, 652700, 652800, 652900,
            654000, 654200, 654300, 659001, 659002, 659004, 659005, 659006,
            659007, 659008, 659010],
    "帕米尔": [653000, 653100, 653200, 659003, 659009],

    # 华北
    "河北": [110000, 130100, 130400, 130500, 130600, 130700, 130800, 131000, 131100],
    "山西": [140100, 140200, 140300, 140400, 140500, 140600, 140700, 140800,
           140900, 141000, 141100],
    "山东": [320300, 370100, 370200, 370300, 370400, 370600, 370700, 370800,
           370900, 371000, 371100, 371300, 371500, 371700],
    "河南": [410100, 410200, 410500, 410600, 410700, 410800, 410900, 411000,
           411100, 411400, 411600],
    "北海": [120000, 130200, 130300, 130900, 370500, 371400, 371600],

    # 江南
    "上海": [310000],
    "江苏": [320100, 320200, 320400, 320500, 320600, 320700, 320800, 320900,
           321000, 321100, 321200, 321300],
    "浙江": [330100, 330200, 330300, 330400, 330500, 330600, 330700, 330800,
           330900, 331000, 331100],
    "安徽": [340100, 340200, 340300, 340400, 340500, 340600, 340700, 340800,
           341000, 341100, 341200, 341300, 341500, 341600, 341700, 341800,
           420100, 420200, 420700, 420900, 421000, 421100, 421200,
           429004, 429005, 429006],
    "江西": [360100, 360200, 360300, 360400, 360500, 360600, 360700, 360800,
           360900, 361000, 361100,
           430100, 430200, 430300, 430500, 430600, 430700, 430900, 431300],
    "福建": [350100, 350200, 350300, 350400, 350500, 350600, 350700, 350800, 350900],
    "台湾": [710000],
    "岭南": [440100, 440200, 440300, 440400, 440500, 440600, 440700, 440800,
           440900, 441200, 441300, 441400, 441500, 441600, 441700, 441800,
           441900, 442000, 445100, 445200, 445300,
           430400, 431000, 431100, 450400, 450800, 450900, 810000, 820000],

    # 云贵
    "云南": [530100, 530300, 530400, 530500, 530600, 530700, 530800, 530900,
           532300, 532500, 532600, 532800, 532900, 533100, 533300, 533400, 513400],
    "贵州": [520100, 520200, 520300, 520400, 520500, 520600, 522300, 522600, 522700,
           430800, 431200, 433100, 420500, 422800],
    "广西": [450200, 450300, 451100, 451200, 451300],
    "南宁": [450100, 451000, 451400],
    "北部湾": [450500, 450600, 450700, 460100, 460200, 460400, 469001,
            469002, 469005, 469006, 469007, 469021, 469022, 469023, 469024,
            469025, 469026, 469027, 469028, 469029, 469030],

    # 青藏
    "青海": [630100, 630200, 632200, 632300, 632500, 632600, 632700, 632800, 623000],
    "西藏": [540100, 540600, 542500],
    "藏南": [540400, 540500],
    "康巴": [540300, 513200, 513300],
    "喜马拉雅": [540200],
}

TOPCODES = {110000, 120000, 310000, 500000, 710000, 810000, 820000}

NE_ASSIGN = {
    "朝鲜": [("North Korea", "*"), ("South Korea", "*")],
    "滨海": [("Russia", "Amur"), ("Russia", "Yevrey"), ("Russia", "Khabarovsk"),
           ("Russia", "Primor'ye"), ("Russia", "Sakhalin")],
    "漠北": [("Mongolia", "*"), ("Russia", "Chita")],
    "科布多": [("Russia", "Tuva"), ("Russia", "Buryat")],
    "新疆": [("Kazakhstan", "Almaty"), ("Kazakhstan", "Almaty City"),
           ("Kazakhstan", "East Kazakhstan"), ("Kazakhstan", "Qaraghandy")],
    "帕米尔": [("Kyrgyzstan", "*"),
            ("Tajikistan", "Gorno-Badakhshan"),
            ("Kazakhstan", "Zhambyl"), ("Kazakhstan", "Qyzylorda"),
            ("Kazakhstan", "South Kazakhstan")],
    "澜沧": [("Laos", "*")],
    "河内": [("Vietnam", "*")],
    "藏南": [("India", "Arunachal Pradesh")],
}
# Mongolia: 阿尔泰 = 西部阿尔泰山地，其余归漠北
MONGOLIA_ALTAY = {"Bayan-Ölgiy", "Uvs", "Govi-Altay"}
MONGOLIA_KHOVD = {"Hovd", "Dzavhan"}
# Vietnam 的 3 个大区多边形与省重叠，跳过
VN_DUP = {"Đông Bắc", "Đông Nam Bộ", "Đồng Bằng Sông Hồng"}


def main():
    t0 = time.time()
    provs = {k: [] for k in PROV}

    # ---------- China: prefecture units (stored inside each 省_full.json) ----------
    top = json.load(open(os.path.join(DATAV, "100000_full.json"), encoding="utf-8"))
    tops = {}
    for f in top["features"]:
        code = str(f["properties"].get("adcode"))
        if code.isdigit():
            tops[int(code)] = f["geometry"]

    pref = {}
    for fn in sorted(os.listdir(DATAV)):
        if not fn.endswith("_full.json") or fn == "100000_full.json":
            continue
        for feat in json.load(open(os.path.join(DATAV, fn), encoding="utf-8"))["features"]:
            code = feat["properties"].get("adcode")
            g = feat.get("geometry")
            if code is None or not g:
                continue
            pref[int(code)] = g
    print("prefecture units indexed", len(pref))

    assigned = {}
    for prov, codes in CN.items():
        for c in codes:
            if c in assigned:
                raise SystemExit("duplicate %d in %s and %s" % (c, assigned[c], prov))
            assigned[c] = prov

    n = 0
    missing = []
    for code, prov in sorted(assigned.items()):
        g = None
        if code not in TOPCODES:
            g = pref.get(code) or tops.get(code)
        else:
            g = tops.get(code)
        if g is None:
            missing.append(code)
            continue
        provs[prov].append(proj(shape(g)))
        n += 1
    print("china units", n, "missing", missing)

    # ---------- Natural Earth admin-1 ----------
    import shapefile
    r1 = shapefile.Reader(os.path.join(NE, "admin1", "ne_10m_admin_1_states_provinces.shp"),
                          encoding="utf-8")
    ne_n = 0
    for sr in r1.iterShapeRecords():
        rec = sr.record.as_dict()
        admin, name = rec.get("admin"), rec.get("name")
        prov = None
        for p, rules in NE_ASSIGN.items():
            for a, nm in rules:
                if a == admin and (nm == "*" or nm == name):
                    prov = p
                    break
            if prov:
                break
        if admin == "Mongolia" and prov == "漠北":
            if name in MONGOLIA_ALTAY:
                prov = "阿尔泰"
            elif name in MONGOLIA_KHOVD:
                prov = "科布多"
        if admin == "Vietnam" and name in VN_DUP:
            continue
        if prov is None:
            continue
        g = shape(sr.shape.__geo_interface__)
        if g.is_empty:
            continue
        provs[prov].append(proj(g))
        ne_n += 1
    print("ne units", ne_n)

    # ---------- assemble ----------
    geoms = {}
    for p, parts in provs.items():
        if not parts:
            print("!! empty", p)
            continue
        g = unary_union([clean(x) for x in parts])
        g = drop_holes(clean(g))
        parts2 = [x for x in (g.geoms if hasattr(g, "geoms") else [g])
                  if x.area > 1e6]
        g = MultiPolygon(parts2) if len(parts2) > 1 else parts2[0]
        geoms[p] = g

    # 东北按外兴安岭南麓裁切
    clip = proj(base.NE_SOUTH)
    for p in ("辽宁", "吉林", "黑龙江", "滨海", "朝鲜"):
        geoms[p] = drop_holes(clean(geoms[p].intersection(clip)))

    # 尚塔尔群岛等近岸小岛归滨海
    rr0 = shapefile.Reader(os.path.join(NE, "admin0", "ne_10m_admin_0_countries.shp"),
                           encoding="utf-8")
    shan_parts = []
    for sr in rr0.iterShapeRecords():
        if sr.record.as_dict().get("ADMIN") != "Russia":
            continue
        g = shape(sr.shape.__geo_interface__)
        for p in (g.geoms if hasattr(g, "geoms") else [g]):
            c = p.centroid
            if 136.0 < c.x < 141.5 and 53.5 < c.y < 56.0:
                shan_parts.append(proj(p))
    shan = unary_union(shan_parts) if shan_parts else None
    if shan is not None:
        geoms["滨海"] = drop_holes(clean(geoms["滨海"].union(shan)))

    # ---------- coverage check: China must be tiled completely ----------
    from pyproj import Transformer
    inv = Transformer.from_crs(base.PROJ, "EPSG:4326", always_xy=True)
    cn_all = unary_union([proj(shape(g)) for g in pref.values()])
    left = cn_all.difference(unary_union(list(geoms.values())))
    bad = [p for p in (left.geoms if hasattr(left, "geoms") else [left])
           if p.area > 50e6]
    print("unassigned China area km2", round(left.area / 1e6), "patches>50km2", len(bad))
    for p in sorted(bad, key=lambda q: -q.area)[:12]:
        c = p.centroid
        lon, lat = inv.transform(c.x, c.y)
        print("   gap %7.0f km2  %6.2f %6.2f" % (p.area / 1e6, lon, lat))

    states = {}
    for p, (st, _c, _x, _y) in PROV.items():
        states.setdefault(st, []).append(geoms[p])
    state_geoms = {s: drop_holes(clean(unary_union(g))) for s, g in states.items()}
    empire = drop_holes(clean(unary_union(list(geoms.values()))))

    for st, g in sorted(state_geoms.items(), key=lambda kv: -kv[1].area):
        print("state %-3s %8.0f km2" % (st, g.area / 1e6))
    print("empire", round(empire.area / 1e6), "km2")

    # ---------- reuse background layers ----------
    old = pickle.load(open(OLD, "rb"))
    terrain = []
    for cls, name, g in old["terrain"]:
        c = g.intersection(empire)
        if not c.is_empty:
            terrain.append((cls, name, clean(c, 1500)))

    # neighbours rebuilt against the new outline
    bbox = Polygon([(15, -30), (210, -30), (210, 88), (15, 88)])
    neigh = []
    for sr in rr0.iterShapeRecords():
        g = shape(sr.shape.__geo_interface__)
        if not g.intersects(bbox):
            continue
        g = g.intersection(bbox)
        if not g.is_empty:
            neigh.append(proj(g))
    neighbours = clean(unary_union(neigh), simplify_m=1200)
    neighbours = neighbours.difference(empire.buffer(1500))

    data = {
        "provinces": geoms,
        "states": state_geoms,
        "empire": empire,
        "neighbours": neighbours,
        "lakes": old["lakes"],
        "rivers": old["rivers"],
        "okinawa": old["okinawa"],
        "terrain": terrain,
        "islands": old["islands"],
    }
    with open(OUT, "wb") as fh:
        pickle.dump(data, fh)

    print("--- province areas (万 km2) ---")
    tot = 0
    for p, (st, cap, _x, _y) in PROV.items():
        a = geoms[p].area / 1e10
        tot += a
        print("%-5s %-3s %-4s %7.1f" % (p, st, cap, a))
    print("sum", round(tot, 1), "saved", OUT, round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    main()
