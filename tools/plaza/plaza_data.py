"""国家广场与广场建筑群 —— 2D 总平面与 3D 体量白模共用的唯一数据源。

坐标系与宫城模型完全一致：原点取**宫城平面中心**，+x 向东、+y 向北，单位米。
这样广场的 .glb 与 `tools/palace/` 的宫城 .glb 可以直接叠在同一场景里。

口径分三层：
  【设定】= 《长安城市志》《总设定》写明的数字（出处见行内注释）；
  【推定】= 建筑单体面宽进深、层数、檐高、前庭与围墙等按国家级仪典建筑比例反推；
  【判读】= 设定两处数字互相打架时，本模型采取的读法（逐条写在 README「口径」节）。

主要出处：
  设定/长安城市志.md                        卷三 内城表（广场 45 ha、大会堂 20 ha、
                                             议事大楼 8 ha、政治博物馆 12 ha、中轴里程）
  设定/总设定·第十六编·长安与国家象征体系.md  二、国家广场与国家大会堂（600×800 m、三厅）
  研究/方案·继位大典与宫城启闭（草案）.md       阅兵台设于承天门外、检阅车走广场东侧道
  设定/国家象征物(2026).md                    国旗、国徽（广场升旗用）

与宫城数据的接口：
  宫城南墙外皮 y = -961/2 - 墙厚/2 = -483.5
  护城河南岸 y = -483.5 - 52 = -535.5
  承天门城台 x ∈ [-48, 48]、y ∈ [-492, -448]（取自 palace_data.STRUCTS）
"""

from __future__ import annotations

# ---------------------------------------------------------------- 宫城接口
PALACE = {
    "width": 753.0,          # 【设定】宫城东西
    "depth": 961.0,          # 【设定】宫城南北
    "wall_t": 6.0,           # 【推定】宫城墙厚（palace_data）
    "moat_w": 52.0,          # 【设定】护城河宽
    "south_wall_face": -480.5,   # -961/2
    "south_wall_outer": -483.5,  # 含墙厚
    "moat_bank_south": -535.5,   # 护城河南岸 = 广场北界
    "gate": {"name": "承天门", "w": 96.0, "d": 44.0, "cy": -470.0},
}

# ---------------------------------------------------------------- 广场本体
# 【设定】东西 600 m、南北 800 m；表列 45 ha。
# 【判读】45 ha = 600 × 750，与 800 m 的差 50 m 读作北端「仪典台区」：
#          护城河南岸起 50 m 为阅兵台与仪典前区（3 ha），其余 750 m 为广场铺装（45 ha）。
PLAZA = {
    "name": "国家广场",
    "width": 600.0,          # 【设定】
    "depth": 800.0,          # 【设定】自护城河南岸至广场南端
    "x0": -300.0,
    "x1": 300.0,
    "y_north": -535.5,       # 【设定·接口】护城河南岸
    "y_south": -1335.5,      # y_north - 800
    "terrace_depth": 50.0,   # 【判读】北端仪典台区（阅兵台所在）
    "paving_depth": 750.0,   # 【判读】= 45 ha / 600 m
    "area_ha": 48.0,         # 600 × 800
    "paving_ha": 45.0,       # 表列 45 ha
}

# 广场上的构筑物
FEATURES = {
    # 承天门前的跨护城河石桥：与城门同宽 【推定】
    "bridge": {"name": "承天门桥", "x0": -48.0, "x1": 48.0,
               "y0": -535.5, "y1": -483.5, "h": 1.2},
    # 北端 50 m 仪典台区：整体抬高一阶 【推定】
    "terrace": {"name": "仪典台区", "x0": -300.0, "x1": 300.0,
                "y0": -585.5, "y1": -535.5, "h": 0.9},
    # 阅兵台：设于承天门外（《继位大典》）；正对中轴，面南 【推定】
    "review_stand": {"name": "阅兵台", "x0": -42.0, "x1": 42.0,
                     "y0": -569.5, "y1": -551.5, "h": 4.5},
    # 中轴御道 40 m 宽 【推定】
    "axis_road": {"name": "中轴御道", "x0": -20.0, "x1": 20.0,
                  "y0": -1335.5, "y1": -585.5},
    # 广场东侧道 12 m：检阅车沿线（《继位大典》「沿广场东侧道检阅」）【设定·功能】
    "east_road": {"name": "广场东侧道", "x0": 276.0, "x1": 288.0,
                  "y0": -1335.5, "y1": -585.5},
}

