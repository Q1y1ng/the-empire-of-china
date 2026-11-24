"""宫城（皇宫）几何数据总表 —— 2D 总平面与 3D 体量白模共用的唯一数据源。

坐标系：原点取宫城平面中心；+x 向东、+y 向北；单位为米。

口径分三层：
  【设定】= 《中华帝国》正式设定写明的数字（出处见行内注释）；
  【宫式】= 按故宫（紫禁城）的院落语法排布：外朝三殿同台、内廷后三宫、六宫各成院落、
            值房沿墙成排、内金水河与五桥、四隅角楼；
  【推定】= 单体面阔进深、殿身高度、门楼形制等按明官式比例反推。

分区：设定里的七个占地（8/6/7/7/16/4/24 ha）是按文案切出的预算，与故宫真实院落不是同一套
切分（设定把三殿拆成"前朝正殿 8 + 中后殿 6"，而故宫三殿共用一台一广场）。故 ZONES 只作文档
口径，图上不画分区线。

出处：
  设定/长安城市志.md                        卷三 宫城 753×961 m、墙高 10 m、护城河 52 m、
                                            四门、分区占地、中轴里程、入宫路线
  设定/总设定·第十六编·长安与国家象征体系.md  一、宫城布局：殿宇名与用途、开放制度
  设定/法律要目·三·部门法(2026).md            第五条（动线）
"""

PALACE = {
    "name": "宫城（皇宫）",
    "city": "长安",
    "width": 753.0,       # 东西 【设定】
    "depth": 961.0,       # 南北 【设定】
    "wall_h": 10.0,       # 【设定】禁卫墙高 10 m
    "wall_t": 6.0,        # 【推定】
    "moat_w": 52.0,       # 【设定】护城河宽 52 m
    "inner_wall_h": 4.2,  # 【宫式】院内宫墙高约 6 m
    "inner_wall_t": 2.5,
    "area_ha": 72.0,      # 【设定】0.72 km²
}

GATES = [
    {"name": "承天门", "side": "S", "opening": 96,
     "note": "皇城与宫城共用南门，即皇宫大门；仿午门，两侧雁翅楼"},
    {"name": "玄武门", "side": "N", "opening": 84, "note": "宫城正北（仿神武门）"},
    {"name": "东华门", "side": "E", "opening": 66, "note": ""},
    {"name": "西华门", "side": "W", "opening": 66, "note": ""},
]

CORNER_TOWER = {"w": 26, "d": 26, "h": 18, "note": "四隅角楼（明制，【推定】）"}

# ---------------------------------------------------------------- 分区（文档口径）
ZONES = [
    {"key": "court", "name": "前朝正殿", "ha": 4.6, "note": "金瓯殿；政委会与议会常委会决策会议"},
    {"key": "mid", "name": "中、后殿", "ha": 3.6, "note": "秉衡殿、凝命殿；常朝、颁诏、接见、签署"},
    {"key": "east", "name": "东侧紫光阁群", "ha": 8.7, "note": "政治局驻地、中央警卫局营区"},
    {"key": "west", "name": "西侧政枢殿群", "ha": 8.7, "note": "国务院核心部门、中央办公厅院"},
    {"key": "rear", "name": "后寝", "ha": 19.2, "note": "乾宁宫、泰宁宫与东西六宫；数殿改为休息招待室"},
    {"key": "garden", "name": "琼苑（御花园）", "ha": 3.5, "note": "帝后日常"},
    {"key": "service", "name": "门庭、巷道、值房", "ha": 24.0, "note": "前庭、北横街、乾东／乾西五所、内廷库房"},
]

ZONE_NOTE = ("分区占地按院落边界实测（2026-11-22 与《长安城市志》卷三同步）：前朝 4.6 / 中后 3.6 / "
             "东西厢 8.7 × 2 / 后寝 19.2 / 御花园 3.5 / 门庭巷道值房 24.0 ha，合计 72.36 ha（含城墙墙基）。")

