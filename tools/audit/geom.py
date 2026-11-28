"""几何自检（Blender 侧）：真实三角面相交、悬空、法线内翻、重合件。

补 `asserts.py` 查不到的那一半：断言查“关系与规格”，这里查“几何本身错了”。
两者不重叠——净空 1.99 m 几何上完全合法，两座台基互相埋进去则不合法。

⚠️ 口径（第一版踩过的坑，别再犯）：
  BVHTree.overlap() 报的是**包围盒相交的面**，不是三角面真相交。
  第一版拿它当“互穿”，`座席0 × 桌板0` 报了 39,958 对——其实是椅背嵌在座箱里的
  正常构造。所以这里对候选面再跑一遍**线段-三角形求交**，只报法律意义上的相交。

  * 互穿：BVH 粗筛 → 每个物体对抽样 ≤200 对面 → 逐边做 `intersect_ray_tri`。
    嵌合（一件插进另一件内部、表面不相交）不算，那是榫接。
  * 悬空：物体最低点必须被别的物体“托住”——别的物体 z 范围包含该点，或顶面在 2 cm 内。
    注意：整厅合并网格（座席0 是 40 万面的一个物体）在这一项上不准，看 group 说明。
  * 法线：只看**闭合**网格的有符号体积（开放网格体积无意义，单列出来不判）。
  * 重合：包围盒 1 cm 内相同 → 疑似重复件。

用法（由 check.py 调）：
    blender.exe -b xxx.blend -P geom.py -- --out geom.json
退出码：0 跑完（结果在 JSON）；2 参数问题。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

try:                      # MSYS bash 里控制台是 UTF-8，Python 默认 cp936 会输出乱码
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_ray_tri

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--max-pairs", type=int, default=30)
ap.add_argument("--sample", type=int, default=200,
                help="每个物体对最多抽多少对面做真实求交")
ap.add_argument("--allow", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                "geom_allow.json"),
                help="已判为构造性接触的物体对（白名单），之后只报新增")
args = ap.parse_args(argv)

TOL = 0.02          # 2 cm：托住判据 / 重合判据

MERGED_GROUPS = {"seat0", "seat1", "seat2", "floor", "dome"}   # 整厅合并网格，逐件判不准


def world_bbox(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return ([min(p[i] for p in pts) for i in range(3)],
            [max(p[i] for p in pts) for i in range(3)])


def bbox_hit(a, b):
    return all(a[0][i] - 0.01 <= b[1][i] and b[0][i] - 0.01 <= a[1][i] for i in range(3))


def tris_of(o):
    """世界坐标三角面（顶点 + 索引）。"""
    me = o.data
    me.calc_loop_triangles()
    mw = o.matrix_world
    verts = [mw @ v.co for v in me.vertices]
    return verts, [tuple(t.vertices) for t in me.loop_triangles]


def tri_hits(t1, t2):
    """两条三角形是否真的相交：A 的三条边去撞 B，再反向撞一次。

    共面贴合不算（那种情况边落在平面上，`intersect_ray_tri` 不给交点）。
    """
    for tri, other in ((t1, t2), (t2, t1)):
        a, b, c = tri
        for p, q in ((a, b), (b, c), (c, a)):
            d = q - p
            if d.length < 1e-9:
                continue
            hit = intersect_ray_tri(other[0], other[1], other[2], d, p, False)
            if hit is None:
                continue
            # 命中的点必须落在线段 pq 上
            if (hit - p).dot(d) <= d.length_squared + 1e-9:
                return True
    return False


def main():
    t0 = time.time()
    deps = bpy.context.evaluated_depsgraph_get()
    objs = [o for o in bpy.data.objects if o.type == "MESH" and not o.hide_viewport]
    boxes = {o.name: world_bbox(o) for o in objs}
    print(f"GEOM 物体 {len(objs)}", flush=True)

    # ---- 1 互穿（真实三角面相交）
    pairs = []
    trees = {o.name: BVHTree.FromObject(o, deps, epsilon=0.0) for o in objs}
    tris_cache = {}
    names = [o.name for o in objs]
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if not bbox_hit(boxes[a], boxes[b]):
                continue
            cand = trees[a].overlap(trees[b])
            if not cand:
                continue
            if a not in tris_cache:
                tris_cache[a] = tris_of(bpy.data.objects[a])
            if b not in tris_cache:
                tris_cache[b] = tris_of(bpy.data.objects[b])
            va, ta = tris_cache[a]
            vb, tb = tris_cache[b]
            real = 0
            for ia, ib in cand[:args.sample]:
                if tri_hits([va[k] for k in ta[ia]], [vb[k] for k in tb[ib]]):
                    real += 1
                    if real >= 3:        # 够判“相交”了，不用数完
                        break
            if real:
                pairs.append({"a": a, "b": b, "bbox_faces": len(cand), "real": real,
                              "merged": (bpy.data.objects[a].get("group") in MERGED_GROUPS
                                         or bpy.data.objects[b].get("group") in MERGED_GROUPS)})
    pairs.sort(key=lambda d: -d["bbox_faces"])
    allowed = set()
    if os.path.exists(args.allow):
        with open(args.allow, encoding="utf-8") as fh:
            for a, b in json.load(fh).get("allow", []):
                allowed.add(frozenset((a, b)))
    for p in pairs:
        p["known"] = frozenset((p["a"], p["b"])) in allowed
    fresh = [p for p in pairs if not p["known"]]
    print(f"GEOM 互穿 {len(pairs)} 对，其中已登记 {len(pairs) - len(fresh)}，"
          f"**未登记 {len(fresh)}**", flush=True)

    # ---- 2 悬空
    floating = []
    for o in objs:
        lo, hi = boxes[o.name]
        zmin = lo[2]
        supported = False
        for other in objs:
            if other is o:
                continue
            olo, ohi = boxes[other.name]
            if (olo[0] - 0.01 <= hi[0] and lo[0] - 0.01 <= ohi[0]
                    and olo[1] - 0.01 <= hi[1] and lo[1] - 0.01 <= ohi[1]):
                if olo[2] - TOL <= zmin <= ohi[2] + TOL:     # 埋进去了，算托住
                    supported = True
                    break
        if not supported:
            floating.append({"name": o.name, "z": round(zmin, 3),
                             "group": o.get("group") or "hall",
                             "merged": (o.get("group") or "") in MERGED_GROUPS})
    floating.sort(key=lambda d: d["z"])
    print(f"GEOM 悬空 {len(floating)}", flush=True)

    # ---- 3 法线 / 4 重合
    inverted, open_meshes, dup = [], [], []
    seen = {}
    for o in objs:
        me = o.data
        bm = bmesh.new()
        bm.from_mesh(me)
        try:
            vol = bm.calc_volume(signed=True)
        except Exception:
            vol = 0.0
        closed = all(e.is_manifold for e in bm.edges)
        bm.free()
        if not closed:
            open_meshes.append(o.name)
        elif vol < -1e-6:
            inverted.append({"name": o.name, "volume": round(vol, 3)})
        key = tuple(round(v / 0.01) for v in boxes[o.name][0] + boxes[o.name][1])
        if key in seen:
            dup.append({"a": seen[key], "b": o.name})
        seen.setdefault(key, o.name)
    print(f"GEOM 内翻 {len(inverted)} / 开放 {len(open_meshes)} / 重合 {len(dup)}",
          flush=True)

    doc = {
        "blend": bpy.data.filepath, "objects": len(objs),
        "overlap": fresh[:args.max_pairs], "overlap_total": len(fresh),
        "overlap_known": len(pairs) - len(fresh),
        "floating": floating, "inverted": inverted,
        "open_meshes": len(open_meshes), "duplicate_bbox": dup,
        "merged_groups": sorted(MERGED_GROUPS),
        "seconds": round(time.time() - t0, 1),
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    print("GEOM_DONE " + json.dumps({k: doc[k] for k in
                                     ("overlap_total", "objects", "seconds")},
                                    ensure_ascii=False), flush=True)
    return 0


raise SystemExit(main())