# ---------------------------------------------------------------- 广场建筑群
# 四至都是【判读】：由「广场两侧 + 三块占地」反推，复算见 README。
SITES = [
    {"key": "hall", "name": "国家大会堂", "x0": -550.0, "x1": -300.0,
     "y0": -1335.5, "y1": -535.5, "ha_doc": 20.0,
     "note": "广场西侧；250 × 800 m = 20 ha；三厅共用外墙与安检，各自独立入口"},
    {"key": "council", "name": "国家议会议事大楼", "x0": 300.0, "x1": 400.0,
     "y0": -1335.5, "y1": -535.5, "ha_doc": 8.0,
     "note": "广场东侧；100 × 800 m = 8 ha；约 1,100 席"},
    {"key": "museum", "name": "国家政治博物馆", "x0": -300.0, "x1": 300.0,
     "y0": -1535.5, "y1": -1335.5, "ha_doc": 12.0,
     "note": "广场南端；600 × 200 m = 12 ha；馆内设大革命主题馆"},
]

# 单体体块：kind 决定 2D 填充与 3D 以后的做法
#   main 主体 / wing 侧厅或配楼 / portico 门廊 / chamber 会议厅 / attic 屋顶层
MASSES = [
    # ── 国家大会堂：200 × 340 m，南北三厅，面东（朝广场）
    {"key": "hall-main", "parent": "hall", "name": "国家大会堂",
     "x0": -540.0, "x1": -340.0, "y0": -1105.5, "y1": -765.5,
     "h": 26.0, "floors": 3, "kind": "main"},
    {"key": "hall-s", "parent": "hall", "name": "左厅（八州厅＋宣政厅）",
     "x0": -540.0, "x1": -340.0, "y0": -1105.5, "y1": -1005.5,
     "h": 22.0, "floors": 3, "kind": "wing"},
    {"key": "hall-c", "parent": "hall", "name": "中厅（万人大礼堂）",
     "x0": -540.0, "x1": -340.0, "y0": -1005.5, "y1": -865.5,
     "h": 34.0, "floors": 2, "kind": "chamber"},
    {"key": "hall-n", "parent": "hall", "name": "右厅（宴会厅）",
     "x0": -540.0, "x1": -340.0, "y0": -865.5, "y1": -765.5,
     "h": 22.0, "floors": 3, "kind": "wing"},
    *[{"key": f"hall-portico-{t}", "parent": "hall", "name": "门廊",
       "x0": -340.0, "x1": -326.0, "y0": cy - 30.0, "y1": cy + 30.0,
       "h": 18.0, "floors": 1, "kind": "portico"}
      for t, cy in (("n", -815.5), ("c", -935.5), ("s", -1055.5))],

    # ── 国家议会议事大楼：80 × 300 m，面西（朝广场）
    {"key": "council-main", "parent": "council", "name": "国家议会议事大楼",
     "x0": 310.0, "x1": 390.0, "y0": -1085.5, "y1": -785.5,
     "h": 24.0, "floors": 3, "kind": "main"},
    {"key": "council-chamber", "parent": "council", "name": "议事厅（1,100 席）",
     "x0": 322.0, "x1": 378.0, "y0": -981.5, "y1": -889.5,
     "h": 30.0, "floors": 1, "kind": "chamber"},
    {"key": "council-portico", "parent": "council", "name": "门廊",
     "x0": 300.0, "x1": 312.0, "y0": -965.5, "y1": -905.5,
     "h": 16.0, "floors": 1, "kind": "portico"},

    # ── 国家政治博物馆：360 × 110 m，面北（朝广场）
    {"key": "museum-main", "parent": "museum", "name": "国家政治博物馆",
     "x0": -180.0, "x1": 180.0, "y0": -1500.5, "y1": -1390.5,
     "h": 21.0, "floors": 3, "kind": "main"},
    {"key": "museum-portico", "parent": "museum", "name": "门廊",
     "x0": -60.0, "x1": 60.0, "y0": -1390.5, "y1": -1372.5,
     "h": 15.0, "floors": 1, "kind": "portico"},
    {"key": "museum-wing", "parent": "museum", "name": "大革命主题馆",
     "x0": 184.0, "x1": 260.0, "y0": -1490.5, "y1": -1396.5,
     "h": 17.0, "floors": 2, "kind": "wing"},
]

