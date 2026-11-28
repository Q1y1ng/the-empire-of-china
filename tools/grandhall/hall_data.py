"""国家大会堂·中厅·万人大礼堂 —— 2D 平剖图与 3D 白模/精模共用的唯一数据源。

坐标系与 `tools/plaza/`、`tools/palace/` 完全一致：
原点取**宫城平面中心**，+x 向东、+y 向北，单位米。本礼堂是中厅的内胆，
因此可以直接套进广场 .glb 的中厅体块（x ∈ [-540, -310]、y ∈ [-1155.5, -915.5]、高 50）；
中厅体块挖空后壁厚 2 m，故内胆四周各退 2.5 m（见 SHELL / DOORBAY）。

## 口径（三层来源）

【设定】《长安城市志》卷二·国家大会堂、《总设定·第十六编》二：
    中厅 = **无立柱万人大礼堂，约 10,000 席**；用于全国政治代表会议全体会议、
    宪法日特别会议、换届周第 1/2—3/4/7 日。3,000 代表 ＋ 列席 2,000—3,000。
【作者·2026-11-23】观众厅＋中央前厅；尺度按本项目放大口径：
    台口 40 m 宽、厅 120 × 95 m、净高 40 m；
    池座 4,000 ＋ 二层挑台 3,500 ＋ 三层挑台 2,500 ＝ 10,000 席。
【参照】人民大会堂万人大礼堂（1959）的真实做法，按本项目放大后取用：
    宽 76 / 深 60 / 中部高 33 m；池座 3,693 ＋ 二层 3,515 ＋ 三层 2,518 ＝ 9,726 席；
    台口 32 m 宽 × 18 m 高；主席台可设 300—500 席；最远观众距主席台 60 m；
    扇面平面、无立柱、穹隆顶"水天一色"：顶棚中央红五星灯 ＋ 镏金 70 道光芒线
    ＋ 40 个葵花瓣灯 ＋ 500 盏满天星灯 ＋ 三环水波式暗灯槽；顶棚与墙圆曲相接；
    中央大厅 20 根明柱、桃红大理石地面、井字梁顶棚悬 5 组水晶吊灯。
【本项目改写】红五星→**国徽圆盘（长安城墙＋金蟠龙＋稻穗齿轮）**，
    光芒线取 **72 道**（周天 360°／5°一道），旗用**红底金龙旗**，
    全部依《国家象征物（2026）》：帝国红 #C8102E、金 #C9A227。
"""

from __future__ import annotations

import math

# ---------------------------------------------------------------- 坐标与体块
# 中厅体块（取自 plaza_data.MASSES 的 hall-c）
BUILD = {"x0": -540.0, "x1": -310.0, "y0": -1155.5, "y1": -915.5, "h": 50.0}
AXIS_Y = -1035.5            # 中轴线 y（与 hall-portico-c 同心）
AXIS_X = (BUILD["x0"] + BUILD["x1"]) / 2.0

# 纵剖面四段（自西向东）：后台 — 主席台 — 观众厅 — 中央前厅
ZONES = {
    "backstage": {"x0": -537.5, "x1": -512.0, "name": "后台"},
    "stage": {"x0": -512.0, "x1": -484.0, "name": "主席台"},
    "hall": {"x0": -484.0, "x1": -431.0, "name": "观众厅"},
    "foyer": {"x0": -431.0, "x1": -311.5, "name": "中央前厅"},
}