# 六宫网格：设定写"六宫"，取东三、西三共六院（一院一宫），不用紫禁城的十二院
COURT_GRID = [(side, num, x, cy, row)
              for side, xs in (("东", (104, 188, 272)), ("西", (-104, -188, -272)))
              for num, x in enumerate(xs, start=1)
              for cy, row in ((150, "南"), (250, "北"))]

# 每院一套：宫门、前殿、后殿、东西配殿（见 STRUCTS / COMPOUNDS 生成段）
COURT_HALF_W, COURT_HALF_D = 38, 45

# ---------------------------------------------------------------- 单体
# kind: hall 殿 / gate 门 / tower 楼阁 / corridor 廊庑 / pavilion 亭 / bridge 桥 / rock 假山 / modern 现代附楼
# roof: hip 庑殿 / gable 悬山 / pyramid 攒尖 / flat 平顶
# base: 台基 (w, d, h)；z: 落位标高（三台上=8）
STRUCTS = [
    # ── 南面：承天门与两雁翅楼（仿午门）
    {"name": "承天门", "kind": "gate", "cx": 0, "cy": -470, "w": 96, "d": 44, "h": 12,
     "roof": "none", "tower": {"w": 62, "d": 26, "h": 13}, "tower_roof": "hip",
     "note": "城台 + 门楼；与皇城共用"},
    {"name": "承天门·东雁翅楼", "kind": "tower", "cx": 62, "cy": -497, "w": 38, "d": 20, "h": 11,
     "roof": "gable", "note": "【宫式】午门两观"},
    {"name": "承天门·西雁翅楼", "kind": "tower", "cx": -62, "cy": -497, "w": 38, "d": 20, "h": 11,
     "roof": "gable", "note": "【宫式】午门两观"},
    {"name": "玄武门", "kind": "gate", "cx": 0, "cy": 470, "w": 84, "d": 40, "h": 12,
     "roof": "none", "tower": {"w": 54, "d": 24, "h": 12}, "tower_roof": "hip", "note": "宫城正北"},
    {"name": "东华门", "kind": "gate", "cx": 376.5, "cy": -90, "w": 66, "d": 30, "h": 11,
     "rot": 90,
     "roof": "none", "tower": {"w": 24, "d": 46, "h": 9}, "tower_roof": "gable",
     "note": "w 沿城墙、d 为城台进深；原来 w=40 / d=66 把 66 m 当门洞、城台往河里挑了 33 m"},
    {"name": "西华门", "kind": "gate", "cx": -376.5, "cy": -90, "w": 66, "d": 30, "h": 11,
     "rot": 90,
     "roof": "none", "tower": {"w": 24, "d": 46, "h": 9}, "tower_roof": "gable",
     "note": "同东华门"},

    # ── 前庭：内金水河五桥、朝房、协和门 / 熙和门
    {"name": "金水桥·中", "kind": "bridge", "cx": 0, "cy": -392, "w": 12, "d": 30, "h": 1.6,
     "roof": "none", "note": "【宫式】内金水河五桥"},
    {"name": "金水桥·东一", "kind": "bridge", "cx": 32, "cy": -394, "w": 9, "d": 28, "h": 1.6,
     "roof": "none", "note": ""},
    {"name": "金水桥·西一", "kind": "bridge", "cx": -32, "cy": -394, "w": 9, "d": 28, "h": 1.6,
     "roof": "none", "note": ""},
    {"name": "金水桥·东二", "kind": "bridge", "cx": 64, "cy": -398, "w": 9, "d": 26, "h": 1.6,
     "roof": "none", "note": ""},
    {"name": "金水桥·西二", "kind": "bridge", "cx": -64, "cy": -398, "w": 9, "d": 26, "h": 1.6,
     "roof": "none", "note": ""},
    {"name": "东朝房", "kind": "corridor", "cx": 176, "cy": -370, "w": 14, "d": 140, "h": 5,
     "roof": "gable", "note": "【宫式】前庭东西朝房"},
    {"name": "西朝房", "kind": "corridor", "cx": -176, "cy": -370, "w": 14, "d": 140, "h": 5,
     "roof": "gable", "note": ""},
    {"name": "协和门", "kind": "gate", "cx": 150, "cy": -330, "w": 26, "d": 18, "h": 8,
     "roof": "gable", "note": "【宫式】前庭东侧门"},
    {"name": "熙和门", "kind": "gate", "cx": -150, "cy": -330, "w": 26, "d": 18, "h": 8,
     "roof": "gable", "note": "【宫式】前庭西侧门"},
    {"name": "宣政门", "kind": "gate", "cx": 0, "cy": -295, "w": 66, "d": 26, "h": 9,
     "base": {"w": 78, "d": 38, "h": 2}, "roof": "none",
     "tower": {"w": 44, "d": 16, "h": 7}, "tower_roof": "hip",
     "note": "【设定·路线】承天门 → 前庭 → 宣政门 → 金瓯殿（仿太和门）"},

    # ── 三台与三殿
    {"name": "金瓯殿", "kind": "hall", "cx": 0, "cy": -160, "w": 90, "d": 50, "h": 15,
     "base": {"w": 110, "d": 72, "h": 2}, "z": 8, "roof": "hip",
     "terrace": {"w": 100, "d": 26, "h": 1.6, "cy": -200},
     "note": "前朝正殿；政委会与议会常委会决策会议；面阔十一间【推定】"},
    {"name": "秉衡殿", "kind": "hall", "cx": 0, "cy": -78, "w": 48, "d": 48, "h": 12,
     "base": {"w": 60, "d": 60, "h": 2}, "z": 8, "roof": "pyramid", "note": "中殿；常朝（仿中和殿）"},
    {"name": "凝命殿", "kind": "hall", "cx": 0, "cy": -22, "w": 75, "d": 45, "h": 12,
     "base": {"w": 90, "d": 60, "h": 2}, "z": 8, "roof": "hip",
     "note": "后殿；颁诏、接见、签署（仿保和殿）"},
    {"name": "东庑", "kind": "corridor", "cx": 127, "cy": -105, "w": 12, "d": 200, "h": 5,
     "z": 8, "roof": "gable", "note": "【宫式】三台东西庑"},
    {"name": "西庑", "kind": "corridor", "cx": -127, "cy": -105, "w": 12, "d": 200, "h": 5,
     "z": 8, "roof": "gable", "note": ""},
    {"name": "体仁阁", "kind": "tower", "cx": 168, "cy": -205, "w": 44, "d": 38, "h": 14,
     "base": {"w": 54, "d": 48, "h": 2}, "roof": "hip", "note": "【宫式】三台东侧楼阁"},
    {"name": "弘义阁", "kind": "tower", "cx": -168, "cy": -205, "w": 44, "d": 38, "h": 14,
     "base": {"w": 54, "d": 48, "h": 2}, "roof": "hip", "note": "【宫式】三台西侧楼阁"},
    {"name": "中左门", "kind": "gate", "cx": 118, "cy": -22, "w": 20, "d": 14, "h": 8,
     "roof": "gable", "note": ""},
    {"name": "中右门", "kind": "gate", "cx": -118, "cy": -22, "w": 20, "d": 14, "h": 8,
     "roof": "gable", "note": ""},

    # ── 内廷中路（后三宫）
    {"name": "内廷门", "kind": "gate", "cx": 0, "cy": 52, "w": 46, "d": 22, "h": 10,
     "base": {"w": 58, "d": 34, "h": 1.5}, "roof": "none",
     "tower": {"w": 30, "d": 12, "h": 6}, "tower_roof": "hip",
     "note": "【宫式】仿乾清门，外朝与内廷分界"},
    {"name": "乾宁宫", "kind": "hall", "cx": 0, "cy": 128, "w": 65, "d": 35, "h": 12,
     "base": {"w": 85, "d": 55, "h": 3}, "roof": "hip",
     "terrace": {"w": 46, "d": 16, "h": 1.5, "cy": 100}, "note": "帝居（仿乾清宫）"},
    {"name": "交泰殿", "kind": "hall", "cx": 0, "cy": 178, "w": 28, "d": 28, "h": 10,
     "base": {"w": 38, "d": 38, "h": 2}, "roof": "pyramid", "note": "【宫式·推定】后三宫之间的方殿"},
    {"name": "泰宁宫", "kind": "hall", "cx": 0, "cy": 222, "w": 55, "d": 35, "h": 11,
     "base": {"w": 75, "d": 55, "h": 3}, "roof": "hip", "note": "后居（仿坤宁宫）"},
    {"name": "后三宫东庑", "kind": "corridor", "cx": 60, "cy": 175, "w": 12, "d": 140, "h": 5,
     "roof": "gable", "note": ""},
    {"name": "后三宫西庑", "kind": "corridor", "cx": -60, "cy": 175, "w": 12, "d": 140, "h": 5,
     "roof": "gable", "note": ""},
    {"name": "后庑", "kind": "corridor", "cx": 0, "cy": 258, "w": 110, "d": 12, "h": 5,
     "roof": "gable", "note": ""},

    # ── 内廷东西六宫：东六宫、西六宫各六院（两行三列），每院门—前殿—后殿—配殿
    *[{"name": f"六宫·{side}{'一二三'[num-1]}{row}·宫门", "kind": "gate",
       "cx": x, "cy": cy - 40, "w": 16, "d": 8, "h": 6, "roof": "gable", "note": ""}
      for side, num, x, cy, row in COURT_GRID],
    *[{"name": f"六宫·{side}{'一二三'[num-1]}{row}·前殿", "kind": "hall",
       "cx": x, "cy": cy - 20, "w": 36, "d": 18, "h": 7,
       "base": {"w": 44, "d": 26, "h": 1}, "roof": "gable", "note": "六宫之一"}
      for side, num, x, cy, row in COURT_GRID],
    *[{"name": f"六宫·{side}{'一二三'[num-1]}{row}·后殿", "kind": "hall",
       "cx": x, "cy": cy + 22, "w": 32, "d": 16, "h": 7,
       "base": {"w": 40, "d": 24, "h": 1}, "roof": "gable", "note": ""}
      for side, num, x, cy, row in COURT_GRID],
    *[{"name": f"六宫·{side}{'一二三'[num-1]}{row}·{'东' if d > 0 else '西'}配殿",
       "kind": "hall", "cx": x + d, "cy": cy, "w": 14, "d": 30, "h": 6,
       "roof": "gable", "note": ""}
      for side, num, x, cy, row in COURT_GRID for d in (25, -25)],
    *[{"name": f"六宫·{side}{'一二三'[num-1]}{row}·后罩房", "kind": "hall",
       "cx": x, "cy": cy + 39, "w": 50, "d": 8, "h": 5, "roof": "gable", "note": "后院库房"}
      for side, num, x, cy, row in COURT_GRID],

    # ── 外朝东西两厢：紫光阁 / 政枢殿
    {"name": "紫光阁", "kind": "hall", "cx": 250, "cy": -265, "w": 70, "d": 45, "h": 13,
     "base": {"w": 85, "d": 58, "h": 3}, "roof": "hip",
     "note": "中央政治局驻地与常委会开会处"},
    {"name": "紫光阁·南配殿", "kind": "hall", "cx": 250, "cy": -320, "w": 40, "d": 18, "h": 7,
     "roof": "gable", "note": ""},
    {"name": "紫光阁·东配殿", "kind": "hall", "cx": 300, "cy": -250, "w": 22, "d": 40, "h": 7,
     "roof": "gable", "note": ""},
    {"name": "紫光阁·西配殿", "kind": "hall", "cx": 200, "cy": -250, "w": 22, "d": 40, "h": 7,
     "roof": "gable", "note": ""},
    {"name": "政枢殿", "kind": "hall", "cx": -250, "cy": -265, "w": 70, "d": 45, "h": 13,
     "base": {"w": 85, "d": 58, "h": 3}, "roof": "hip", "note": "国务院核心部门、中央办公厅"},
    {"name": "政枢殿·南配殿", "kind": "hall", "cx": -250, "cy": -320, "w": 40, "d": 18, "h": 7,
     "roof": "gable", "note": ""},
    {"name": "政枢殿·东配殿", "kind": "hall", "cx": -300, "cy": -250, "w": 22, "d": 40, "h": 7,
     "roof": "gable", "note": ""},
    {"name": "政枢殿·西配殿", "kind": "hall", "cx": -200, "cy": -250, "w": 22, "d": 40, "h": 7,
     "roof": "gable", "note": ""},
    {"name": "紫光阁·北配殿", "kind": "hall", "cx": 250, "cy": -210, "w": 40, "d": 18, "h": 7,
     "roof": "gable", "note": "常委会会议室"},
    {"name": "政枢殿·北配殿", "kind": "hall", "cx": -250, "cy": -210, "w": 40, "d": 18, "h": 7,
     "roof": "gable", "note": "国务院常务会议室"},

    # ── 外朝东侧：中央警卫局营区（紫光阁旁驻精锐分队）
    {"name": "营区门", "kind": "gate", "cx": 271, "cy": -356, "w": 24, "d": 12, "h": 7,
     "roof": "gable", "note": "【宫式】营区门"},
    *[{"name": f"警卫营房·{i+1}", "kind": "hall", "cx": x, "cy": y, "w": 44, "d": 14, "h": 5,
       "roof": "gable", "note": "中央警卫局精锐分队营房"}
      for i, (x, y) in enumerate([(216, -430), (260, -430), (304, -430),
                                  (216, -392), (260, -392), (304, -392)])],
    {"name": "营区·器械库", "kind": "hall", "cx": 330, "cy": -392, "w": 20, "d": 40, "h": 5,
     "roof": "gable", "note": "库房"},

    # ── 外朝西侧：中央办公厅院（政枢殿之北）
    {"name": "办公厅门", "kind": "gate", "cx": -271, "cy": -356, "w": 24, "d": 12, "h": 7,
     "roof": "gable", "note": "【宫式】院门"},
    {"name": "中央办公厅", "kind": "hall", "cx": -266, "cy": -420, "w": 96, "d": 24, "h": 9,
     "base": {"w": 108, "d": 34, "h": 1.5}, "roof": "hip", "note": "中央办公厅文书与值班"},
    {"name": "办公厅·东厢", "kind": "hall", "cx": -318, "cy": -390, "w": 40, "d": 14, "h": 5,
     "roof": "gable", "note": ""},
    {"name": "办公厅·西厢", "kind": "hall", "cx": -214, "cy": -390, "w": 40, "d": 14, "h": 5,
     "roof": "gable", "note": ""},
    # 架空混合：紫光阁办公化的现代附楼
    {"name": "紫光阁·现代附楼", "kind": "modern", "cx": 330, "cy": -150, "w": 34, "d": 54, "h": 9,
     "roof": "flat", "note": "【架空混合·推定】紫光阁办公化的现代附楼"},

    # ── 琼苑东西两侧：乾东五所 / 乾西五所（皇子居所，各五院）
    *[{"name": f"{side}五所·{'一二三四五'[i]}", "kind": "hall", "cx": x, "cy": y,
       "w": 26, "d": 16, "h": 7, "base": {"w": 32, "d": 22, "h": 1},
       "roof": "gable", "note": "皇子居所（【宫式】乾东五所／乾西五所）"}
      for side, sx in (("东", 1), ("西", -1))
      for i, (x, y) in enumerate([(sx * 228, 332), (sx * 278, 332), (sx * 328, 332),
                                  (sx * 253, 380), (sx * 303, 380)])],

    # ── 琼苑（御花园）
    {"name": "钦安殿", "kind": "hall", "cx": 0, "cy": 352, "w": 30, "d": 24, "h": 9,
     "base": {"w": 40, "d": 34, "h": 2}, "roof": "hip", "note": "【宫式】御花园正殿"},
    {"name": "琼苑·亭一", "kind": "pavilion", "cx": 96, "cy": 322, "w": 12, "d": 12, "h": 5,
     "roof": "pyramid", "note": ""},
    {"name": "琼苑·亭二", "kind": "pavilion", "cx": -96, "cy": 322, "w": 12, "d": 12, "h": 5,
     "roof": "pyramid", "note": ""},
    {"name": "琼苑·亭三", "kind": "pavilion", "cx": 96, "cy": 382, "w": 12, "d": 12, "h": 5,
     "roof": "pyramid", "note": ""},
    {"name": "琼苑·亭四", "kind": "pavilion", "cx": -96, "cy": 382, "w": 12, "d": 12, "h": 5,
     "roof": "pyramid", "note": ""},
    {"name": "琼苑·假山", "kind": "rock", "cx": 0, "cy": 314, "w": 46, "d": 18, "h": 6,
     "roof": "none", "note": "【宫式】堆秀山"},
    {"name": "顺贞门", "kind": "gate", "cx": 0, "cy": 405, "w": 30, "d": 14, "h": 8,
     "roof": "gable", "note": "【宫式】御花园北门"},
]

