"""验收合并 glb：单独导入（不依赖两个源文件），查物体/三角面/材质/贴图，并出池座一张图。"""
from __future__ import annotations

import json
import math
import os
import sys

import bpy
from mathutils import Vector

GLB = os.path.join(os.environ["TEMP"], "hall_fit", "国家广场·含万人大礼堂.glb")
OUT = os.path.join(os.environ["TEMP"], "hall_fit")
AX = -1035.5

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)

meshes = [o for o in bpy.data.objects if o.type == "MESH"]
tris = 0
for o in meshes:
    o.data.calc_loop_triangles()
    tris += len(o.data.loop_triangles)
lo = Vector((1e9,) * 3)
hi = Vector((-1e9,) * 3)
for o in meshes:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        for i in range(3):
            lo[i] = min(lo[i], w[i])
            hi[i] = max(hi[i], w[i])

info = {
    "objects": len(meshes),
    "tris": tris,
    "materials": len({m.name for o in meshes for m in o.data.materials if m}),
    "images": len(bpy.data.images),
    "bbox": [[round(v, 2) for v in lo], [round(v, 2) for v in hi]],
    "has_hall": any(o.name.startswith("座席") for o in meshes),
    "has_plaza": any(o.name.startswith("大会堂·中厅（万人大礼堂）") for o in meshes),
}
print("VERIFY " + json.dumps(info, ensure_ascii=False), flush=True)

# ---- 灯光 / 相机（与 try_merge 同口径）
sc = bpy.context.scene
sc.render.engine = "CYCLES"
pre = bpy.context.preferences.addons["cycles"].preferences
for backend in ("OPTIX", "CUDA"):
    try:
        pre.compute_device_type = backend
        pre.get_devices()
        if any(d.type == backend for d in pre.devices):
            for d in pre.devices:
                d.use = d.type == backend
            sc.cycles.device = "GPU"
            sc.cycles.denoiser = "OPTIX" if backend == "OPTIX" else "OPENIMAGEDENOISE"
            break
    except Exception as e:
        print("DEVICE", backend, e, flush=True)

sun_d = bpy.data.lights.new("Sun", type="SUN")
sun_d.energy = 3.2
sun_d.angle = math.radians(3)
sun = bpy.data.objects.new("Sun", sun_d)
sc.collection.objects.link(sun)
sun.rotation_euler = (math.radians(42), 0, math.radians(128))
w = bpy.data.worlds.new("World")
sc.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.42, 0.55, 0.72, 1.0)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.62


def area(loc, rot, size, power):
    d = bpy.data.lights.new("A", "AREA")
    d.shape = "RECTANGLE"
    d.size, d.size_y = size
    d.energy = power
    o = bpy.data.objects.new("A", d)
    sc.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = rot


for x in (-478, -462, -446, -430, -414, -398):
    area((x, AX, 28), (0, 0, 0), (18, 110), 2400)
area((-483.0, AX, 11), (0, -math.pi / 2, 0), (40, 18), 3400)
area((-478.0, AX, 14), (math.radians(-35), 0, 0), (34, 14), 1800)
area((-350.0, AX, 21), (0, 0, 0), (70, 200), 2800)

sc.cycles.samples = 40
sc.cycles.max_bounces = 8
sc.render.resolution_x, sc.render.resolution_y = 1200, 675
sc.render.image_settings.file_format = "PNG"
sc.view_settings.view_transform = "AgX"
try:
    sc.view_settings.look = "AgX - Medium High Contrast"
except Exception:
    pass
sc.view_settings.exposure = 0.15

cam_d = bpy.data.cameras.new("Cam")
cam_d.clip_start = 0.5
cam_d.clip_end = 40000.0
cam_d.lens = 26
cam = bpy.data.objects.new("Cam", cam_d)
sc.collection.objects.link(cam)
sc.camera = cam
cam.location = (-459.0, AX, 2.5)
cam.rotation_euler = (Vector((-500.0, AX + 2, 6.0)) - cam.location).to_track_quat("-Z", "Y").to_euler()

sc.render.filepath = os.path.join(OUT, "验收·合并glb·池座.png")
bpy.ops.render.render(write_still=True)
print("DONE", sc.render.filepath, flush=True)