STAGE = {"x0": -512.0, "x1": -484.0, "half_w": 22.0, "z": 1.5, "h": 22.0}
PROSCENIUM = {"x": -484.0, "w": 40.0, "h": 22.0}      # 台口
HALL = {
    # 【作者·2026-11-28 裁决】①「选 B」收进深、座宽×排距回到实物量级 0.55×0.88；
    #   ②「以人民大会堂为蓝本，座位最后面就是墙/门，不留空地」；
    #   ③「是墙来找座椅不是座椅去找墙」——**进深是推导量，不是输入量**。
    #   口径：三层座席同止于末排 r=82，后墙 = 末排 + WALL(1.0 m 出门/门斗余量)，
    #   进深 = (FOCUS.x + 82 + 1.0) − x_front = 53 m；剩余长度全给中央前厅（119.5 m），
    #   内胆总长 226 m 不变，故广场外壳、中厅体块、门斗、下沉 2.3 全部不动。
    #   结果：10,127 席（池座 5,122／二层 2,810／三层 2,195）、密度 2.39、视距 45.9 m、后区空场 0。
    "x_front": -484.0, "x_rear": -431.0,
    "w_front": 40.0, "w_rear": 120.0,
    "depth": 53.0,
    "z_floor": 0.0,        # 台口前第一排地坪
    "z_apex": 50.0,        # 穹顶最高点（净高 44）
    "z_spring": 32.0,      # 穹顶与侧墙／后墙交接高度
    "z_stage_ceiling": 25.0,   # 台口上方天花（台口 22 m，留 3 m 过梁）
}
FOCUS = {"x": -514.0, "y": AXIS_Y}   # 扇心：台口后 30 m（几何作图点）

FOYER = {"x0": -389.0, "x1": -311.5, "y0": -1153.0, "y1": -918.0,
         "h": 24.0, "beam_z": 22.0, "n_col": 20, "col_r": 0.9}

# 【作者·2026-11-25】套合裁决：
#   ① 中厅体块保持 50 m 不抬高，**万人大礼堂下沉**——内胆地坪留在 z=0（比 2.3 m 台基面低 2.3 m），
#      穹顶顶 50.0 正好落在琉璃顶底 50.15 之下；
#   ② 中厅体块挖空，壁厚 2 m（外皮 −540/−310、±120；内皮 −538/−312、±118），
#      内胆四周各退 2.5 m 让出 0.5 m 空腔；
#   ③ 前厅东墙改**玻璃门斗**：整面玻璃幕墙 ＋ 轴线上 24 × 2.5 m 玻璃门斗。
SHELL = {"t": 2.0, "gap": 0.5}          # 广场中厅壁厚 / 内胆与内皮之间的空腔
DOORBAY = {"half_w": 12.0, "depth": 2.2, "h": 8.0, "x": -311.5}   # 玻璃门斗（自前厅东墙向东出挑）

# ---------------------------------------------------------------- 座席
# 座席模数：座宽 0.58、排距 0.95（人民大会堂实物为 0.55×0.85 的量级），
# 纵向走道宽 1.6 m。【作者·2026-11-28 一以人民大会堂为蓝本】间距由弧长 18 m 收到 12 m：
#   座席 10,882 → 10,366，密度 2.57 → 2.44，通道更接近实物手感（实物 2.13）。
SEAT = {"pitch": 0.55, "row": 0.88, "aisle": 1.6, "aisle_every": 12.0}

# 三层座席。池座为纯扇面（wrap=0）；两层挑台为**U 形**——前缘在轴线上最深、
# 沿两侧向台口方向包转（wrap = 侧翼前伸的半径量，theta_ref = 该前伸量对应的张角）。
TIERS = [
    # 2026-11-28 座席系统整改：加横向过道（mid/rear）、挑台向后铺开、削缓起坡，
    # 让三层净空从 1.99 m 提到 2.3 m 以上，同时把座席总数补回约 1 万。
    # 【作者·2026-11-28】三层同止于末排 r=82（座背直接靠后墙，不留空地）。
    #   实算 5,122 / 2,810 / 2,195 = 10,127 席，密度 2.39（人民大会堂 2.13）。
    {"key": "pit", "name": "池座", "r0": 38.5, "r1": 82.0,
     "z0": 0.0, "slope": 0.075, "wrap": 0.0, "theta_ref": 0.5, "target": 5122,
     "aisles": {"mid": 1.8, "rear": 2.4}},
    {"key": "bal1", "name": "二层挑台", "r0": 60.0, "r1": 82.0,
     "z0": 10.0, "slope": 0.26, "wrap": 0.0, "theta_ref": 0.5, "target": 2810,
     "aisles": {"mid": 1.8, "rear": 2.4}},
    {"key": "bal2", "name": "三层挑台", "r0": 64.0, "r1": 82.0,
     "z0": 20.9, "slope": 0.28, "wrap": 0.0, "theta_ref": 0.5, "target": 2195,
     "aisles": {"mid": 1.8, "rear": 2.8}},
]
# 【作者·2026-11-28】座席系统五条缺陷：①座椅不贴地 ②座椅朝向看不出 ③池座后区空场
#   ④二三层净空不足 ⑤只有纵向过道、没有横向过道（被座椅卡死）
#   本轮处理 ①②④⑤；③是厅的平面尺寸相对 1 万座偏大的规格问题，待作者裁决。