# 三台（三殿共用的工字形高台，整块挤出，避免叠盒子接缝）
PLATFORM_POLY = [(-118, -215), (118, -215), (118, -109), (78, -109), (78, -50),
                 (103, -50), (103, 11), (-103, 11), (-103, -50), (-78, -50),
                 (-78, -109), (-118, -109)]
PLATFORM_H = 8.0
PLATFORMS = [
    {"name": "三台·前陛", "cx": 0, "cy": -219, "w": 44, "d": 12, "h": 4, "note": "台阶"},
]

# ---------------------------------------------------------------- 院墙
COMPOUNDS = [
    # 东西六宫：东六宫、西六宫各六院（两行三列），每院 66×90 m
    *[{"name": f"六宫·{side}{'一二三'[num-1]}{row}",
       "x0": x - COURT_HALF_W, "x1": x + COURT_HALF_W,
       "y0": cy - COURT_HALF_D, "y1": cy + COURT_HALF_D, "gates": [("S", x, 14)]}
      for side, num, x, cy, row in COURT_GRID],
    # 外朝东西两厢
    {"name": "紫光阁院", "x0": 160, "x1": 352, "y0": -345, "y1": -195, "gates": [("S", 250, 22)]},
    {"name": "政枢殿院", "x0": -352, "x1": -160, "y0": -345, "y1": -195, "gates": [("S", -250, 22)]},
    {"name": "中央警卫局营区", "x0": 190, "x1": 352, "y0": -452, "y1": -356,
     "gates": [("N", 271, 20)]},
    {"name": "中央办公厅院", "x0": -352, "x1": -190, "y0": -452, "y1": -356,
     "gates": [("N", -271, 20)]},
    # 御花园东西两侧的皇子居所院
    {"name": "东五所", "x0": 200, "x1": 352, "y0": 305, "y1": 405, "gates": [("S", 276, 18)]},
    {"name": "西五所", "x0": -352, "x1": -200, "y0": 305, "y1": 405, "gates": [("S", -276, 18)]},
    # 御花园
    {"name": "琼苑", "x0": -160, "x1": 160, "y0": 300, "y1": 410,
     "gates": [("S", 0, 26), ("S", 116, 14), ("S", -116, 14), ("N", 0, 26)]},
]

