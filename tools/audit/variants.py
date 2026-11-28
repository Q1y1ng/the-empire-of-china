"""变体：一次算出三套「厅/席」方案的数字，让作者用数选，而不是改一版看一眼。

为什么需要它：作者卡在“观众厅 9,500 m² 放 10,340 席，密度 1.088，而人民大会堂约 2.2”。
这既是规格也是几何——改一版要动 `HALL` 深度、三层 `r1`、走道数，然后重建 30 s、
出图 3.5 min，作者进 Unity 看一眼说“不对”再来一轮。三套方案的数字其实**现在就能算准**。

做法：临时替换 `hall_data` 的 `HALL` / `TIERS`，调它自己的 `tier_rows()` 求席数——
不复写任何式子（复写就是第 N 份重复）。算完恢复原状。

用法：
    py -3 tools/audit/variants.py
    py -3 tools/audit/variants.py --json out.json
"""
from __future__ import annotations

import argparse
import copy
import json
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

TARGET_SEATS = 10_000     # 设定口径：约一万席
PROSCENIUM_R = 36.06      # 台口对角线距离（hall_data.check() 里的口径）

# 三套方案：只改「厅的进深/后墙宽」与「池座末排半径上限」，其余照旧
SCHEMES = [
    {"key": "current", "name": "现状", "depth": None, "w_rear": None,
     "pit_r1": None, "note": "不改，作为基线"},
    {"key": "shrink", "name": "缩厅", "depth": 70.0, "w_rear": 120.0,
     "pit_r1": None, "note": "后墙前移 25 m，收紧后区空场，密度上去了但席数会降"},
    {"key": "fill", "name": "铺满", "depth": None, "w_rear": None,
     "pit_r1": 110.0, "note": "池座铺到接近后墙（10,000 席口径下密度最高）"},
]


def _area(depth, w_front, w_rear):
    return (w_front + w_rear) / 2.0 * depth


def simulate(scheme):
    """临时改 hall_data 的全局，跑它的 tier_rows 求席数，最后原样恢复。"""
    old_hall = dict(D.HALL)
    old_tiers = copy.deepcopy(D.TIERS)
    try:
        depth = scheme["depth"] or D.HALL["depth"]
        w_rear = scheme["w_rear"] or D.HALL["w_rear"]
        D.HALL["depth"] = depth
        D.HALL["w_rear"] = w_rear
        D.HALL["x_rear"] = D.HALL["x_front"] + depth

        # 厅的后墙半径（扇心到后墙）：方案变浅时，把越界的层截回来
        r_wall = depth + (D.FOCUS["x"] * -1 - D.HALL["x_front"])
        r_wall = depth + 30.0          # 扇心在台口后 30 m，与 hall_radius(0) 同口径

        tiers = []
        for t in D.TIERS:
            t = dict(t)
            if scheme["key"] == "fill" and t["key"] == "pit":
                t["r1"] = min(scheme["pit_r1"], r_wall - 2.0)
            else:
                t["r1"] = min(t["r1"], r_wall - 2.0)
            tiers.append(t)
        D.TIERS = tiers

        per_tier = {}
        for t in tiers:
            per_tier[t["key"]] = sum(r["seats"] for r in D.tier_rows(t))
        seats = sum(per_tier.values())
        area = _area(depth, D.HALL["w_front"], w_rear)
        far = max(t["r1"] for t in tiers) - PROSCENIUM_R

        # 净空不在这里算：它要靠 bal2 网格的底面（asserts.py 的口径，3.566 m）。
        # 这里若用 z0 相减会得出 5.47——那是层间高差，不是净空，两个数并排放就是新的口径病。
        bal1 = [t for t in tiers if t["key"] == "bal1"][0]

        # 后区空场：池座末排到后墙
        pit = [t for t in tiers if t["key"] == "pit"][0]
        rows = D.tier_rows(pit)
        void = round(r_wall - rows[-1]["r"], 1) if rows else None

        return {
            "key": scheme["key"], "name": scheme["name"], "note": scheme["note"],
            "depth": depth, "w_rear": w_rear, "area": round(area, 0),
            "seats": seats, "per_tier": per_tier,
            "density": round(seats / area, 3),
            "far_sight": round(far, 1),
                        "rear_void": void,
            "meets_target": seats >= TARGET_SEATS,
        }
    finally:
        D.HALL.clear()
        D.HALL.update(old_hall)
        D.TIERS = old_tiers


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="")
    args = ap.parse_args()

    base_seats = D.total_seats()
    rows = [simulate(s) for s in SCHEMES]

    print(f"厅/席三方案（基线 {base_seats} 席，目标 ≥{TARGET_SEATS}）\n")
    head = f"{'方案':6s} {'进深':>5s} {'后墙宽':>6s} {'面积':>7s} {'席数':>6s} " \
           f"{'密度':>5s} {'最远':>5s} {'后区空场':>7s} {'达标':>4s}"
    print(head)
    print("-" * len(head))
    for r in rows:
        print(f"{r['name']:6s} {r['depth']:5.0f} {r['w_rear']:6.0f} {r['area']:7.0f} "
              f"{r['seats']:6d} {r['density']:5.2f} {r['far_sight']:5.1f} "
              f"{str(r['rear_void']):>7s} "
              f"{'✓' if r['meets_target'] else '✗':>4s}")

    print()
    for r in rows:
        print(f"· {r['name']}（{r['key']}）：{r['note']}")
        print(f"    分层席数 " + "，".join(f"{k} {v}" for k, v in r["per_tier"].items()))

    print("\n判据说明：密度参考 2.2（人民大会堂 76×60 m / 1 万席）；"
          "最远视距 = 末排半径 − 台口对角线。净空不在这张表里——它靠网格底面，见 asserts.py 的 3.566 m。")
    print("这三行数是给作者选的，不是改代码的依据——选定后再动几何。")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"baseline": base_seats, "schemes": rows}, fh, ensure_ascii=False, indent=1)
        print(f"已存 {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