STAGE_SEATS = 400        # 主席台（不计入万人席）

# 【作者·2026-11-23】三项裁决
# 【作者·2026-11-24】第四项裁决：国徽浮雕「难做就不要了」→ show=False，主席台只留木饰后墙
EMBLEM = {"d": 6.4, "show": False}   # ① 国徽直径 6.4 m（"可以"）；浮雕不做了
FLAGS_AT_PROSCENIUM = False     # ② 台口两侧不设红底金龙旗（"不必"）
REP_DESKS = True                # ③ 池座（及各层）设代表席小桌（"设"）

# ---------------------------------------------------------------- 色彩
# 依《国家象征物（2026）》：帝国红 C0 M100 Y100 K10 ≈ #C8102E，金 ≈ #C9A227
SRGB = {
    "imperial_red": (0xC8, 0x10, 0x2E),
    "gold": (0xC9, 0xA2, 0x27),
    "white_marble": (0xE8, 0xE4, 0xD8),
    "rose_marble": (0xB8, 0x82, 0x74),
    "plaster": (0xE4, 0xDD, 0xCB),
    "wood": (0x4A, 0x2E, 0x1C),
    "bronze": (0x6B, 0x50, 0x24),
}


def srgb_lin(rgb):
    """sRGB 0—255 → Blender 线性 0—1。"""
    out = []
    for c in rgb:
        v = c / 255.0
        out.append(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4)
    return tuple(out)


# ---------------------------------------------------------------- 几何辅助
def hall_plan():
    """观众厅平面四角（自西北起顺时针）。"""
    f, r = HALL["x_front"], HALL["x_rear"]
    hf, hr = HALL["w_front"] / 2.0, HALL["w_rear"] / 2.0
    return [(f, AXIS_Y - hf), (f, AXIS_Y + hf), (r, AXIS_Y + hr), (r, AXIS_Y - hr)]


def hall_centroid():
    """观众厅平面形心（梯形：距前缘 depth·(a+2b)/3(a+b)）。"""
    a, b = HALL["w_front"], HALL["w_rear"]
    t = HALL["depth"] * (a + 2 * b) / (3.0 * (a + b))
    return (HALL["x_front"] + t, AXIS_Y)


def wall_half_angle(r):
    """半径 r（自扇心 FOCUS）的同心弧在观众厅内允许的半张角（弧度）。

    侧墙自台口角 (±20 m) 向后的 120 m 展开；弧超出后墙后改由后墙截断。
    """
    ax = HALL["depth"]                       # 侧墙方向（x 向东）
    ay = (HALL["w_rear"] - HALL["w_front"]) / 2.0
    hf = HALL["w_front"] / 2.0
    bx = 2.0 * (30.0 * ax + hf * ay)
    cc = 30.0 ** 2 + hf ** 2 - r * r
    a = ax * ax + ay * ay
    disc = bx * bx - 4 * a * cc
    if disc >= 0:
        s = (-bx + math.sqrt(disc)) / (2 * a)
        if 0.0 <= s <= 1.0:
            return math.atan2(hf + ay * s, 30.0 + ax * s)
    dx = HALL["x_rear"] - FOCUS["x"]        # 125
    if r <= dx:
        return 0.0
    dy = min(math.sqrt(r * r - dx * dx), HALL["w_rear"] / 2.0)
    return math.atan2(dy, dx)


