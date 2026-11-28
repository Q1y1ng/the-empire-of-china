"""manifest 差分 → 受影响机位。纯 py3，不碰 Blender。

场景：改了一处几何，13 张图是不是都要重出？以前没有登记表，只能全重出。
现在每次构建落一份 manifest（{name, group, bbox, tris}），两份一 diff：
  * 变化的物体 → 变化的 group
  * 每个机位可见的 group = 全体 − 该机位的 hide 列表
  * 两者相交 → 这张图必须重出；不相交 → 跳过

用法：
    py -3 manifest.py --new "$TEMP/gm/manifest.json"                 # 只看这次有什么
    py -3 manifest.py --old prev.json --new cur.json                 # 差分 + 受影响机位
    py -3 manifest.py --old prev.json --new cur.json --fail-if-any   # 有变化就 exit 1

退出码：0 正常；1 有几何变化且给了 --fail-if-any；2 参数/文件问题。
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
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from shots_table import load_shots  # noqa: E402
import manifest_io  # noqa: E402

EPS = 0.002          # 2 mm：小于它的 bbox 变化是浮点噪音，不算改动
TRI_EPS = 0


def load(path):
    """→ (doc, {name: item})，解析口径统一在 manifest_io，两种 schema 都认。"""
    doc, items, totals = manifest_io.load(path)
    doc["_totals"] = totals
    return doc, {o["name"]: o for o in items}


def same(a, b):
    if a["tris"] != b["tris"] and abs(a["tris"] - b["tris"]) > TRI_EPS:
        return False
    for key in ("min", "max"):
        for x, y in zip(a[key], b[key]):
            if abs(x - y) > EPS:
                return False
    return True


def diff(old, new):
    added = [n for n in new if n not in old]
    removed = [n for n in old if n not in new]
    changed = [n for n in new if n in old and not same(old[n], new[n])]
    return added, removed, changed


SENSOR = 36.0        # Blender 默认传感器宽 36 mm，sensor_fit=AUTO 时作用在长边


def _norm(v):
    n = (v[0] ** 2 + v[1] ** 2 + v[2] ** 2) ** 0.5 or 1.0
    return (v[0] / n, v[1] / n, v[2] / n)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def in_view(spec, item, ar=16 / 9):
    """粗视锥判定：bbox 任一角点在相机视野内即算可见。

    比“分组可见”细一档——座席是整厅合并网格，只按分组判会把 16 个机位全标成
    受影响；按视锥判，只有真正拍到那片座席的机位才重出。
    忽略近远裁剪（相机 clip 0.5–20000，对这些机位不构成限制）。
    """
    loc, tgt = spec["loc"], spec["target"]
    fwd = _norm((tgt[0] - loc[0], tgt[1] - loc[1], tgt[2] - loc[2]))
    up_world = (0.0, 0.0, 1.0)
    right = _cross(fwd, up_world)
    if (right[0] ** 2 + right[1] ** 2 + right[2] ** 2) < 1e-9:     # 俯视/仰视
        right = (1.0, 0.0, 0.0)
    right = _norm(right)
    up = _norm(_cross(right, fwd))

    if spec.get("ortho"):
        half_w = spec["ortho"] / 2.0
        half_h = half_w / spec.get("ar", ar)
        for cx in (item["min"][0], item["max"][0]):
            for cy in (item["min"][1], item["max"][1]):
                for cz in (item["min"][2], item["max"][2]):
                    v = (cx - loc[0], cy - loc[1], cz - loc[2])
                    if _dot(v, fwd) <= 0:
                        continue
                    if abs(_dot(v, right)) <= half_w and abs(_dot(v, up)) <= half_h:
                        return True
        return False

    hfov = 2.0 * math.atan((SENSOR / 2.0) / max(spec.get("lens", 35), 1e-3))
    vfov = 2.0 * math.atan(((SENSOR / spec.get("ar", ar)) / 2.0)
                           / max(spec.get("lens", 35), 1e-3))
    th, tv = math.tan(hfov / 2.0), math.tan(vfov / 2.0)
    for cx in (item["min"][0], item["max"][0]):
        for cy in (item["min"][1], item["max"][1]):
            for cz in (item["min"][2], item["max"][2]):
                v = (cx - loc[0], cy - loc[1], cz - loc[2])
                z = _dot(v, fwd)
                if z <= 0.01:
                    continue
                if abs(_dot(v, right)) <= z * th and abs(_dot(v, up)) <= z * tv:
                    return True
    return False


def stations_for(groups, objects, frustum=True):
    """给定要重出的 group 集合，返回受影响机位名（按 SHOTS 顺序）。"""
    hits = []
    all_groups = {o.get("group") or "hall" for o in objects}
    for name, spec in load_shots():
        visible = all_groups - set(spec.get("hide", ()))
        if not (groups & visible):
            continue
        if not frustum:
            hits.append(name)
            continue
        if any(in_view(spec, o) for o in objects
               if (o.get("group") or "hall") in groups
               and (o.get("group") or "hall") in visible):
            hits.append(name)
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", default="")
    ap.add_argument("--new", required=True)
    ap.add_argument("--fail-if-any", action="store_true")
    ap.add_argument("--json", default="", help="把差分结果另存为 JSON")
    ap.add_argument("--top", type=int, default=8)
    args = ap.parse_args()

    for p in (args.old, args.new):
        if p and not os.path.exists(p):
            print(f"找不到 {p}", file=sys.stderr)
            return 2

    new_doc, new = load(args.new)
    meta = "，".join(x for x in (new_doc.get("blender"), new_doc.get("generated")) if x)
    print(f"新 manifest：{new_doc['_totals']['objects']} 物体 / "
          f"{new_doc['_totals']['tris']:,} 三角面" + (f"（{meta}）" if meta else ""))

    result = {"new_totals": new_doc["_totals"], "added": [], "removed": [],
              "changed": [], "groups": {}, "stations": []}

    if not args.old:
        groups = {}
        for o in new.values():
            groups[o["group"]] = groups.get(o["group"], 0) + 1
        print("分组：" + "，".join(f"{k}×{v}" for k, v in
                                 sorted(groups.items(), key=lambda kv: -kv[1])))
        if args.json:
            with open(args.json, "w", encoding="utf-8") as fh:
                json.dump(groups, fh, ensure_ascii=False, indent=1)
        return 0

    old_doc, old = load(args.old)
    added, removed, changed = diff(old, new)
    d_obj = new_doc["_totals"]["objects"] - old_doc["_totals"]["objects"]
    d_tri = new_doc["_totals"]["tris"] - old_doc["_totals"]["tris"]
    print(f"对比旧 manifest：+{len(added)} 新增 / -{len(removed)} 删除 / "
          f"~{len(changed)} 改动；共 {d_obj:+d} 物体、{d_tri:+,} 三角面")

    groups = {}
    for name in added + changed:
        g = new[name].get("group") or "hall"
        groups[g] = groups.get(g, 0) + 1
    for name in removed:
        g = old[name].get("group") or "hall"
        groups[g] = groups.get(g, 0) + 1

    for name in (added + changed)[:args.top]:
        print(f"  改  {name:28s} group={new[name]['group']:12s} "
              f"tris={new[name]['tris']:,}")

    if groups:
        print("受影响分组：" + "，".join(f"{k}×{v}" for k, v in
                                   sorted(groups.items(), key=lambda kv: -kv[1])))
        shots = stations_for(set(groups), list(new.values()))
        print(f"需要重出的机位（{len(shots)}/{len(load_shots())}）："
              + ("，".join(shots) if shots else "无"))
    else:
        shots = []
        print("没有几何变化——13 张图一张都不用重出。")

    result.update(added=added, removed=removed, changed=changed,
                  groups=groups, stations=shots)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=1)
        print(f"差分已存 {args.json}")

    if args.fail_if_any and (added or removed or changed):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
