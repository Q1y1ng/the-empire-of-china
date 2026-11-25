"""套合出图：把「万人大礼堂·精模」（内胆）套进「国家广场·精模」的大会堂·中厅（外壳）。

【作者·2026-11-25 裁决】中厅保持 50 m 不抬高，**万人大礼堂下沉**：内胆地坪 z=0，比 2.3 m
台基面低 2.3 m；中厅体块挖空（壁厚 2 m、东面留 24 × 13.3 m 门洞）；前厅东墙改玻璃门斗。

本脚本只做三件事（几何修正已回写进两边的建模脚本，不再在这里改）：
  1. 打开广场模型的门扇（否则门洞被实心门扇挡死）；
  2. 补一组等效面积光（内胆 .glb 只有自发光材质，glTF 不带灯）；
  3. 出图：门斗人视 / 池座坐姿 / 轴向横剖；可选导出合并 glb。

用法：
  blender.exe -b --factory-startup -P try_merge.py -- [--spp 56] [--res 1500x844]
                                                   [--only 门斗|厅内|套合] [--glb]
"""
from __future__ import annotations

import json
import math
import os
import sys

import bpy
from mathutils import Vector

ASSETS = r"E:\AI\帝国\docs\assets"
PLAZA = ASSETS + r"\国家广场(2026)·精模.glb"
HALL = ASSETS + r"\国家广场(2026)·万人大礼堂·精模.glb"
AX = -1035.5

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


SPP = int(arg("--spp", 56))
RES = arg("--res", "1500x844")
ONLY = arg("--only", "")
OUT = os.path.join(os.environ.get("TEMP", "/tmp"), "hall_fit")
os.makedirs(OUT, exist_ok=True)
report = {}


# ---------------------------------------------------------------- 载入
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=PLAZA)
report["plaza_objects"] = len(bpy.data.objects)

before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=HALL)
inner = [o for o in bpy.data.objects if o not in before]
report["inner_objects"] = len(inner)

# ---------------------------------------------------------------- 打开广场模型的门扇
DOOR_PREFIX = ("大会堂·门廊·门", "大会堂·门廊·铺首")
doors = [x for x in bpy.data.objects if x.name.startswith(DOOR_PREFIX)]
for o in doors:
    bpy.data.objects.remove(o, do_unlink=True)
report["doors_removed"] = len(doors)

# ---------------------------------------------------------------- 灯光 / 世界
sun_d = bpy.data.lights.new("Sun", type="SUN")
sun_d.energy = 3.2
sun_d.angle = math.radians(3)
sun = bpy.data.objects.new("Sun", sun_d)
bpy.context.scene.collection.objects.link(sun)
sun.rotation_euler = (math.radians(42), 0, math.radians(128))

w = bpy.data.worlds.new("World")
bpy.context.scene.world = w
w.use_nodes = True
bg = w.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.42, 0.55, 0.72, 1.0)
bg.inputs[1].default_value = 0.62


def area(name, loc, rot, size, power, color=(1.0, 0.97, 0.92)):
    d = bpy.data.lights.new(name, "AREA")
    d.shape = "RECTANGLE"
    d.size, d.size_y = size
    d.energy = power
    d.color = color
    o = bpy.data.objects.new(name, d)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = rot
    return o


for i, x in enumerate((-478, -462, -446, -430, -414, -398)):
    area(f"顶光{i}", (x, AX, 28), (0, 0, 0), (18, 110), 2400)
area("台口面光", (-483.0, AX, 11), (0, -math.pi / 2, 0), (40, 18), 3400)
area("台面光", (-478.0, AX, 14), (math.radians(-35), 0, 0), (34, 14), 1800)
area("前厅光", (-350.0, AX, 21), (0, 0, 0), (70, 200), 2800)
area("门斗光", (-312.0, AX, 12), (0, -math.pi / 2, 0), (24, 10), 600)
report["lights"] = 10