def row_intervals(r, tier):
    """半径 r 一排的可用角度区间（挑台为 U 形：轴线处最深，两侧向前包转）。"""
    th = wall_half_angle(r)
    if th < 0.02:
        return []
    wrap = tier.get("wrap", 0.0)
    if wrap > 0.0 and r < tier["r0"]:
        tb = tier.get("theta_ref", 0.5) * math.sqrt(min(1.0, (tier["r0"] - r) / wrap))
        if tb >= th:
            return []
        return [(-th, -tb), (tb, th)]
    return [(-th, th)]


def row_blocks(r, tier):
    """一行座席切块：区间内按弧长约 18 m 切纵向走道；返回 [(θ0, θ1, 座位数)]。"""
    pitch = SEAT["pitch"]
    out = []
    for a0, a1 in row_intervals(r, tier):
        arc = (a1 - a0) * r
        if arc < 4.0:
            continue
        n_aisle = max(0, int(round(arc / SEAT["aisle_every"])) - 1)
        usable = arc - n_aisle * SEAT["aisle"]
        n_seat = int(usable / pitch)
        if n_seat <= 0:
            continue
        # 均分成 n_aisle+1 块，块间留走道（角度宽度走道宽/r）
        dw = (a1 - a0)
        seg = (dw - n_aisle * SEAT["aisle"] / r) / (n_aisle + 1)
        if seg <= 0:
            continue
        per = n_seat // (n_aisle + 1)
        rem = n_seat - per * (n_aisle + 1)
        for i in range(n_aisle + 1):
            b0 = a0 + i * (seg + SEAT["aisle"] / r)
            cnt = per + (1 if i < rem else 0)
            out.append((round(b0, 5), round(b0 + seg, 5), cnt))
    return out


def tier_rows(tier):
    """一层座席的逐排数据：[{r, z, blocks, seats}]。

    横向过道（`aisles`）：中线一道 `mid` 宽、末排让出 `rear` 宽——只**跳过行**，
    楼板由 `fan_surface` 按 (r, θ) 密铺到厅墙，不会因此破洞。
    """
    rr = []
    ais = tier.get("aisles") or {}
    mid_w = float(ais.get("mid", 0.0) or 0.0)
    rear_w = float(ais.get("rear", 0.0) or 0.0)
    r_mid = 0.5 * (tier["r0"] + tier["r1"])
    # 【作者·2026-11-28】「座位最后面就是墙/门，不留空地」→ 最后 2 排必须在墙前，
    # 横向过道挪到它们之前。原来过道贴着 r1，等于把最后几排吃掉、留 4 m 空场。
    back_rows = 2
    r_rear_aisle_end = tier["r1"] - back_rows * SEAT["row"]
    r = tier["r0"]
    while r <= tier["r1"] + 1e-9:
        in_mid = mid_w > 0.0 and abs(r - r_mid) <= mid_w * 0.5
        in_rear = (rear_w > 0.0
                   and r_rear_aisle_end - rear_w < r <= r_rear_aisle_end)
        if not (in_mid or in_rear):
            blocks = row_blocks(r, tier)
            rr.append({
                "r": round(r, 3),
                "z": round(tier_row_z(tier, r), 3),
                "blocks": blocks,
                "seats": sum(b[2] for b in blocks),
            })
        r += SEAT["row"]
    # U 形挑台的侧翼自 r0 向前包转：把 r0 之前的行补出来
    if tier.get("wrap", 0.0) > 0.0:
        head = []
        r = tier["r0"] - SEAT["row"]
        while r > 0:
            blocks = row_blocks(r, tier)
            if not blocks:
                break
            head.append({
                "r": round(r, 3),
                "z": round(tier["z0"], 3),
                "blocks": blocks,
                "seats": sum(b[2] for b in blocks),
            })
            r -= SEAT["row"]
        rr = list(reversed(head)) + rr
    return rr


def seat_stats():
    """三层座席逐层实数。"""
    out = {}
    for t in TIERS:
        rows = tier_rows(t)
        out[t["key"]] = {
            "name": t["name"], "rows": len(rows),
            "seats": sum(x["seats"] for x in rows),
            "target": t["target"],
            "r": (t["r0"], t["r1"]),
            "z": (t["z0"], rows[-1]["z"] if rows else t["z0"]),
        }
    return out


