"""窄断言：作者进去“看一眼”之前，先把能算的数算掉。

为什么不是通用几何体检：作者提的 5 条里 4 条不是几何问题——
净空 1.99 m 在几何上完全合法（两张面离 1.99 m 有什么错？），
“横向过道不存在”是**缺失**，任何包围盒/面级检查都查不出。
所以这里查的是**关系与规格**，且每条口径都钉死在代码里，不靠人推。

数据来源只有两个，都不需要 Blender、不需要 import build_hall：
  * `tools/grandhall/hall_data.py`（零副作用，派生几何的唯一入口）
  * `build/hall_manifest.json`（`build_hall.py --no-render --manifest` 产出）

用法：
    py -3 tools/audit/asserts.py                       # 用 build/hall_manifest.json
    py -3 tools/audit/asserts.py --manifest X.json --json out.json
    py -3 tools/audit/asserts.py --fail-on-warn        # 待裁项也当失败（CI 用）

退出码：0 全过；1 有 FAIL（或 --fail-on-warn 下有 WARN）；2 参数/文件问题。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

try:                      # MSYS bash 里控制台是 UTF-8，Python 默认 cp936 会输出乱码
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GRANDHALL = os.path.join(ROOT, "tools", "grandhall")
if GRANDHALL not in sys.path:
    sys.path.insert(0, GRANDHALL)

import hall_data as D  # noqa: E402
import sightline as SL  # noqa: E402  # 复用 EYE/RAIL/R_TARGET，口径只留一份

DEFAULT_MANIFEST = os.path.join(ROOT, "build", "hall_manifest.json")

# 门槛（与作品会话来定 2026-11-28）
HEADROOM_MIN = 2.30       # 挑台下净空
AISLE_MIN = 1.50          # 横向过道宽
AISLE_COUNT_MIN = 2       # 每层横向过道处数
GAP_TOL = 0.02            # 座椅离地容差（2 cm）
# 席/m²。人民大会堂实物 = 9,726/(76×60) = 2.13。
# 旧区间 0.9–2.4 是按「进深 95、后区 40 m 空场」的旧平面定的；
# 作者 2026-11-28 改为「座席贴后墙」后，密度必然上移，故按实物重定 1.6–2.6。
DENSITY_RANGE = (1.6, 2.6)
REAR_VOID_RANGE = (0.5, 2.0)   # 【作者·2026-11-28】末排贴墙：座背到后墙面 0.5–2 m


def load_manifest(path):
    """读 manifest；schema 统一在 manifest_io 里，别在这里另写一份解析。"""
    from manifest_io import load
    return load(path)


def by_group(items, group):
    return [i for i in items if i["group"] == group]


def r_of(x, y):
    return math.hypot(x - D.FOCUS["x"], y - D.FOCUS["y"])


def plan_area():
    """观众厅平面面积（鞋带公式，量的是 hall_plan() 这个唯一口子）。"""
    poly = D.hall_plan()
    s = 0.0
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


# ------------------------------------------------------------------ 断言
def seat_floor_gap(items):
    """① seat.floor_gap：座箱底面 − 同排楼板高。口径：取该层最前一排的楼板高。"""
    detail, worst = [], 0.0
    for idx, tier in enumerate(D.TIERS):
        g = by_group(items, f"seat{idx}")
        if not g:
            detail.append(f"{tier['key']}: 无 seat{idx} 物体")
            continue
        rows = D.tier_rows(tier)
        floor_z = D.tier_row_z(tier, rows[0]["r"])
        gap = round(min(i["min"][2] for i in g) - floor_z, 3)
        worst = max(worst, abs(gap))
        detail.append(f"{tier['key']}: 底 {min(i['min'][2] for i in g):.3f} − 楼板 "
                      f"{floor_z:.3f} = {gap:+.3f} m")
    return abs(worst) <= GAP_TOL, f"最大偏离 {worst:.3f} m（容差 {GAP_TOL}）", detail


def balcony_headroom(items):
    """② bal2.headroom：三层底面与二层楼板的最小净空（同一半径对同一半径）。

    旧口径是「三层全局最低点 − 二层楼板最高点」，只在三层整体高于二层末排时成立。
    2026-11-29 两层挑台径向重叠（二层 r 60—82、三层 r 64—82）后该口径会误报：
    三层前端（r=64）最低、二层末排（r=82）最高，两个点根本不在同一半径上。改为逐排
    比同一半径；板厚不写死，由「三层起点标高 − 其网格最低点」反推。
    """
    b2 = by_group(items, "bal2")
    if not b2:
        return False, "无 bal2 物体", []
    bal1 = [t for t in D.TIERS if t["key"] == "bal1"][0]
    bal2 = [t for t in D.TIERS if t["key"] == "bal2"][0]
    soffit_front = min(i["min"][2] for i in b2)
    slab = round(bal2["z0"] - soffit_front, 3)      # 板厚，从几何反推（不新增常量）
    worst = None
    for row in D.tier_rows(bal1):
        r = row["r"]
        if r < bal2["r0"] - 0.01:
            continue
        x, y = D.FOCUS["x"] + r, D.FOCUS["y"]
        floor1 = D.tier_z(bal1, x, y, clamp=True)
        soffit2 = D.tier_z(bal2, x, y, clamp=True) - slab
        h = soffit2 - floor1
        if worst is None or h < worst[0]:
            worst = (h, r, floor1, soffit2)
    if worst is None:
        return False, "二三层没有径向重叠，无从比较", []
    h, r, floor1, soffit2 = worst
    h = round(h, 3)
    detail = [f"板厚 {slab:.3f}（三层起点 {bal2['z0']:.2f} − 网格最低 {soffit_front:.3f}）",
              f"最紧处 r={r:.1f}：三层底 {soffit2:.3f} − 二层板 {floor1:.3f} = {h:.3f} m"]
    return h >= HEADROOM_MIN, f"{h:.3f} m（门槛 {HEADROOM_MIN}）", detail

def tier_overhang(items):
    """④��� tier.overhang：下层座席被**上层挑台前缘**切掉的那一段台口。

    为什么另算：`sightline.py` 只判「本层自己的栏板」——二层真正的遮挡物是三层楼板
    （板底到栏板顶那条带子）。2026-11-29 查：方案B 后三层前缘压在二层后半段之上，
    三层 z0=12 时二层有 12 排只能看见台面以下（切到 7 m）。抬三层到 15.6 后剩 8 排、
    且只切 13 m 以上（台口上缘，纯装饰面）。门槛取 10 m：切到 10 m 以下才算真问题。
    """
    b2 = by_group(items, "bal2")
    if not b2:
        return False, "无 bal2 物体", []
    bal1 = [t for t in D.TIERS if t["key"] == "bal1"][0]
    bal2 = [t for t in D.TIERS if t["key"] == "bal2"][0]
    slab = round(bal2["z0"] - min(i["min"][2] for i in b2), 3)
    band = (bal2["z0"] - slab, bal2["z0"] + SL.RAIL)   # 三层前缘的实体带（板底→栏板顶）
    cut_rows, worst = [], 99.0
    for row in D.tier_rows(bal1):
        r = row["r"]
        if r <= bal2["r0"] + 0.01:
            continue
        # 目标 t 被挡 ⇔ 眼到 t 的视线在 r0 处的高度落进 band：
        #   z(r0) = ze + (t − ze)·(r0 − r_t)/(r − r_t)，对 t 反解
        kr = (bal2["r0"] - SL.R_TARGET) / (r - SL.R_TARGET)
        ze = row["z"] + SL.EYE
        edges = sorted(ze + (b - ze) * kr for b in band)
        if edges[1] > 1.5 and edges[0] < SL.TARGETS["top"]:
            cut_rows.append(r)
            worst = min(worst, edges[0])
    n = len(cut_rows)
    if not n:
        return True, "二层零遮挡", ["三层前缘实体带整条落在二层末排视线之上"]
    detail = [f"被切 {n} 排（r {cut_rows[0]:.1f} 起），最高起切点 {worst:.2f} m",
              f"三层前缘实体带 {band[0]:.2f}—{band[1]:.2f} m（板厚 {slab:.3f}）"]
    return worst >= 10.0, f"{n} 排只丢台口上缘，自 {worst:.2f} m 起切", detail


def cross_aisles():
    """③ cross_aisle_count：每层横向过道处数（数据声明，不是从几何里找缺口）。

    “过道不存在”只能这样查——几何上少一排座椅是合法的，包围盒看不出意图。
    """
    detail, ok = [], True
    for tier in D.TIERS:
        ais = tier.get("aisles") or {}
        widths = {k: float(v) for k, v in ais.items() if float(v or 0) > 0}
        wide = [k for k, v in widths.items() if v >= AISLE_MIN]
        if len(wide) < AISLE_COUNT_MIN:
            ok = False
        detail.append(f"{tier['key']}: {len(wide)} 处 ≥{AISLE_MIN} m "
                      + "，".join(f"{k}={v:g}" for k, v in widths.items()))
    return ok, f"每层 ≥{AISLE_COUNT_MIN} 处", detail


def rear_void():
    """④ pit.rear_void：池座末排到后墙的距离。

    口径（作者 2026-11-28）：「座位最后面就是墙/门，不留空地」——所以这不是
    待裁项，是硬约束：座背到墙面只留 0.5–2 m（出门与门斗的做法余量）。
    """
    pit = [t for t in D.TIERS if t["key"] == "pit"][0]
    rows = D.tier_rows(pit)
    rear = D.hall_radius(0.0)
    void = round(rear - rows[-1]["r"], 2)
    detail = [f"末排 r={rows[-1]['r']:.2f}，后墙 r={rear:.2f}", f"空场 {void} m"]
    ok = REAR_VOID_RANGE[0] <= void <= REAR_VOID_RANGE[1]
    return ok, f"{void} m（要求 {REAR_VOID_RANGE[0]}–{REAR_VOID_RANGE[1]}）", detail


def seat_density(seats):
    """⑤ 席密度：席数 ÷ 池座平面面积。区间是参考，不硬卡。"""
    area = plan_area()
    n = seats or D.total_seats()
    dens = round(n / area, 3)
    lo, hi = DENSITY_RANGE
    ok = lo <= dens <= hi
    detail = [f"{n} 席 / {area:.0f} m²（平面 {D.HALL['w_front']:g}→{D.HALL['w_rear']:g}"
              f" × {D.HALL['depth']:g} m）", f"{dens} 席/m²（参考 {lo}–{hi}）"]
    return ok, f"{dens} 席/m²", detail


FWD_AIM = 0.99            # 朝向 · 规定方向
FWD_UNIT_TOL = 2e-3       # 朝向必须是单位向量
FWD_REPORT_TOL = 0.02     # 样本重算值 vs 构建端记录值


def audience_dir():
    """观众厅在台口的哪一侧（+x / −x）。与 build_hall 同源，各自从 hall_data 推。"""
    dx = D.HALL["x_rear"] - D.PROSCENIUM["x"]
    return (1.0 if dx > 0 else -1.0, 0.0)


def seat_forward(facing):
    """⑥ seat.forward：每一组椅子到底朝哪一侧。

    本项前三轮都是 SKIP，理由是「manifest 没有朝向字段」——那时确实没有，
    而**猜出来的通过比不查更危险**。现在构建端给了：在落进网格的顶点上取
    「座心 − 靠背心」→ 单位朝向，再记对齐度的全量 min/max/mean，
    并按步长抽样（含首末座）存原始 (座心, 朝向)。

    这里不采信它报的数，逐样本自己重算：
      1. |fwd| 必须为单位向量（挡住零向量/退化朝向）；
      2. 观众席（aim=focus）朝向 · 指向扇心 ≥ 0.99——正对舞台；
         主席团（aim=audience）朝向 · 观众厅方向 ≥ 0.99——坐在台上、面向观众。
         两个基准方向都由本脚本从 hall_data 现推，不用 manifest 的说法；
      3. 重算值与构建端记录值差 ≤ 0.02，且落在它报的 [min,max] 内——
         否则两端口径不同源，样本代表不了全量。

    能抓住的真实缺陷：模板旋转错半圈、靠背与座垫两串盒子写反、
    主席团椅背落到 +x 侧（作者 2026-11-28 抓到的那个）。
    注：主席团九椅是**一排平行朝前**的，用逐座扇心方向量只有正中间＝−1，
    其余 −0.68…——所以基准必须按角色分，否则会拿错尺子冤枉对的模型。
    """
    if not isinstance(facing, dict) or not facing.get("groups"):
        return None, "SKIP：manifest 无 seat_facing（旧 manifest，重建即可）", [
            "构建端已写 seat_facing；当前 manifest 落后于代码。",
            "重新出一次：build_hall.py --no-render --manifest build/hall_manifest.json"]

    focus = facing.get("focus") or []
    if len(focus) != 2:
        return False, "seat_facing 缺扇心坐标", ["重算 cos 需要 FOCUS(x,y)"]
    fx0, fy0 = focus
    aud = audience_dir()

    bad, rows, margin = [], [], 9.9
    for g in facing["groups"]:
        name = g.get("group", "?")
        role, aim = g.get("role"), g.get("aim")
        n = int(g.get("n") or 0)
        samples = g.get("samples") or []
        want_aim = {"audience": "focus", "chairman": "audience"}.get(role)
        if want_aim is None:
            bad.append(f"{name}：未知 role={role!r}")
            continue
        if aim != want_aim:
            bad.append(f"{name}：role={role} 应当用 aim={want_aim}，manifest 写 {aim!r}")
            continue
        if n <= 0 or not samples:
            bad.append(f"{name}：n={n} 样本={len(samples)}（无样本可重算）")
            continue
        cs = []
        for sp in samples:
            if len(sp) != 5:
                bad.append(f"{name}：样本格式 {sp!r}")
                continue
            x, y, ux, uy, rep = sp
            ln = math.hypot(ux, uy)
            if abs(ln - 1.0) > FWD_UNIT_TOL:
                bad.append(f"{name} @({x:.0f},{y:.0f})：朝向非单位向量 |f|={ln:.4f}")
                continue
            if aim == "focus":
                dx, dy = fx0 - x, fy0 - y
            else:
                dx, dy = aud
            dl = math.hypot(dx, dy) or 1.0
            c = (ux * dx + uy * dy) / dl
            cs.append(c)
            margin = min(margin, c - FWD_AIM)
            if c < FWD_AIM:
                bad.append(f"{name} @({x:.0f},{y:.0f})：对齐 {c:+.3f} < {FWD_AIM}")
            if abs(c - rep) > FWD_REPORT_TOL:
                bad.append(f"{name} @({x:.0f},{y:.0f})：重算 {c:+.3f} ≠ 记录 {rep:+.3f}")
        if not cs:
            continue
        lo, hi = min(cs), max(cs)
        if lo < (g.get("cos_min") or -9) - FWD_REPORT_TOL \
                or hi > (g.get("cos_max") or 9) + FWD_REPORT_TOL:
            bad.append(f"{name}：样本 {lo:+.3f}…{hi:+.3f} 落在构建端报告"
                       f" {g.get('cos_min'):+.3f}…{g.get('cos_max'):+.3f} 之外")
        rows.append(f"{name}（{role}／基准 {aim}）n={n} 样本{len(samples)}："
                    f"对齐 {lo:+.3f}…{hi:+.3f}，要求 ≥ {FWD_AIM}")

    if bad:
        return False, f"{len(bad)} 处朝向不符", bad[:8] + rows
    aud_n = sum(int(g.get("n") or 0) for g in facing["groups"]
                if g.get("role") == "audience")
    ch_n = sum(int(g.get("n") or 0) for g in facing["groups"]
               if g.get("role") == "chairman")
    return True, (f"{len(rows)} 组朝向成立：观众席 {aud_n:,} + 主席团 {ch_n} 把"
                  f"（最差余量 {margin:+.3f}）"), rows



def seat_module():
    """⑥ seat.module：座椅模数不变式（尺寸全部来自 hall_data.SEAT_DETAIL，一处定死）。"""
    Q, S = D.SEAT_DETAIL, D.SEAT
    checks = [
        ("座垫宽 + 2×边距 = 座距",
         abs(Q["pad_w"] + 2 * Q["gap_side"] - S["pitch"]) < 1e-9,
         f"{Q['pad_w']} + 2×{Q['gap_side']} = {S['pitch']}"),
        ("座深 + 靠背厚 ≤ 排距 − 0.35（净腿）",
         Q["pad_d"] + Q["back_t"] <= S["row"] - 0.35 + 1e-9,
         f"{Q['pad_d']} + {Q['back_t']} ≤ {S['row']} − 0.35"),
        ("扶手外缘 ≤ 半座距",
         Q["arm_off"] + Q["arm_w"] / 2 <= S["pitch"] / 2 + 1e-9,
         f"{Q['arm_off'] + Q['arm_w'] / 2:.3f} ≤ {S['pitch'] / 2:.3f}"),
        ("桌板不超过上限（否则穿前排靠背）",
         all(v <= Q["desk_d_max"] + 1e-9 for v in Q["desk_d_tiers"].values()),
         f"{Q['desk_d_tiers']} ≤ {Q['desk_d_max']}"),
        ("座面高 = 座箱 + 座板",
         abs(Q["box_h"] + Q["board_h"] - 0.44) < 0.03,
         f"{Q['box_h'] + Q['board_h']:.2f} m"),
    ]
    bad = [n for n, ok, _ in checks if not ok]
    return not bad, ("全部成立" if not bad else f"{len(bad)} 条不成立"), \
        [f"{'✓' if ok else '✗'} {n}（{d}）" for n, ok, d in checks]


def origin_stack(items):
    """附赠①：物体堆在原点（palace 的 90 根屋脊就是这么来的）。"""
    bad = []
    for i in items:
        cx = (i["min"][0] + i["max"][0]) / 2
        cy = (i["min"][1] + i["max"][1]) / 2
        if abs(cx) < 5 and abs(cy) < 5:
            bad.append(f"{i['name']} @ ({cx:.1f}, {cy:.1f})")
    return not bad, f"{len(bad)} 个", bad[:6]


def out_of_shell(items):
    """附赠②：越出中厅体块（x −540…−310、y −1155.5…−915.5、z 0…50）。"""
    b = D.BUILD
    bad = []
    for i in items:
        if (i["min"][0] < b["x0"] - 1 or i["max"][0] > b["x1"] + 1
                or i["min"][1] < b["y0"] - 1 or i["max"][1] > b["y1"] + 1
                or i["max"][2] > b["h"] + 20):
            bad.append(f"{i['name']} x[{i['min'][0]:.0f},{i['max'][0]:.0f}] "
                       f"z[{i['min'][2]:.1f},{i['max'][2]:.1f}]")
    return not bad, f"{len(bad)} 个", bad[:6]


# ------------------------------------------------------------------ 主流程
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=DEFAULT_MANIFEST)
    ap.add_argument("--json", default="")
    ap.add_argument("--fail-on-warn", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.manifest):
        print(f"找不到 manifest：{args.manifest}\n"
              f"先生成：blender -b ... -P build_hall.py -- --precise --draco "
              f"--no-render --manifest build/hall_manifest.json", file=sys.stderr)
        return 2

    doc, items, totals = load_manifest(args.manifest)
    print(f"manifest：{args.manifest}")
    print(f"  mode={doc.get('mode')} 物体={totals['objects']} "
          f"三角面={totals['tris']:,} 席={totals['seats']}\n")

    checks = [
        ("seat.floor_gap", "座箱底 − 同排楼板高", *seat_floor_gap(items)),
        ("bal2.headroom", "三层最低点 − 二层楼板（clamp）", *balcony_headroom(items)),
        ("tier.overhang", "二层被三层挑台切掉的台口", *tier_overhang(items)),
        ("cross_aisle", "每层横向过道 ≥1.5 m 的处数", *cross_aisles()),
        ("pit.rear_void", "池座末排 → 后墙", *rear_void()),
        ("seat.density", "席数 ÷ 观众厅平面", *seat_density(totals["seats"])),
        ("seat.forward", "靠背在座心之后 · 观众席指扇心／主席团指观众厅",
         *seat_forward(doc.get("seat_facing"))),
        ("seat.module", "座椅族模数不变式", *seat_module()),
        ("origin_stack", "物体中心离原点 <5 m", *origin_stack(items)),
        ("out_of_shell", "越出中厅体块", *out_of_shell(items)),
    ]

    fails = warns = 0
    out = []
    for name, caliper, ok, summary, detail in checks:
        tag = "PASS" if ok is True else ("WARN/SKIP" if ok is None else "FAIL")
        if ok is False:
            fails += 1
        elif ok is None:
            warns += 1
        print(f"[{tag:9s}] {name:15s} {caliper}")
        print(f"            → {summary}")
        for d in detail:
            print(f"              · {d}")
        out.append({"name": name, "ok": ok, "summary": summary, "detail": detail})
    print(f"\n合计：{len(checks) - fails - warns} 通过 / {fails} 失败 / {warns} 待裁或跳过")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"manifest": args.manifest, "checks": out,
                       "fails": fails, "warns": warns}, fh, ensure_ascii=False, indent=1)
        print(f"结果已存 {args.json}")

    if fails:
        return 1
    if warns and args.fail_on_warn:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
