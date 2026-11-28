"""万人大礼堂 —— 视线校核。

对每一层座席的每一排，算「越过本层挑台前缘栏板」能看到主席台上多低的东西，
并给出三项判据：

    z_floor   台面本身（+1.5 m）能否看见
    z_head    主席台就坐者的头部（台面 +1.30 m）能否看见
    z_top     台口上缘（+22 m）能否看见

判据的几何：座席眼高取该排地坪 +1.15 m；遮挡物取**本层挑台前缘栏板**
（半径 r_front、板顶 = 该层前缘地坪 +0.95 m）。挑台只遮挡比自己低的目标，
因此各层只需校核自己的栏板与（对池座后区而言）上一层挑台的底面。

    py -3 sightline.py            # 打印表格
    py -3 sightline.py --summary  # 每层「几排看得见」汇总 + 挑台需要多陡
    py -3 sightline.py --json     # 供 build_draft.py 画视线图
"""

from __future__ import annotations

import json
import math
import sys

import hall_data as D

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

FX, FY = D.FOCUS["x"], D.FOCUS["y"]
EYE = 1.15          # 坐姿眼高
RAIL = 0.95         # 挑台前缘栏板高
STAGE_DECK = D.STAGE["z"]
HEAD = 1.30         # 就坐者头顶相对台面
TARGETS = {
    "deck": STAGE_DECK,
    "head": STAGE_DECK + HEAD,
    "top": D.PROSCENIUM["h"],
}


def visible_floor(r_seat, z_eye, r_front, z_rail, r_target):
    """越过拦板后，在目标半径处能看到的最高遮挡下界（低于此值看不见）。"""
    if r_seat <= r_target:
        return None
    t = (r_seat - r_front) / (r_seat - r_target)
    return z_eye + (z_rail - z_eye) * (1.0 / (1.0 - t)) if t < 1.0 else z_eye


def sight_limit(r_seat, z_eye, r_front, z_rail, r_target):
    """在 r_target 处，视线（过栏板顶）的高度。低于它的东西看不见。"""
    if r_seat <= r_front + 0.01 or r_front <= r_target:
        return -999.0      # 该排就在栏板处，无遮挡
    k = (z_eye - z_rail) / (r_seat - r_front)      # 每米下落的米数
    return z_rail - k * (r_front - r_target)


def tier_report(tier):
    rows = D.tier_rows(tier)
    r_front = tier["r0"] if tier.get("wrap", 0) == 0 else D.tier_front_for_axis(tier)
    z_rail = tier["z0"] + RAIL
    out = []
    for row in rows:
        r = row["r"]
        if r < r_front - 0.01:
            continue
        z_eye = row["z"] + EYE
        lim = sight_limit(r, z_eye, r_front, z_rail, 36.06)
        out.append({
            "r": round(r, 2),
            "z_eye": round(z_eye, 2),
            "limit": round(lim, 2),
            "deck": lim <= TARGETS["deck"],
            "head": lim <= TARGETS["head"],
            "top": lim <= TARGETS["top"],
        })
    return out


def need_slope(tier, target, n_rows=None):
    """末排要看见「目标高度」，本层坡度至少多少。

    由 lim(rear) ≤ target 解出：
        s ≥ (z0 + RAIL − target)/(r_front − r_t) − (EYE − RAIL)/(r_rear − r_front)
    与进深几乎无关（最后一项很小），主导项是「栏板高出目标多少 ÷ 到台口的水平距离」。
    """
    rows = D.tier_rows(tier)
    r_front = tier["r0"]
    r_rear = rows[-1]["r"]
    a = r_front - 36.06
    d = max(r_rear - r_front, 1e-6)
    if a <= 0:
        return None
    return (tier["z0"] + RAIL - target) / a - (EYE - RAIL) / d


def z0_for_slope(tier, slope, target):
    """保持给定坡度时，本层起点标高最多多少才能让末排看见目标（反函数）。"""
    rows = D.tier_rows(tier)
    a = tier["r0"] - 36.06
    d = max(rows[-1]["r"] - tier["r0"], 1e-6)
    return target - RAIL + a * (slope + (EYE - RAIL) / d)