# ---------------------------------------------------------------- 渲染设置
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
sc.cycles.samples = SPP
sc.cycles.max_bounces = 8
sc.cycles.use_denoising = True
rw, rh = (int(v) for v in RES.split("x"))
sc.render.resolution_x, sc.render.resolution_y = rw, rh
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = "PNG"
sc.view_settings.view_transform = "AgX"
for look in ("AgX - Medium High Contrast", "Medium High Contrast", "None"):
    try:
        sc.view_settings.look = look
        break
    except Exception:
        continue
sc.view_settings.exposure = 0.15

cam_d = bpy.data.cameras.new("Cam")
cam_d.clip_start = 0.5
cam_d.clip_end = 40000.0
cam = bpy.data.objects.new("Cam", cam_d)
sc.collection.objects.link(cam)
sc.camera = cam


def look_at(ob, target):
    ob.rotation_euler = (Vector(target) - ob.location).to_track_quat("-Z", "Y").to_euler()


# ---------------------------------------------------------------- 横剖
def section_at_axis():
    for o in [x for x in bpy.data.objects if x.name.startswith(("hall·", "council·", "museum·"))]:
        bpy.data.objects.remove(o, do_unlink=True)
    targets = [o for o in bpy.data.objects if o.type == "MESH"
               and (o.name.startswith("大会堂") or o in set(inner))]
    n = 0
    for ob in targets:
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        try:
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.mesh.bisect(plane_co=(0, AX, 0), plane_no=(0, 1, 0),
                                clear_inner=True, use_fill=False)
            bpy.ops.object.mode_set(mode="OBJECT")
            n += 1
        except Exception as e:
            print("BISECT_FAIL", ob.name, e, flush=True)
    print("SECTION", n, flush=True)
    ridge = bpy.data.objects.get("大会堂·中厅顶·正脊")
    if ridge:
        ridge.hide_render = True


# ---------------------------------------------------------------- 合并 glb（必须在横剖之前导出）
if "--glb" in argv or "--glb-only" in argv:
    glb = os.path.join(OUT, "国家广场·含万人大礼堂.glb")
    bpy.ops.export_scene.gltf(
        filepath=glb, export_format="GLB", export_apply=True,
        export_image_format="JPEG", export_image_quality=88,
        export_draco_mesh_compression_enable=True,
        export_draco_mesh_compression_level=6,
        export_draco_position_quantization=14,
        export_draco_normal_quantization=10,
        export_draco_texcoord_quantization=12)
    report["glb"] = glb
    report["glb_mb"] = round(os.path.getsize(glb) / 1e6, 2)
    print("GLB", glb, report["glb_mb"], "MB", flush=True)
if "--glb-only" in argv:
    print("MERGE_JSON " + json.dumps(report, ensure_ascii=False), flush=True)
    raise SystemExit(0)

SHOTS = {
    "正立面": dict(loc=(-140.0, AX, 14.0), target=(-311.5, AX, 15.0), lens=24,
                 section=False),
    "门斗": dict(loc=(-303.0, AX + 4.0, 4.8), target=(-320.0, AX + 2.0, 3.6), lens=24,
                 section=False),
    "厅内": dict(loc=(-459.0, AX, 2.5), target=(-500.0, AX + 2, 6.0), lens=26,
                 section=False),
    "套合": dict(loc=(-425.0, -1320.0, 95.0), target=(-425.0, -1040.0, 32.0), lens=32,
                 section=True),
}

for name, s in SHOTS.items():
    if ONLY and ONLY != name:
        continue
    if s["section"]:
        section_at_axis()
    cam.location = s["loc"]
    cam_d.lens = s["lens"]
    look_at(cam, s["target"])
    path = os.path.join(OUT, f"套合试验·{name}.png")
    sc.render.filepath = path
    print("RENDER", name, path, flush=True)
    bpy.ops.render.render(write_still=True)

print("MERGE_JSON " + json.dumps(report, ensure_ascii=False), flush=True)