# 围墙（建筑群共用安检与外墙；【推定】墙厚 1.5 m，高 3.5 m）
WALL_T = 1.5
WALL_H = 3.5
# 每段墙开口：东侧三厅各一门、西侧一座安检院门；议事与博物馆各一座正门
GATES = {
    "hall": [("E", -815.5, 18.0), ("E", -935.5, 26.0), ("E", -1055.5, 18.0)],
    "council": [("W", -935.5, 30.0), ("N", 350.0, 0.0), ("S", 350.0, 0.0)],
    "museum": [("N", 0.0, 40.0)],
}

# 周边道路（示意，【推定】24 m）
ROADS = [
    {"name": "西侧道路", "x0": -574.0, "x1": -550.0, "y0": -1535.5, "y1": -535.5},
    {"name": "东侧道路", "x0": 400.0, "x1": 424.0, "y0": -1535.5, "y1": -535.5},
    {"name": "南侧道路", "x0": -574.0, "x1": 424.0, "y0": -1559.5, "y1": -1535.5},
]

# 轴线（各段，供 2D 画虚线与 3D 摆旗杆/灯柱）
AXIS = {"x": 0.0}

# ---------------------------------------------------------------- 计算
def rect_ha(x0, x1, y0, y1):
    return abs((x1 - x0) * (y1 - y0)) / 10000.0


def mass_by_key(key):
    return next(m for m in MASSES if m["key"] == key)


def site(key):
    return next(s for s in SITES if s["key"] == key)


def stats():
    s = {
        "plaza_ha": rect_ha(PLAZA["x0"], PLAZA["x1"], PLAZA["y_north"], PLAZA["y_south"]),
        "paving_ha": rect_ha(PLAZA["x0"], PLAZA["x1"],
                             PLAZA["y_north"] - PLAZA["terrace_depth"], PLAZA["y_south"]),
        "terrace_ha": rect_ha(-300, 300, PLAZA["y_north"] - PLAZA["terrace_depth"],
                              PLAZA["y_north"]),
        "sites": {s["key"]: rect_ha(s["x0"], s["x1"], s["y0"], s["y1"]) for s in SITES},
        "footprints": {},
        "floor_ha": {},
    }
    for k in ("hall", "council", "museum"):
        f = 0.0
        for m in MASSES:
            if m["parent"] == k and m["key"] not in ("museum-wing",):
                f += rect_ha(m["x0"], m["x1"], m["y0"], m["y1"])
        s["footprints"][k] = f
        s["floor_ha"][k] = sum(
            rect_ha(m["x0"], m["x1"], m["y0"], m["y1"]) * m["floors"]
            for m in MASSES if m["parent"] == k and m["kind"] != "portico")
    return s


def check():
    """把数字对账打成一台账；build_plan.py --check 会打印。"""
    st = stats()
    lines = [
        f'广场总占地 {st["plaza_ha"]:.2f} ha（600×800）',
        f'广场铺装 {st["paving_ha"]:.2f} ha（600×750；表列 45）',
        f'仪典台区 {st["terrace_ha"]:.2f} ha（600×50）',
        f'大会堂 用地 {st["sites"]["hall"]:.2f} ha / 建筑占地 {st["footprints"]["hall"]:.2f} ha'
        f' / 建筑面积 {st["floor_ha"]["hall"]:.2f} ha（表列 20）',
        f'议事楼 用地 {st["sites"]["council"]:.2f} ha / 建筑占地 {st["footprints"]["council"]:.2f} ha'
        f' / 建筑面积 {st["floor_ha"]["council"]:.2f} ha（表列 8）',
        f'博物馆 用地 {st["sites"]["museum"]:.2f} ha / 建筑占地 {st["footprints"]["museum"]:.2f} ha'
        f' / 建筑面积 {st["floor_ha"]["museum"]:.2f} ha（表列 12）',
        f'广场南北 800 m 与中轴里程（承天门 6.45 − 永宁门 5.70 = 750 m）差 50 m，'
        f'内城 2,700 m 另与广场+博物馆 1,000 m 不相容；本模型只做广场建筑群，不含内城城墙。',
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(check())
