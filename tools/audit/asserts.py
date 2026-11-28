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
    """② bal2.headroom：三层挑台最低点 − 二层可站楼板最高点（bbox 级保守下界）。

    口径说明：不引入板厚常量（1.55 若写进来就是第 4 份重复），直接用 bal2 网格的
    最低点作“底面”。二层楼板取 clamp 后的最高值——末排之外是平台，不是继续爬坡。
    """
    b2 = by_group(items, "bal2")
    if not b2:
        return False, "无 bal2 物体", []
    soffit = min(i["min"][2] for i in b2)
    bal1 = [t for t in D.TIERS if t["key"] == "bal1"][0]
    rows = D.tier_rows(bal1)
    floor_max = max(D.tier_z(bal1, D.FOCUS["x"] + r, D.FOCUS["y"], clamp=True)
                    for r in [x["r"] for x in rows])
    h = round(soffit - floor_max, 3)
    detail = [f"三层最低点 {soffit:.3f}（{min(b2, key=lambda i: i['min'][2])['name']}）",
              f"二层楼板最高 {floor_max:.3f}（clamp 后）", f"净空 {h:.3f} m"]
    return h >= HEADROOM_MIN, f"{h:.3f} m（门槛 {HEADROOM_MIN}）", detail


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


def seat_forward():
    """⑥ seat.forward：朝向。manifest 里没有朝向字段 → 明确 SKIP，不假装通过。"""
    return None, "SKIP：manifest 无朝向字段", [
        "要查这条，需要 build_hall 在 manifest 里给每个座席组加 forward 向量，",
        "或在构建端断言：chair_forward · (FOCUS − pos) > 0，主席台 9 椅取 −1。",
        "本脚本不猜——猜出来的通过比不查更危险。"]


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
        ("cross_aisle", "每层横向过道 ≥1.5 m 的处数", *cross_aisles()),
        ("pit.rear_void", "池座末排 → 后墙", *rear_void()),
        ("seat.density", "席数 ÷ 观众厅平面", *seat_density(totals["seats"])),
        ("seat.forward", "椅面法向 · 指向扇心", *seat_forward()),
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
