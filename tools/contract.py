"""跨模型契约：两个模型之间**约定的那几个数**，只在这里写一次。

背景（2026-11-25 踩过）：万人大礼堂（内胆）与广场（外壳）靠坐标硬碰硬对齐——
`build_massing.py` 里写死了 −538/−312、±118，`hall_data.py` 里写 −540…−310 与退让 2.5，
`try_merge.py` 每次靠人肉核包围盒。三处一旦漂一个数，套合就废，而没人知道该以谁为准。

本文件收四类接口事实：中厅体块、壁厚/空腔、内胆实际范围（含已裁决的例外）、台基与下沉。

重要口径（2026-11-25 作者裁决，别再按“抬升”算）：
    中厅体块**不抬高**，万人大礼堂**下沉** 2.3 m——内胆地坪留在 z=0，
    穹顶顶 50.0 落在琉璃顶底 50.15 之下。
    早先算的“抬到台基面后 52.3、顶穿檐口”是**已否决的方案**，不要写回契约。

用法：
    py -3 tools/contract.py            # 自检：契约内部一致 + hall_data 与契约一致
    py -3 tools/contract.py --json     # 给别的脚本读

接入（各项目择机）：`build_massing.py` / `hall_data.py` / `try_merge.py` 改成
`from contract import C` 取值，别再写字面量。契约变了只有这里改。
"""
from __future__ import annotations

import argparse
import json
import os
import sys

try:                      # MSYS bash 里控制台是 UTF-8，Python 默认 cp936 会输出乱码
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GRANDHALL = os.path.join(ROOT, "tools", "grandhall")

C = {
    # 外壳外皮（广场模型「大会堂·中厅」体块）
    "hall_block": {"x0": -540.0, "x1": -310.0, "y0": -1155.5, "y1": -915.5,
                   "z_top": 50.0, "z_glass_bottom": 50.15},
    # 壁厚 2 m（外皮→内皮）、内胆与内皮之间空腔 0.5 m
    "shell": {"t": 2.0, "gap": 0.5},
    # 内胆实际范围（已落地，不是“理想退让”）
    "inner_tank": {"x0": -537.5, "x1": -311.5, "y0": -1153.0, "y1": -918.0,
                   "z_floor": 0.0, "z_apex": 50.0},
    # 已知且已裁决的例外：东面不是 gap 而是门斗面
    "exceptions": [
        {"name": "前厅东墙／玻璃门斗",
         "fact": "内胆东面 −311.5 与内腔东内皮 −312 差 +0.5 m：门斗出挑进壁厚",
         "ruling": "作者 2026-11-25 裁决：前厅东墙改玻璃门斗", },
    ],
    # 玻璃门斗（自内胆东墙向东出挑）
    "door_bay": {"half_w": 12.0, "depth": 2.2, "h": 8.0, "x": -311.5},
    # 台基 2.3 m，内胆地坪在其下 2.3 m（下沉方案）
    "podium": {"z": 2.3, "plan": [238.0, 608.0], "sink": 2.3},
}


def cavity():
    """外壳内腔（内皮所围）。"""
    b, t = C["hall_block"], C["shell"]["t"]
    return {"x0": b["x0"] + t, "x1": b["x1"] - t,
            "y0": b["y0"] + t, "y1": b["y1"] - t}