def total_seats():
    return sum(v["seats"] for v in seat_stats().values())


# ---------------------------------------------------------------- 穹顶
def dome_edge_z(bx):
    """穹顶边缘按边界点位置取高：台口一侧 22.5，向侧／后墙抬到 26。"""
    t = min(1.0, max(0.0, (bx - HALL["x_front"]) / 24.0))
    return HALL["z_stage_ceiling"] + (HALL["z_spring"] - HALL["z_stage_ceiling"]) * (
        t * t * (3 - 2 * t))


def dome_z(rho, z_edge):
    """ρ（0 中心 → 1 边界）处的顶棚高度；边缘竖直收头，读出"与墙圆曲相接"。"""
    g = max(0.0, 1.0 - rho * rho) ** 0.7
    return z_edge + (HALL["z_apex"] - z_edge) * g


def dome_height(x, y):
    """平面点 (x, y) 处的穹顶内表面高度。"""
    c = hall_centroid()
    dx, dy = x - c[0], y - c[1]
    ang = math.atan2(dy, dx)
    rb = _ray_to_polygon(c, ang, hall_plan())
    if not rb:
        return HALL["z_spring"]
    rho = min(1.0, math.hypot(dx, dy) / rb)
    bx = c[0] + math.cos(ang) * rb
    return dome_z(rho, dome_edge_z(bx))


def tier_z_at(tier, x, y):
    """点 (x, y) 落在该层座席范围内则返回地坪高，否则 None。"""
    dx, dy = x - FOCUS["x"], y - FOCUS["y"]
    r = math.hypot(dx, dy)
    th = math.atan2(dy, dx)
    if not any(iv[0] <= th <= iv[1] for iv in row_intervals(r, tier)):
        return None
    return tier_z(tier, x, y, clamp=True)


# ---------------------------------------------------------------- 派生几何（无 bpy 副作用）
def tier_row_z(tier, r):
    """半径 r 处的座席排高（未 clamp）。逐排数据、楼板面、体检脚本共用这一条式子。"""
    return tier["z0"] + max(0.0, r - tier["r0"]) * tier["slope"]


def tier_z(tier, x, y, clamp=True):
    """点 (x, y) 处的该层楼板标高。

    clamp=True：不超过末排标高——末排之外是后区平台（这块要不要留、留多宽是待裁项）。
    """
    r = math.hypot(x - FOCUS["x"], y - FOCUS["y"])
    z = tier_row_z(tier, r)
    if clamp:
        rows = tier_rows(tier)
        if rows:
            z = min(z, rows[-1]["z"])
    return z


def hall_half_width(x):
    """观众厅在 x 处的半宽（前 40 m、后 160 m 线性展开）。"""
    t = (x - HALL["x_front"]) / HALL["depth"]
    return HALL["w_front"] / 2.0 + t * (HALL["w_rear"] - HALL["w_front"]) / 2.0


def in_hall(x, y, grow=0.0):
    """点是否在观众厅平面内；grow 为外扩量（补齐网格边缘锯齿缝）。"""
    if not (HALL["x_front"] - grow <= x <= HALL["x_rear"] + grow):
        return False
    return abs(y - AXIS_Y) <= hall_half_width(x) + grow


def hall_radius(th):
    """自扇心沿 th 方向到观众厅边界的距离（梯形四边求交）。"""
    dx, dy = math.cos(th), math.sin(th)
    poly = hall_plan()
    ts = []
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        ex, ey = x2 - x1, y2 - y1
        den = dx * ey - dy * ex
        if abs(den) < 1e-12:
            continue
        t = ((x1 - FOCUS["x"]) * ey - (y1 - FOCUS["y"]) * ex) / den
        u = ((x1 - FOCUS["x"]) * dy - (y1 - FOCUS["y"]) * dx) / den
        if t > 0 and -1e-9 <= u <= 1 + 1e-9:
            ts.append(t)
    # 扇心在观众厅之外（台口以西 30 m），一条射线先进后出，取**出射**那一点
    return max(ts) if ts else 0.0


