"""国家广场与广场建筑群 —— 2D 总平面与 3D 体量白模共用的唯一数据源。

坐标系与宫城模型完全一致：原点取**宫城平面中心**，+x 向东、+y 向北，单位米。
这样广场的 .glb 与 `tools/palace/` 的宫城 .glb 可以直接叠在同一场景里。

口径分三层：
  【设定】= 《长安城市志》《总设定》写明的数字（出处见行内注释）；
  【作者】= 2026-11-22 作者对建模的裁决（800 m 全铺装、阅兵台并入承天门、
            承天门前新设主干道、三座建筑放大）；
  【推定】= 建筑单体面宽进深、层数、檐高、前庭与围墙等按国家级仪典建筑比例反推。

主要出处：
  设定/长安城市志.md                        卷三 内城表（广场 45 ha、大会堂 20 ha、
                                             议事大楼 8 ha、政治博物馆 12 ha、中轴里程）
  设定/总设定·第十六编·长安与国家象征体系.md  二、国家广场与国家大会堂（600×800 m、三厅）
  研究/方案·继位大典与宫城启闭（草案）.md       阅兵台、检阅车走广场东侧道
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
    "moat_bank_south": -535.5,   # 护城河南岸＝承天门大街北缘
    "gate": {"name": "承天门", "w": 96.0, "d": 44.0, "cy": -470.0},
}

# ---------------------------------------------------------------- 承天门大街（新设）
# 【作者·2026-11-22】承天门前新设一条东西向主干道，关系类似长安街与天安门广场。
# 100 m ＝ 8 m 人行道 ×2 ＋ 84 m 车行道（含 6 m 中央分隔带）。
AVENUE = {
    "name": "承天门大街",
    "x0": -700.0, "x1": 560.0,
    "y_north": -535.5,       # 护城河南岸
    "y_south": -635.5,       # 广场北缘
    "width": 100.0,
    "sidewalk": 8.0,
    "median": 6.0,
    "note": "新设主干道；西往安定门、东往长乐门，轴线处与承天门桥相接",
}

# ---------------------------------------------------------------- 广场本体
# 【设定】东西 600 m、南北 800 m；【作者】800 m 全部铺装 = 48 ha。
# 表列 45 ha 与 600×800 = 48 ha 不一致，本模型从作者裁决取 48 ha，设定表待同步。
PLAZA = {
    "name": "国家广场",
    "width": 600.0,          # 【设定】
    "depth": 800.0,          # 【设定】
    "x0": -300.0,
    "x1": 300.0,
    "y_north": -635.5,       # 大街南缘
    "y_south": -1435.5,      # y_north - 800
    "area_ha": 48.0,         # 600 × 800
    "table_ha": 45.0,        # 设定表列，待同步
}

# 广场上的构筑物
FEATURES = {
    # 承天门前的跨护城河石桥：与城门同宽 【推定】
    "bridge": {"name": "承天门桥", "x0": -48.0, "x1": 48.0,
               "y0": -535.5, "y1": -483.5, "h": 1.2},
    # 阅兵台并入承天门城台（【作者】）；这里只画城台上的检阅平台
    "review": {"name": "阅兵台（承天门城台）", "x0": -34.0, "x1": 34.0,
               "y0": -492.0, "y1": -476.0, "h": 2.6},
    # 中轴御道 40 m 宽 【推定】
    "axis_road": {"name": "中轴御道", "x0": -20.0, "x1": 20.0,
                  "y0": -1435.5, "y1": -635.5},
    # 广场东侧道 12 m：检阅车沿线（《继位大典》「沿广场东侧道检阅」）【设定·功能】
    "east_road": {"name": "广场东侧道", "x0": 276.0, "x1": 288.0,
                  "y0": -1435.5, "y1": -635.5},
}

# ---------------------------------------------------------------- 广场建筑群
# 四至【判读】：西 250 m、东 160 m、南 600×200 m；20/8/12 ha 按**建筑面积**读。
SITES = [
    {"key": "hall", "name": "国家大会堂", "x0": -550.0, "x1": -300.0,
     "y0": -1435.5, "y1": -635.5, "ha": 20.0,
     "note": "广场西侧；250 × 800 m 院落；三厅共用外墙与安检，各自独立入口"},
    {"key": "council", "name": "国家议会议事大楼", "x0": 300.0, "x1": 460.0,
     "y0": -1435.5, "y1": -635.5, "ha": 12.8,
     "note": "广场东侧；160 × 800 m 院落；约 1,100 席"},
    {"key": "museum", "name": "国家政治博物馆", "x0": -300.0, "x1": 300.0,
     "y0": -1635.5, "y1": -1435.5, "ha": 12.0,
     "note": "广场南端；600 × 200 m 院落；馆内设大革命主题馆"},
]

# 单体体块：kind 决定 2D 填充与 3D 以后的做法
#   main 主体 / wing 侧厅或配楼 / portico 门廊 / chamber 会议厅（主体中部高体量）
MASSES = [
    # ── 国家大会堂：210 × 470 m，两层，南北三厅，面东（朝广场）
    {"key": "hall-s", "parent": "hall", "name": "左厅（八州厅＋宣政厅）",
     "x0": -540.0, "x1": -330.0, "y0": -1270.5, "y1": -1120.5,
     "h": 27.0, "floors": 2, "kind": "wing"},
    {"key": "hall-c", "parent": "hall", "name": "中厅（万人大礼堂）",
     "x0": -540.0, "x1": -330.0, "y0": -1120.5, "y1": -950.5,
     "h": 34.0, "floors": 2, "kind": "chamber"},
    {"key": "hall-n", "parent": "hall", "name": "右厅（宴会厅）",
     "x0": -540.0, "x1": -330.0, "y0": -950.5, "y1": -800.5,
     "h": 27.0, "floors": 2, "kind": "wing"},
    *[{"key": f"hall-portico-{t}", "parent": "hall", "name": "门廊",
       "x0": -330.0, "x1": -314.0, "y0": cy - 34.0, "y1": cy + 34.0,
       "h": 20.0, "floors": 1, "kind": "portico"}
      for t, cy in (("n", -875.5), ("c", -1035.5), ("s", -1195.5))],

    # ── 国家议会议事大楼：130 × 310 m，两层，面西（朝广场）；中部为议事厅高体量
    {"key": "council-main", "parent": "council", "name": "国家议会议事大楼",
     "x0": 315.0, "x1": 445.0, "y0": -1190.5, "y1": -880.5,
     "h": 26.0, "floors": 2, "kind": "main"},
    {"key": "council-chamber", "parent": "council", "name": "议事厅（1,100 席）",
     "x0": 335.0, "x1": 425.0, "y0": -1090.5, "y1": -980.5,
     "h": 32.0, "floors": 2, "kind": "chamber"},
    {"key": "council-portico", "parent": "council", "name": "门廊",
     "x0": 300.0, "x1": 315.0, "y0": -1065.5, "y1": -1005.5,
     "h": 18.0, "floors": 1, "kind": "portico"},

    # ── 国家政治博物馆：400 × 150 m，两层，面北（朝广场）；东段为大革命主题馆
    {"key": "museum-main", "parent": "museum", "name": "国家政治博物馆",
     "x0": -200.0, "x1": 200.0, "y0": -1610.5, "y1": -1460.5,
     "h": 24.0, "floors": 2, "kind": "main"},
    {"key": "museum-portico", "parent": "museum", "name": "门廊",
     "x0": -50.0, "x1": 50.0, "y0": -1460.5, "y1": -1440.5,
     "h": 18.0, "floors": 1, "kind": "portico"},
]

# 围墙（建筑群共用安检与外墙；【推定】墙厚 1.5 m，高 3.5 m）
WALL_T = 1.5
WALL_H = 3.5
GATES = {
    "hall": [("E", -875.5, 60.0), ("E", -1035.5, 68.0), ("E", -1195.5, 60.0)],
    "council": [("W", -1035.5, 60.0)],
    "museum": [("N", 0.0, 120.0)],
}

# 周边道路（示意，【推定】30 m）
ROADS = [
    {"name": "西侧道路", "x0": -580.0, "x1": -550.0, "y0": -1635.5, "y1": -635.5},
    {"name": "东侧道路", "x0": 460.0, "x1": 490.0, "y0": -1635.5, "y1": -635.5},
    {"name": "南侧道路", "x0": -580.0, "x1": 490.0, "y0": -1665.5, "y1": -1635.5},
]

# 轴线
AXIS = {"x": 0.0}

# ---------------------------------------------------------------- 计算
def rect_ha(x0, x1, y0, y1):
    return abs((x1 - x0) * (y1 - y0)) / 10000.0


def mass_by_key(key):
    return next(m for m in MASSES if m["key"] == key)


def site(key):
    return next(s for s in SITES if s["key"] == key)


def stats():
    st = {
        "plaza_ha": rect_ha(PLAZA["x0"], PLAZA["x1"], PLAZA["y_north"], PLAZA["y_south"]),
        "sites": {s["key"]: rect_ha(s["x0"], s["x1"], s["y0"], s["y1"]) for s in SITES},
        "footprints": {},
        "floor_ha": {},
    }
    footprint_keys = {
        "hall": ("hall-s", "hall-c", "hall-n"),
        "council": ("council-main",),
        "museum": ("museum-main",),
    }
    for k in ("hall", "council", "museum"):
        st["footprints"][k] = sum(
            rect_ha(*(mass_by_key(x)[p] for p in ("x0", "x1", "y0", "y1")))
            for x in footprint_keys[k])
        st["floor_ha"][k] = sum(
            rect_ha(*(mass_by_key(x)[p] for p in ("x0", "x1", "y0", "y1"))) * mass_by_key(x)["floors"]
            for x in footprint_keys[k])
    return st


def check():
    """把数字对账打成一台账；build_plan.py --check 会打印。"""
    st = stats()
    lines = [
        f'承天门大街 {AVENUE["width"]:.0f} m（{AVENUE["y_north"]:.1f} ~ {AVENUE["y_south"]:.1f}）',
        f'广场 {PLAZA["width"]:.0f}×{PLAZA["depth"]:.0f} m = {st["plaza_ha"]:.2f} ha'
        f'（设定表列 {PLAZA["table_ha"]:.0f} ha，按作者裁决取 48）',
        f'大会堂 用地 {st["sites"]["hall"]:.2f} ha / 建筑占地 {st["footprints"]["hall"]:.2f} ha'
        f' / 建筑面积 {st["floor_ha"]["hall"]:.2f} ha（设定 20）',
        f'议事楼 用地 {st["sites"]["council"]:.2f} ha / 建筑占地 {st["footprints"]["council"]:.2f} ha'
        f' / 建筑面积 {st["floor_ha"]["council"]:.2f} ha（设定 8）',
        f'博物馆 用地 {st["sites"]["museum"]:.2f} ha / 建筑占地 {st["footprints"]["museum"]:.2f} ha'
        f' / 建筑面积 {st["floor_ha"]["museum"]:.2f} ha（设定 12）',
        '广场南北 800 m + 博物馆 200 m 与内城 2,700 m 不相容；本模型只做广场建筑群，'
        '不含内城城墙与永宁门。',
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(check())