def selftest():
    rows, ok = [], True

    def check(name, cond, detail=""):
        nonlocal ok
        ok = ok and bool(cond)
        rows.append((name, bool(cond), detail))

    b, sh, tank, cav = C["hall_block"], C["shell"], C["inner_tank"], cavity()
    check("内腔 = 外皮 − 2×壁厚",
          abs((b["x1"] - b["x0"]) - 2 * sh["t"] - (cav["x1"] - cav["x0"])) < 1e-9,
          f"内腔 {cav['x1'] - cav['x0']:.1f} × {cav['y1'] - cav['y0']:.1f} m")
    check("内胆西/北/南 = 内腔 − 空腔（各 0.5）",
          abs(tank["x0"] - (cav["x0"] + sh["gap"])) < 1e-9
          and abs(tank["y0"] - (cav["y0"] + sh["gap"])) < 1e-9
          and abs(tank["y1"] - (cav["y1"] - sh["gap"])) < 1e-9,
          f"西 {tank['x0']} / 南 {tank['y0']} / 北 {tank['y1']}")
    east_delta = tank["x1"] - (cav["x1"] - sh["gap"])
    check("内胆东面 = 门斗面（已裁决例外，不算漂移）",
          abs(tank["x1"] - C["door_bay"]["x"]) < 1e-9 and east_delta > 0,
          f"东面 {tank['x1']}，理想空腔线 {cav['x1'] - sh['gap']:.1f}，"
          f"外移 {east_delta:+.1f}（门斗出挑进壁厚）")
    check("穹顶顶 ≤ 琉璃顶底", tank["z_apex"] <= b["z_glass_bottom"] + 1e-9,
          f"{tank['z_apex']} ≤ {b['z_glass_bottom']}（余 {b['z_glass_bottom'] - tank['z_apex']:.2f}）")
    check("下沉量 = 台基标高 − 内胆地坪",
          abs(C["podium"]["sink"] - (C["podium"]["z"] - tank["z_floor"])) < 1e-9,
          f"{C['podium']['sink']} = {C['podium']['z']} − {tank['z_floor']}")

    # 与 hall_data 对照（零副作用，可 import）
    if GRANDHALL not in sys.path:
        sys.path.insert(0, GRANDHALL)
    try:
        import hall_data as D
        check("hall_data.BUILD 与契约一致",
              all(abs(D.BUILD[k] - b[k]) < 1e-9 for k in ("x0", "x1", "y0", "y1"))
              and abs(D.BUILD["h"] - b["z_top"]) < 1e-9,
              f"{D.BUILD['x0']}…{D.BUILD['x1']}，顶 {D.BUILD['h']}")
        check("hall_data.SHELL 与契约一致",
              abs(D.SHELL["t"] - sh["t"]) < 1e-9 and abs(D.SHELL["gap"] - sh["gap"]) < 1e-9,
              f"t={D.SHELL['t']} gap={D.SHELL['gap']}")
        check("hall_data.DOORBAY 与契约一致",
              abs(D.DOORBAY["half_w"] - C["door_bay"]["half_w"]) < 1e-9
              and abs(D.DOORBAY["x"] - C["door_bay"]["x"]) < 1e-9,
              f"半宽 {D.DOORBAY['half_w']}（宽 {2 * D.DOORBAY['half_w']:.0f}）x={D.DOORBAY['x']}")
        check("ZONES 首尾 = 内胆东西面",
              abs(D.ZONES["backstage"]["x0"] - tank["x0"]) < 1e-9
              and abs(D.ZONES["foyer"]["x1"] - tank["x1"]) < 1e-9,
              f"{D.ZONES['backstage']['x0']} … {D.ZONES['foyer']['x1']}")
    except Exception as exc:                      # noqa: BLE001
        check("import hall_data", False, str(exc))

    return ok, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    ok, rows = selftest()

    if args.json:
        json.dump({"ok": ok, "contract": C,
                   "checks": [{"name": n, "ok": c, "detail": d} for n, c, d in rows]},
                  sys.stdout, ensure_ascii=False, indent=1)
        return 0 if ok else 1

    b, tank, cav = C["hall_block"], C["inner_tank"], cavity()
    print("跨模型契约（tools/contract.py）")
    print(f"  外壳外皮 {b['x0']:.1f}…{b['x1']:.1f} × {b['y0']:.1f}…{b['y1']:.1f}，"
          f"顶 {b['z_top']:.1f}（琉璃顶底 {b['z_glass_bottom']}）")
    print(f"  内腔     {cav['x0']:.1f}…{cav['x1']:.1f} × {cav['y0']:.1f}…{cav['y1']:.1f}"
          f"（壁厚 {C['shell']['t']}）")
    print(f"  内胆     {tank['x0']:.1f}…{tank['x1']:.1f} × {tank['y0']:.1f}…{tank['y1']:.1f}"
          f"，地坪 {tank['z_floor']}，穹顶 {tank['z_apex']}（下沉 {C['podium']['sink']}）")
    print(f"  门斗     宽 {2 * C['door_bay']['half_w']:.0f} × 出挑 {C['door_bay']['depth']} "
          f"× 高 {C['door_bay']['h']}\n")
    for name, c, detail in rows:
        print(f"[{'PASS' if c else 'FAIL':4s}] {name}" + (f"  — {detail}" if detail else ""))
    print("\n契约自检通过" if ok else "\n契约自检失败")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
