"""金瓯殿 · 单殿精模展示 —— 调用 lg_roof / lg_dougong / lg_facade / lg_look

用法：
    blender -b --factory-startup -P build_precise.py -- --out OUT [--samples 128]
            [--res 1920] [--only 屋顶] [--hdri sunny|overcast|none] [--shots all|名字]

尺寸与整宫一致：面阔 11 间 90 m、进深 5 间 50 m，重檐，匾额「金瓯殿」。
"""

import argparse
import json
import math
import os
import sys
import time

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import precise_lib as PL  # noqa: E402
import lg_look as LK  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default=os.path.join(HERE, "..", "..", "docs", "assets"))
ap.add_argument("--samples", type=int, default=128)
ap.add_argument("--res", type=int, default=1920)
ap.add_argument("--only", default="")
ap.add_argument("--hdri", default="sunny")
ap.add_argument("--sun-energy", type=float, default=0.0)
ap.add_argument("--exposure", type=float, default=0.0)
args = ap.parse_args(argv)
WORK = os.path.join(os.environ.get("TEMP", HERE), "palace_precise")
os.makedirs(WORK, exist_ok=True)
os.makedirs(args.out, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.unit_settings.system = "METRIC"
col = sc.collection
PL.set_collection(col)
PL.MAT.update(LK.make_materials())

BAYS = [7.0, 7.5, 8.0, 8.5, 9.0, 10.0, 9.0, 8.5, 8.0, 7.5, 7.0]
DBAYS = [8.0, 9.5, 15.0, 9.5, 8.0]
W, D = sum(BAYS), sum(DBAYS)

t_build = time.time()
PL.hall("金瓯殿", W, D, bays=BAYS, dbays=DBAYS, z=0.0, storeys=2,
        base_h=3.2, col_h=12.0, plaque="金瓯殿", lod=2)
build_s = time.time() - t_build

# 广场：汉白玉铺地 + 一圈台明
PL.box("广场", 700, 700, 0.5, 0, 0, -0.5, PL.MAT["brick"])

# ---------------------------------------------------------------- 环境光
hdri = {"sunny": "hdri_sky_sunny_2k.hdr",
        "overcast": "hdri_sky_overcast_2k.hdr",
        "none": None}[args.hdri]
review = LK.review_settings()
# 与整宫同一套光比（太阳 2.6 : 环境 1.3），否则单殿图比整宫图"烈"一档
w_strength = 1.30 if hdri else 1.0
sun_e = args.sun_energy or 2.60
info = LK.setup_world(sc, hdri, strength=w_strength,
                      az=228, elev=36, fallback_sky=True)
sun = LK.setup_sun(sc, energy=sun_e, az=228, elev=36)
sun_info = sun[1] if isinstance(sun, (tuple, list)) and len(sun) > 1 else str(sun)
exp = args.exposure if args.exposure else -0.50
LK.setup_render(sc, res=args.res, samples=args.samples, exposure=exp)

cam_data = bpy.data.cameras.new("Cam")
cam_data.clip_start = 0.5
cam_data.clip_end = 6000
cam = bpy.data.objects.new("Cam", cam_data)
col.objects.link(cam)
sc.camera = cam


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


# 机位：名字 → (位置, 目标, 焦距, 光圈)
SHOTS = [
    ("正立面", (0, -262, 21), (0, 0, 22), 70, 0.0),
    ("鸟瞰", (172, -212, 132), (0, 0, 22), 55, 0.0),
    ("檐下", (36, -58, 15), (16, -26, 21), 50, 2.8),
    ("屋顶", (82, -92, 70), (4, 0, 34), 60, 0.0),
    ("人视", (0, -82, 1.72), (0, 0, 15), 35, 4.0),
    # 仰视：专为看斗拱的逐跳出跳与昂嘴纵深（正对墙面时进深被透视压扁，看不出来）
    ("仰视", (26, -56, 2.2), (46, -18, 18.4), 60, 0.0),
]

res = {}
for name, loc, target, lens, fstop in SHOTS:
    if args.only and args.only not in name:
        continue
    cam.location = loc
    cam_data.type = "PERSP"
    cam_data.lens = lens
    cam_data.dof.use_dof = bool(fstop)
    if fstop:
        cam_data.dof.focus_distance = (Vector(target) - Vector(loc)).length
        cam_data.dof.aperture_fstop = fstop
    look_at(cam, target)
    path = os.path.join(WORK, f"jinol_{name}.png")
    sc.render.filepath = path
    t0 = time.time()
    ok = LK.render(sc, path)
    res[name] = {"s": round(time.time() - t0, 1), "bytes": os.path.getsize(path),
                 "ok": bool(ok)}
    print("RENDER", name, res[name], flush=True)

import shutil
if args.out and os.path.abspath(args.out) != os.path.abspath(WORK):
    for name, loc, target, lens, fstop in SHOTS:
        if name in res:
            src = os.path.join(WORK, f"jinol_{name}.png")
            dst = os.path.join(args.out, f"皇宫宫城(2026)·精模·单殿·{name}.png")
            try:
                shutil.copyfile(src, dst)
            except Exception as exc:
                print("COPY_FAIL", name, exc)

blend = os.path.join(WORK, "jinol_hall.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend)
glb = os.path.join(WORK, "jinol_hall.glb")
bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", export_apply=True)

tri = 0
for o in col.objects:
    if o.type == "MESH":
        o.data.calc_loop_triangles()
        tri += len(o.data.loop_triangles)
print("RESULT " + json.dumps({"renders": res, "objects": len(col.objects),
                              "triangles": tri, "build_s": round(build_s, 1),
                              "world": info, "sun": sun_info, "exposure": exp,
                              "blend": blend, "glb": glb,
                              "glb_mb": round(os.path.getsize(glb) / 1e6, 2)},
                             ensure_ascii=False))