# 内廷分界墙（外朝 / 内廷），留三门
INNER_LINE = {"y": 45, "x0": -376.5, "x1": 376.5, "t": 3.0, "h": 6.0,
              "gaps": [(0, 46), (150, 24), (-150, 24)]}

# 内金水河
RIVER = {
    "width": 16.0,
    "points": [(-340, -418), (-262, -410), (-180, -398), (-96, -387), (0, -383),
               (96, -387), (180, -398), (262, -410), (340, -418)],
    "note": "【宫式】内金水河，横穿前庭，五桥跨之",
}

# 动线
ROUTE = [  # 【设定】法律要目·三 第五条（动线）
    (1, "承天门", 0, -470),
    (2, "金瓯殿月台", 0, -200),
    (3, "秉衡殿前檐", 0, -105),
    (4, "凝命殿前檐", 0, -45),
    (5, "琼苑南半部", 0, 350),
    (6, "玄武门", 0, 470),
]

AXIS_LABEL = "中轴 961 m"


# ---------------------------------------------------------------- 生成器
def _seg_h(x0, x1, y, t, gaps):
    cuts = sorted((c - w / 2, c + w / 2) for c, w in gaps)
    out, cur = [], x0
    for a, b in cuts:
        if b <= x0 or a >= x1:
            continue
        if a > cur:
            out.append((cur, min(a, x1), y - t / 2, y + t / 2))
        cur = max(cur, b)
    if cur < x1:
        out.append((cur, x1, y - t / 2, y + t / 2))
    return out