def print_summary(res):
    step = D.SEAT["row"]
    print("每层可见性（判据：越过本层挑台前缘栏板）")
    for t in D.TIERS:
        rep = res[t["key"]]
        if not rep:
            continue
        n = len(rep)
        deck = sum(1 for x in rep if x["deck"])
        head = sum(1 for x in rep if x["head"])
        top = sum(1 for x in rep if x["top"])
        riser = t["slope"] * step * 100
        print(f'  {t["name"]}: 见台面 {deck}/{n} 排、见头部 {head}/{n} 排、'
              f'见台口上缘 {top}/{n} 排；坡度 {t["slope"]:.2f}（每排升 {riser:.0f} cm）')
        for label, target in (("台面", TARGETS["deck"]), ("头部", TARGETS["head"])):
            s = need_slope(t, target)
            if s is None:
                continue
            z0 = z0_for_slope(t, t["slope"], target)
            mark = "已满足" if s <= t["slope"] + 1e-9 else \
                   f"需坡度 {s:.2f}（每排 {s * step * 100:.0f} cm），或 z0 ≤ {z0:.2f} m"
            print(f'      末排看{label}: {mark}')
    print(f'\n目标：台面 {TARGETS["deck"]:.2f} / 头部 {TARGETS["head"]:.2f} / '
          f'台口上缘 {TARGETS["top"]:.2f} m')


def main():
    D.tier_front_for_axis = lambda t: t["r0"]
    res = {}
    for t in D.TIERS:
        res[t["key"]] = tier_report(t)

    if "--summary" in sys.argv:
        print_summary(res)
        if "--json" in sys.argv:
            print(json.dumps(res, ensure_ascii=False))
        return

    lines = []
    for t in D.TIERS:
        rep = res[t["key"]]
        if not rep:
            continue
        first, last = rep[0], rep[-1]
        ok_deck = sum(1 for x in rep if x["deck"])
        ok_head = sum(1 for x in rep if x["head"])
        lines.append(
            f'{t["name"]}: 前缘 r={t["r0"]:.1f} 栏板顶 {t["z0"] + RAIL:.2f} m；'
            f'共 {len(rep)} 排，能看见台面的 {ok_deck} 排、能看见就坐者头部的 {ok_head} 排')
        lines.append(
            f'    首排 r={first["r"]:.1f} 眼高 {first["z_eye"]:.2f} → 台面处可见下界 '
            f'{first["limit"]:.2f} m')
        lines.append(
            f'    末排 r={last["r"]:.1f} 眼高 {last["z_eye"]:.2f} → 台面处可见下界 '
            f'{last["limit"]:.2f} m')
    print("\n".join(lines))
    print(f'\n目标：台面 {TARGETS["deck"]:.2f} / 就坐者头部 {TARGETS["head"]:.2f} / '
          f'台口上缘 {TARGETS["top"]:.2f} m')
    if "--json" in sys.argv:
        print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------- 全席扫描
def parapet_r(tier, th):
    return max(tier["r0"] - tier.get("wrap", 0.0) * (th / tier.get("theta_ref", 0.5)) ** 2,
               D.tier_rows(tier)[0]["r"])


def seat_view(tier, th, r, target):
    """任意位置的座席（可不在中轴上）望目标点，返回在自身楼板边缘处的视线高度。"""
    x, y = FX + r * math.cos(th), FY + r * math.sin(th)
    if not (D.HALL["x_front"] <= x <= D.HALL["x_rear"]):
        return None
    if abs(y - D.AXIS_Y) > D.HALL["w_front"] / 2 + (x - D.HALL["x_front"]) * (
            D.HALL["w_rear"] - D.HALL["w_front"]) / (2 * D.HALL["depth"]):
        return None
    z_eye = tier["z0"] + max(0.0, r - tier["r0"]) * tier["slope"] + EYE
    if tier["key"] == "pit":
        return 999.0            # 池座无上覆栏板，不受挑台遮挡
    tx, ty, tz = target
    n = 400
    for i in range(1, n):
        t = i / n
        px, py = x + (tx - x) * t, y + (ty - y) * t
        pr = math.hypot(px - FX, py - FY)
        pth = math.atan2(py - FY, px - FX)
        if pr < parapet_r(tier, pth):
            z_hit = z_eye + (tz - z_eye) * t
            return 1.0 if z_hit >= tier["z0"] + RAIL else -1.0
    return 999.0


def scan(target):
    st = {}
    for t in D.TIERS:
        ok = bad = 0
        arms_ok = arms_bad = 0
        for th in (-0.52, -0.4, -0.28, -0.14, 0.0, 0.14, 0.28, 0.4, 0.52):
            for r in [t["r0"] + k * 2.0 for k in range(1, 12)]:
                v = seat_view(t, th, r, target)
                if v is None:
                    continue
                good = v > 0
                ok += good
                bad += (not good)
                if abs(th) >= 0.28:
                    arms_ok += good
                    arms_bad += (not good)
        st[t["key"]] = (ok, bad, arms_ok, arms_bad)
    return st
