# -*- coding: utf-8 -*-
"""单张高精度成图：主席台看观众席，广角。

用法（在 build_hall.py 跑过一次、Temp 里有 .blend 之后）：
  blender -b --factory-startup -P render_hero.py -- [--lens 14] [--res 5120] [--samples 320]
"""
import os
import sys

import bpy
from mathutils import Vector

BLEND = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp", "grandhall",
                     "grandhall_precise.blend")
OUTDIR = r"E:\桌面"
AX = -1035.5                      # 中轴 y（图纸坐标）

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    if name in argv:
        return type(default)(argv[argv.index(name) + 1])
    return default


lens = arg("--lens", 14.0)
res = arg("--res", 5120)
samples = arg("--samples", 320)

if not os.path.exists(BLEND):
    sys.exit("missing blend: " + BLEND)
bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.context.scene

# --- Cycles GPU（--factory-startup 会把设备偏好重置成 NONE，必须显式选）
pre = bpy.context.preferences.addons["cycles"].preferences
for backend in ("OPTIX", "CUDA"):
    try:
        pre.compute_device_type = backend
        pre.get_devices()
        if not any(d.type == backend for d in pre.devices):
            continue
        for d in pre.devices:
            d.use = (d.type == backend)
        sc.cycles.device = "GPU"
        sc.cycles.denoiser = "OPTIX" if backend == "OPTIX" else "OPENIMAGEDENOISE"
        print("DEVICE", backend, flush=True)
        break
    except Exception as exc:                      # noqa: BLE001
        print("DEVICE", backend, exc, flush=True)

# --- 机位：主席台面 1.50 + 眼高 1.65，广角望向观众席
cam = bpy.data.objects.get("Cam") or sc.camera
if cam is None:
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    sc.collection.objects.link(cam)
sc.camera = cam
cam.data.type = "PERSP"
cam.data.lens = lens
cam.data.sensor_width = 36.0
cam.data.sensor_fit = "HORIZONTAL"
cam.data.clip_start = 0.3
cam.data.clip_end = 20000.0
cam.location = (arg("--x", -509.0), AX, arg("--z", 3.25))
look = Vector((arg("--tx", -452.0), AX, arg("--tz", 6.5)) ) - cam.location
cam.rotation_euler = look.to_track_quat("-Z", "Y").to_euler()

# --- 渲染参数：与 build_hall.py 精模同一套调色，只把精度拉满
sc.render.engine = "CYCLES"
sc.cycles.samples = samples
sc.cycles.use_denoising = True
sc.cycles.max_bounces = 8
sc.cycles.transparent_max_bounces = 4
sc.render.resolution_x = res
sc.render.resolution_y = int(round(res * 9 / 16))
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGB"
sc.render.image_settings.color_depth = "8"
sc.render.image_settings.compression = 15
sc.view_settings.view_transform = "AgX"
sc.view_settings.look = "AgX - Medium High Contrast"
sc.view_settings.exposure = 0.25

name = "万人大礼堂·主席台望观众席·%d×%d·%dspp.png" % (
    sc.render.resolution_x, sc.render.resolution_y, samples)
if "--hide" in argv:
    pats = [p for p in argv[argv.index("--hide") + 1].split(",") if p]
    for o in bpy.data.objects:
        if any(p in o.name for p in pats):
            o.hide_render = True
            print("HIDE", o.name, flush=True)
os.makedirs(OUTDIR, exist_ok=True)
sc.render.filepath = os.path.join(OUTDIR, name)
bpy.ops.render.render(write_still=True)
print("HERO_DONE", sc.render.filepath, flush=True)