def _seg_v(y0, y1, x, t, gaps):
    cuts = sorted((c - w / 2, c + w / 2) for c, w in gaps)
    out, cur = [], y0
    for a, b in cuts:
        if b <= y0 or a >= y1:
            continue
        if a > cur:
            out.append((x - t / 2, x + t / 2, cur, min(a, y1)))
        cur = max(cur, b)
    if cur < y1:
        out.append((x - t / 2, x + t / 2, cur, y1))
    return out


def compound_walls(c, t=None):
    t = t or PALACE["inner_wall_t"]
    by_side = {"S": [], "N": [], "E": [], "W": []}
    for side, center, width in (c.get("gates") or []):
        by_side[side].append((center, width))
    out = []
    for x0, x1, y0, y1 in _seg_h(c["x0"], c["x1"], c["y0"], t, by_side["S"]):
        out.append({"x0": x0, "x1": x1, "y0": y0, "y1": y1, "name": c["name"] + "_S"})
    for x0, x1, y0, y1 in _seg_h(c["x0"], c["x1"], c["y1"], t, by_side["N"]):
        out.append({"x0": x0, "x1": x1, "y0": y0, "y1": y1, "name": c["name"] + "_N"})
    for x0, x1, y0, y1 in _seg_v(c["y0"], c["y1"], c["x0"], t, by_side["W"]):
        out.append({"x0": x0, "x1": x1, "y0": y0, "y1": y1, "name": c["name"] + "_W"})
    for x0, x1, y0, y1 in _seg_v(c["y0"], c["y1"], c["x1"], t, by_side["E"]):
        out.append({"x0": x0, "x1": x1, "y0": y0, "y1": y1, "name": c["name"] + "_E"})
    return out


