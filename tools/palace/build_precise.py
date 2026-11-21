"""金瓯殿 · 单殿精模展示 —— 直接调用 precise_lib 的构件库

用法：
    blender -b --factory-startup -P build_precise.py -- --out OUT [--samples 128] [--res 1920]

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

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default=os.path.join(HERE, "..", "..", "docs", "assets"))
ap.add_argument("--samples", type=int, default=128)
ap.add_argument("--res", type=int, default=1920)
ap.add_argument("--only", default="")
args = ap.parse_args(argv)
WORK = os.path.join(os.environ.get("TEMP", HERE), "palace_precise")
os.makedirs(WORK, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.unit_settings.system = "METRIC"
col = sc.collection
PL.set_collection(col)
PL.make_materials()

BAYS = [7.0, 7.5, 8.0, 8.5, 9.0, 10.0, 9.0, 8.5, 8.0, 7.5, 7.0]
DBAYS = [8.0, 9.5, 15.0, 9.5, 8.0]
W, D = sum(BAYS), sum(DBAYS)

PL.hall("金瓯殿", W, D, bays=BAYS, dbays=DBAYS, z=0.0, storeys=2,
        base_h=3.2, col_h=12.0, plaque="金瓯殿", lod=2)

# 广场地面
PL.box("广场", 400, 400, 0.4, 0, 0, -0.4, PL.MAT["stone2"])

cam_data = bpy.data.cameras.new("Cam")
cam_data.clip_start = 0.5
cam_data.clip_end = 6000
cam = bpy.data.objects.new("Cam", cam_data)
col.objects.link(cam)
sc.camera = cam


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


sun_d = bpy.data.lights.new("Sun", type="SUN")
sun_d.energy = 3.0
sun_d.angle = math.radians(3)
sun = bpy.data.objects.new("Sun", sun_d)
col.objects.link(sun)
sun.rotation_euler = (math.radians(36), 0, math.radians(228))

sc.world = bpy.data.worlds.new("World")
sc.world.use_nodes = True
bg = sc.world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.58, 0.70, 0.88, 1.0)
bg.inputs[1].default_value = 0.35

sc.render.engine = "CYCLES"
sc.cycles.device = "GPU"
sc.cycles.samples = args.samples
sc.cycles.use_denoising = True
sc.cycles.max_bounces = 6
sc.render.image_settings.file_format = "PNG"
sc.view_settings.view_transform = "Standard"
sc.view_settings.exposure = -0.2

shots = [
    ("正立面", dict(loc=(0, -230, 16), target=(0, 0, 18), lens=55)),
    ("鸟瞰", dict(loc=(120, -160, 82), target=(0, 0, 16), lens=45)),
    ("檐下", dict(loc=(18, -52, 9), target=(14, -26, 16.5), lens=55)),
    ("屋顶", dict(loc=(64, -70, 52), target=(8, 0, 32), lens=70)),
]
res = {}
for name, s in shots:
    if args.only and args.only not in name:
        continue
    cam.location = s["loc"]
    cam_data.type = "PERSP"
    cam_data.lens = s["lens"]
    look_at(cam, s["target"])
    sc.render.resolution_x = args.res
    sc.render.resolution_y = int(args.res * 9 / 16)
    path = os.path.join(WORK, f"jinol_{name}.png")
    sc.render.filepath = path
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    res[name] = {"s": round(time.time() - t0, 1), "bytes": os.path.getsize(path)}
    print("RENDER", name, res[name])

blend = os.path.join(WORK, "jinol_hall.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend)
glb = os.path.join(WORK, "jinol_hall.glb")
bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", export_apply=True)

tri = 0
for o in col.objects:
    if o.type == "MESH":
        o.data.calc_loop_triangles()
        tri += len(o.data.loop_triangles)
print("RESULT " + json.dumps({"renders": res, "objects": len(col.objects), "triangles": tri,
                              "blend": blend, "glb": glb,
                              "glb_mb": round(os.path.getsize(glb) / 1e6, 2)},
                             ensure_ascii=False))
