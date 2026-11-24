"""量测：把「万人大礼堂·精模」塞进「国家广场·精模」的 大会堂·中厅 体块，核定间隙与冲突。

用法（Blender 无头）：
  blender.exe -b --factory-startup -P probe_fit.py -- [--save-merge path.blend]
只读两个 .glb，不改任何产物；结论打印成 JSON。
"""
from __future__ import annotations

import json
import sys

import bpy
from mathutils import Vector

ASSETS = r"E:\AI\帝国\docs\assets"
PLAZA = ASSETS + r"\国家广场(2026)·精模.glb"
HALL = ASSETS + r"\国家广场(2026)·万人大礼堂·精模.glb"

# hall-c 体块（plaza_data.MASSES）
BOX = {"x0": -540.0, "x1": -310.0, "y0": -1155.5, "y1": -915.5,
       "z0": 2.3, "z1": 50.0}          # z0 = 台基面，z1 = 身子顶（檐口 47.8–50.0）
PLINTH_TOP = 2.3


def bbox(objs):
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    n = 0
    for o in objs:
        if o.type != "MESH":
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
            n += 1
    return [round(v, 3) for v in lo], [round(v, 3) for v in hi], n


def stats(objs):
    objs = [o for o in objs if o.type == "MESH"]
    tris = 0
    verts = 0
    for o in objs:
        me = o.data
        me.calc_loop_triangles()
        tris += len(me.loop_triangles)
        verts += len(me.vertices)
    mats = sorted({m.name for o in objs for m in o.data.materials if m})
    return {"objects": len(objs), "verts": verts, "tris": tris,
            "materials": len(mats), "material_names": mats}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    save = None
    if "--save-merge" in argv:
        save = argv[argv.index("--save-merge") + 1]

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=PLAZA)
    plaza = list(bpy.data.objects)

    hall_c = [o for o in plaza if o.type == "MESH" and o.name.startswith("大会堂·中厅")]
    hall_all = [o for o in plaza if o.type == "MESH" and o.name.startswith("大会堂")]
    plinth = [o for o in plaza if o.type == "MESH" and o.name.startswith("大会堂·台基")]

    out = {"plaza_file": PLAZA, "hall_file": HALL}
    out["plaza_total"] = stats(plaza)
    for tag, objs in (("hall_c", hall_c), ("hall_all", hall_all), ("plinth", plinth)):
        lo, hi, _ = bbox(objs)
        out[tag] = {"bbox": [lo, hi], "stats": stats(objs),
                    "object_names": sorted(o.name for o in objs)[:40]}
    print("PROBE plaza done", len(plaza), flush=True)

    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=HALL)
    inner = [o for o in bpy.data.objects if o not in before]

    lo, hi, _ = bbox(inner)
    out["interior"] = {"bbox": [lo, hi], "stats": stats(inner)}
    out["interior_top_names"] = sorted(o.name for o in inner if o.type == "MESH")[:80]

    # 每个 mesh 的包围盒，找越界者
    over = []
    for o in inner:
        if o.type != "MESH":
            continue
        blo, bhi, _ = bbox([o])
        flags = []
        if blo[0] < BOX["x0"] - 1e-3:
            flags.append("x<西面")
        if bhi[0] > BOX["x1"] + 1e-3:
            flags.append("x>东面")
        if blo[1] < BOX["y0"] - 1e-3:
            flags.append("y<南面")
        if bhi[1] > BOX["y1"] + 1e-3:
            flags.append("y>北面")
        if blo[2] < PLINTH_TOP - 1e-3:
            flags.append("z<台基面")
        if bhi[2] > BOX["z1"] + 1e-3:
            flags.append("z>体块顶")
        if flags:
            over.append({"name": o.name, "bbox": [blo, bhi], "flags": flags})

    out["out_of_box"] = {
        "count": len(over),
        "items": sorted(over, key=lambda d: -d["bbox"][1][2])[:40],
    }

    # 关键净空
    clear = {
        "west": round(lo[0] - BOX["x0"], 3),
        "east": round(BOX["x1"] - hi[0], 3),
        "south": round(lo[1] - BOX["y0"], 3),
        "north": round(BOX["y1"] - hi[1], 3),
        "bottom_vs_plinth": round(lo[2] - PLINTH_TOP, 3),
        "top_clearance": round(BOX["z1"] - hi[2], 3),
    }
    out["clearance"] = clear

    # 场景总计
    out["merged_total"] = stats([o for o in bpy.data.objects])
    out["images"] = len(bpy.data.images)

    print("PROBE_JSON " + json.dumps(out, ensure_ascii=False), flush=True)

    if save:
        bpy.ops.wm.save_as_mainfile(filepath=save)
        print("SAVED", save, flush=True)


main()