def inner_line_walls():
    L = INNER_LINE
    return [{"x0": a, "x1": b, "y0": L["y"] - L["t"] / 2, "y1": L["y"] + L["t"] / 2,
             "name": "内廷墙"} for a, b, _, _ in _seg_h(L["x0"], L["x1"], L["y"], L["t"], L["gaps"])]


def _overlap(a, b, pad=1.0):
    return not (a["x1"] + pad < b["x0"] or b["x1"] + pad < a["x0"]
                or a["y1"] + pad < b["y0"] or b["y1"] + pad < a["y0"])


def _blockers():
    out = [{"x0": c["x0"], "x1": c["x1"], "y0": c["y0"], "y1": c["y1"]} for c in COMPOUNDS]
    for s in STRUCTS:
        out.append({"x0": s["cx"] - s["w"] / 2, "x1": s["cx"] + s["w"] / 2,
                    "y0": s["cy"] - s["d"] / 2, "y1": s["cy"] + s["d"] / 2})
        if s.get("base"):
            b = s["base"]
            out.append({"x0": s["cx"] - b["w"] / 2, "x1": s["cx"] + b["w"] / 2,
                        "y0": s["cy"] - b["d"] / 2, "y1": s["cy"] + b["d"] / 2})
    for p in PLATFORMS:
        out.append({"x0": p["cx"] - p["w"] / 2, "x1": p["cx"] + p["w"] / 2,
                    "y0": p["cy"] - p["d"] / 2, "y1": p["cy"] + p["d"] / 2})
    out.append({"x0": -344, "x1": 344, "y0": -432, "y1": -366})   # 前庭与河
    return out