def _ray_to_polygon(c, ang, poly):
    """自形心沿 ang 的射线与多边形边界交点距离。"""
    dx, dy = math.cos(ang), math.sin(ang)
    best = None
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        ex, ey = x2 - x1, y2 - y1
        den = dx * ey - dy * ex
        if abs(den) < 1e-12:
            continue
        t = ((x1 - c[0]) * ey - (y1 - c[1]) * ex) / den
        u = ((x1 - c[0]) * dy - (y1 - c[1]) * dx) / den
        if t > 0 and 0.0 <= u <= 1.0:
            if best is None or t < best:
                best = t
    return best


# ---------------------------------------------------------------- 前厅
def foyer_columns():
    """中央前厅 20 根明柱：两列十根，间距 24 m。"""
    n = FOYER["n_col"] // 2
    y0 = FOYER["y0"] + (FOYER["y1"] - FOYER["y0"] - (n - 1) * 24.0) / 2.0
    out = []
    for x in (-372.0, -328.0):
        for i in range(n):
            out.append((x, y0 + i * 24.0))
    return out


DOORS = {
    # 观众厅后墙（前厅→厅内）三樘铜门
    "hall": [(-389.0, AXIS_Y + d, 8.0, 7.0) for d in (-30.0, 0.0, 30.0)],
    # 东立面（广场→前厅）：【作者·2026-11-25】五樘铜门改为整面玻璃幕墙＋24 m 玻璃门斗
    "foyer": [],
}


# ---------------------------------------------------------------- 对账
def check():
    st = seat_stats()
    tot = total_seats()
    lines = [
        f'中厅体块 {BUILD["x1"] - BUILD["x0"]:.0f} × {BUILD["y1"] - BUILD["y0"]:.0f} m，檐高 {BUILD["h"]:.0f} m',
        f'观众厅：台口 {HALL["w_front"]:.0f} m 宽 × {PROSCENIUM["h"]:.0f} m 高，'
        f'后墙 {HALL["w_rear"]:.0f} m 宽，进深 {HALL["depth"]:.0f} m，净高 {HALL["z_apex"]:.0f} m',
    ]
    for k in ("pit", "bal1", "bal2"):
        d = st[k]
        lines.append(
            f'{d["name"]}：{d["rows"]} 排 / {d["seats"]:,} 席（目标 {d["target"]:,}），'
            f'r {d["r"][0]:.1f}—{d["r"][1]:.1f} m，地坪 {d["z"][0]:.1f}—{d["z"][1]:.1f} m')
    lines += [
        f'观众厅合计 {tot:,} 席；主席台 {STAGE_SEATS} 席（不计入万人席）；'
        f'总容量 {tot + STAGE_SEATS:,}',
        f'最远观众距台口 {max(t["r1"] for t in TIERS) - 36.06:.1f} m（台口对角线距离）',
        f'中央前厅 {FOYER["x1"] - FOYER["x0"]:.0f} m 深 × '
        f'{FOYER["y1"] - FOYER["y0"]:.0f} m 宽，{FOYER["n_col"]} 根明柱，净高 {FOYER["h"]:.0f} m',
        f'国徽：{"直径 " + format(EMBLEM["d"], ".1f") + " m" if EMBLEM.get("show", True) else "不做浮雕"}'
        f'（作者 2026-11-23/24 裁决）；台口旗：'
        f'{"设" if FLAGS_AT_PROSCENIUM else "不设"}；代表席小桌：'
        f'{"设" if REP_DESKS else "不设"}（作者 2026-11-23 裁决）',
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- 自检
def _scan():
    for t in TIERS:
        rows = tier_rows(t)
        if not rows:
            print(f'{t["name"]:6s} 空')
            continue
        print(f'{t["name"]:6s} r {rows[0]["r"]:.1f}—{rows[-1]["r"]:.1f} '
              f'{len(rows):3d} 排 {sum(x["seats"] for x in rows):6,} 席 '
              f'（目标 {t["target"]:,}）')
    print(f'合计 {total_seats():,}')


if __name__ == "__main__":
    print(check())
    print()
    _scan()
