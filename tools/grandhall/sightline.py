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
    py -3 sightline.py --json     # 供 build_draft.py 画视线图
"""

from __future__ import annotations

import json
import sys

import hall_data as D

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


def main():
    D.tier_front_for_axis = lambda t: t["r0"]
    res = {}
    for t in D.TIERS:
        res[t["key"]] = tier_report(t)
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