def service_blocks():
    """值房：沿墙成排 + 外朝两厢内排（【宫式】），自动避让院落与殿身。"""
    bl = _blockers()
    out = []
    hw = PALACE["width"] / 2 - PALACE["wall_t"] / 2 - 12
    hd = PALACE["depth"] / 2 - PALACE["wall_t"] / 2 - 12

    def free(cx, cy, w, d):
        r = {"x0": cx - w / 2, "x1": cx + w / 2, "y0": cy - d / 2, "y1": cy + d / 2}
        return not any(_overlap(r, b) for b in bl)

    for x in (-hw, hw):
        y = -430.0
        while y <= 430.0:
            if free(x, y, 12, 40):
                out.append((x, y, 12.0, 40.0, 5.0))
            y += 46.0
    for y in (-hd, hd):
        x = -334.0
        while x <= 334.0:
            if abs(x) > 70 and free(x, y, 40, 12):
                out.append((x, y, 40.0, 12.0, 5.0))
            x += 46.0
    # 外朝两厢内部的朝房排（内阁、銮仪卫一类）
    for x in (196, 246, 306, 336, -196, -246, -306, -336):
        for y in (-170, -125, -80, -35, 10):
            if free(x, y, 44, 16):
                out.append((x, y, 44.0, 16.0, 5.0))
    # 内廷东西夹道：库房 / 值房纵向成排
    for x in (333, -333):
        y = 60.0
        while y <= 296.0:
            if free(x, y, 14, 40):
                out.append((x, y, 14.0, 40.0, 5.0))
            y += 46.0
    # 内廷南侧班房（内廷门两翼）
    for y in (60, 88):
        x = -180.0
        while x <= 180.0:
            if abs(x) > 80 and free(x, y, 40, 12):
                out.append((x, y, 40.0, 12.0, 5.0))
            x += 46.0
    # 御花园东西夹道
    for x in (180, -180):
        y = 312.0
        while y <= 400.0:
            if free(x, y, 14, 40):
                out.append((x, y, 14.0, 40.0, 5.0))
            y += 46.0
    # 北横街两排值房
    for y in (428, 460):
        x = -330.0
        while x <= 330.0:
            if abs(x) > 70 and free(x, y, 40, 12):
                out.append((x, y, 40.0, 12.0, 5.0))
            x += 46.0
    return out


def roof_mat_for(kind, w=0, d=0):
    """屋顶材质：值房、院墙用青瓦；廊庑用稍暗的琉璃；殿宇用琉璃黄。"""
    if kind in ("service", "wall"):
        return "tile"
    if kind == "corridor":
        return "roof2"
    return "roof"


def trees():
    pts = []
    for gx in range(-140, 141, 22):
        for gy in range(306, 404, 20):
            if abs(gx) < 30 and 336 < gy < 372:      # 让开钦安殿
                continue
            if abs(gx) < 34 and 300 < gy < 328:      # 让开假山
                continue
            pts.append((gx + (gx * 7 % 11) - 5, gy + (gy * 5 % 9) - 4))
    return pts


def stats():
    hall = sum(s["w"] * s["d"] for s in STRUCTS
               if s["kind"] in ("hall", "gate", "tower", "pavilion"))
    corridor = sum(s["w"] * s["d"] for s in STRUCTS if s["kind"] == "corridor")
    service = sum(w * d for _cx, _cy, w, d, _h in service_blocks())
    water = RIVER["width"] * 700
    garden = (410 - 300) * 320
    total = PALACE["width"] * PALACE["depth"] / 1e4
    return {
        "total_ha": round(total, 2),
        "hall_ha": round(hall / 1e4, 2),
        "corridor_ha": round(corridor / 1e4, 2),
        "service_ha": round(service / 1e4, 2),
        "water_ha": round(water / 1e4, 2),
        "garden_ha": round(garden / 1e4, 2),
        "density_pct": round((hall + corridor + service) / (total * 1e4) * 100, 1),
        "courtyards": len(COMPOUNDS),
        "structs": len(STRUCTS),
        "walls": len(inner_line_walls()) + sum(len(compound_walls(c)) for c in COMPOUNDS),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(stats(), ensure_ascii=False, indent=2))
    print("值房块数：", len(service_blocks()), " 树：", len(trees()))
