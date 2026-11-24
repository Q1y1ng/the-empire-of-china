"""可行性试验：把「万人大礼堂·精模」（内胆）套进「国家广场·精模」的大会堂·中厅（外壳）。

只读两个 .glb，产物写 %TEMP%/hall_fit，不改仓库里任何交付件。
本脚本同时验证 7 条修正假设（见 README 的可行性小结）：

  1. 内胆整体 +2.3 m —— 广场模型的大会堂落在 2.3 m 台基上，内胆地坪原在 z=0；
  2. 内胆前厅东墙（x=−310，与中厅体块东面共面）西移 1.2 m，消除共面闪面；
  3. 中厅体块东面按门廊挖 24 × 14 m 门洞（广场模型的入口门位置）；
  4. 舞台顶板西侧超出体块 3 m（x=−543），夹到 −540；
  5. 铜门与把手随东墙内移；
  6. 中厅体块做半透明，用于看内胆与外壳的套合关系；
  7. 内胆 .glb 不含灯光（glTF 只带自发光材质），补一组面积光。

用法：
  blender.exe -b --factory-startup -P try_merge.py -- [--spp 64] [--res 1600x900]
                                                  [--only 套合|入口|厅内]
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

BOX = {"x0": -540.0, "x1": -310.0, "y0": -1155.5, "y1": -915.5}
AX = -1035.5
LIFT = 2.3          # 台基面
PORTAL = {"w": 24.0, "z0": 1.9, "z1": 15.6}      # 广场模型入口门 24 × 14 m，不随内胆抬升
FOYER_INSET = 1.2

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(name, default):
    return argv[argv.index(name) + 1] if name in argv else default

SPP = int(arg("--spp", 48))
RES = arg("--res", "1600x900")
ONLY = arg("--only", "")
OUT = os.path.join(os.environ.get("TEMP", "/tmp"), "hall_fit")
os.makedirs(OUT, exist_ok=True)
report = {}


# ---------------------------------------------------------------- 载入
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=PLAZA)
n_plaza = len(bpy.data.objects)
report["plaza_objects"] = n_plaza

before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=HALL)
inner = [o for o in bpy.data.objects if o not in before]
report["inner_objects"] = len(inner)

body = bpy.data.objects.get("大会堂·中厅（万人大礼堂）")
assert body is not None, "找不到中厅体块"

# ---------------------------------------------------------------- 1 整体抬升
moved = 0
for o in inner:
    o.location.z += LIFT
    moved += 1
report["lift"] = {"dz": LIFT, "objects": moved}

# ---------------------------------------------------------------- 2/5 前厅东墙与铜门内移
def shift_verts(obnames, pred, delta):
    hits = 0
    for nm in obnames:
        ob = bpy.data.objects.get(nm)
        if not ob or ob.type != "MESH":
            continue
        n = 0
        for v in ob.data.vertices:
            if pred(v.co):
                v.co += Vector(delta)
                n += 1
        ob.data.update()
        hits += n
    return hits

n_wall = shift_verts(["前厅·墙"], lambda c: c.x > -310.01, (-FOYER_INSET, 0, 0))
n_door = shift_verts(["铜门", "铜门把手"], lambda c: c.x > -310.35, (-FOYER_INSET, 0, 0))
report["foyer_inset"] = {"dz_x": -FOYER_INSET, "wall_verts": n_wall, "door_verts": n_door}

# 开门：删掉中间那樘铜门（含门套），否则门厅被实心门扇挡死
import bmesh  # noqa: E402

def open_door(obname):
    ob = bpy.data.objects.get(obname)
    if not ob:
        return 0
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    dead = [f for f in bm.faces
            if (c := f.calc_center_median()).x > -312.6 and abs(c.y - AX) < 3.6 and c.z < 11.0]
    bmesh.ops.delete(bm, geom=dead, context="FACES")
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return len(dead)

report["opened_faces"] = open_door("铜门") + open_door("铜门把手")

# ---------------------------------------------------------------- 4 舞台顶板夹到 −540
n_roof = shift_verts(["舞台顶板"], lambda c: c.x < -540.0 + 1e-6, (0, 0, 0))
for v in bpy.data.objects["舞台顶板"].data.vertices:
    if v.co.x < -540.0:
        v.co.x = -540.0
bpy.data.objects["舞台顶板"].data.update()
report["stage_roof_trim"] = {"prev_min_x": -543.0, "now_min_x": -540.0}

# ---------------------------------------------------------------- 3 门洞
def add_cube(name, center, size):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return ob

cut = add_cube("挖洞", (-311.0, AX, (PORTAL["z0"] + PORTAL["z1"]) / 2),
               (2.6, PORTAL["w"], PORTAL["z1"] - PORTAL["z0"]))
mod = body.modifiers.new("portal", "BOOLEAN")
mod.operation = "DIFFERENCE"
mod.object = cut
mod.solver = "EXACT"
bpy.context.view_layer.objects.active = body
body.select_set(True)
bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.data.objects.remove(cut, do_unlink=True)
report["portal"] = {"w": PORTAL["w"], "z": [PORTAL["z0"], PORTAL["z1"]]}

# ---------------------------------------------------------------- 门扇打开（否则挖洞被广场模型的实心门扇挡死）
DOOR_PREFIX = "大会堂·门廊·门"
_doors = [x for x in bpy.data.objects if x.name.startswith(DOOR_PREFIX)]
for o in _doors:
    bpy.data.objects.remove(o, do_unlink=True)
report["doors_removed"] = len(_doors)
report["doors_left"] = sum(1 for x in bpy.data.objects if x.name.startswith(DOOR_PREFIX))

sun_d = bpy.data.lights.new("Sun", type="SUN")
sun_d.energy = 3.2
sun_d.angle = math.radians(3)
sun = bpy.data.objects.new("Sun", sun_d)
bpy.context.scene.collection.objects.link(sun)
# 广场模型原为 (35°, 0, 232°)——东立面在阴影里；试验把太阳挪到东南，正面受光
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


# 内胆 .glb 只有自发光，没有灯：补一组等效面积光
for i, x in enumerate((-478, -462, -446, -430, -414, -398)):
    area(f"顶光{i}", (x, AX, 28 + LIFT), (0, 0, 0), (18, 110), 2400)
area("台口面光", (-483.0, AX, 11 + LIFT), (0, -math.pi / 2, 0), (40, 18), 3400)
area("台面光", (-478.0, AX, 14 + LIFT), (math.radians(-35), 0, 0), (34, 14), 1800)
area("前厅光", (-350.0, AX, 21 + LIFT), (0, 0, 0), (70, 200), 2800)
report["lights"] = 9

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
sc.render.film_transparent = False
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


# ---------------------------------------------------------------- 半透明（套合镜头用）
GHOST_PREFIX = ["大会堂·中厅顶", "大会堂·中厅（万人大礼堂）", "前厅·顶"]
_ghosted = set()


def make_ghost(ob):
    if ob.name in _ghosted:
        return
    for i, m in enumerate(ob.data.materials):
        if m is None:
            continue
        # 不复用原材质节点树：glTF 的节点接法各异，直接新建一个纯 Principled 幽灵材质
        nm = bpy.data.materials.new(m.name + "·透")
        nm.use_nodes = True
        bsdf = nm.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = (0.62, 0.66, 0.72, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.55
        bsdf.inputs["Alpha"].default_value = 0.0
        try:
            nm.surface_render_method = "BLENDED"
        except Exception:
            pass
        ob.data.materials[i] = nm
    _ghosted.add(ob.name)
    print("GHOSTED", ob.name, len(ob.data.materials), flush=True)


def ghost_shell():
    """（备用）外壳半透明——已改用法：套合镜头改用横剖，见 section_at_axis。"""
    hits = 0
    for ob in list(bpy.data.objects):
        if ob.type != "MESH":
            continue
        if any(ob.name.startswith(p) for p in GHOST_PREFIX):
            make_ghost(ob)
            hits += 1
    print("GHOST_TOTAL", hits, flush=True)


def section_at_axis():
    """沿 y = AX 横剖，保留北半（y > AX），机位放在南侧看剖面。"""
    # 院落草地用的是 plaza_data 的 key 名（hall/），没被下列前缀命中，先删掉
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
    # 屋脊金线会斜穿剖面，遮掉
    ridge = bpy.data.objects.get("大会堂·中厅顶·正脊")
    if ridge:
        ridge.hide_render = True

# ---------------------------------------------------------------- 机位
SHOTS = {
    "厅内": dict(loc=(-459.0, AX, 2.5 + LIFT), target=(-500.0, AX + 2, 6.0 + LIFT),
                 lens=26, section=False),
    # 横剖会把场景切掉一半，必须放最后
    "套合": dict(loc=(-425.0, -1320.0, 95.0), target=(-425.0, -1040.0, 32.0), lens=32,
                 section=True),
}

for name, s in SHOTS.items():
    if ONLY and ONLY != name:
        continue
    if s.get("section"):
        section_at_axis()
    cam.location = s["loc"]
    cam_d.lens = s["lens"]
    look_at(cam, s["target"])
    path = os.path.join(OUT, f"套合试验·{name}.png")
    sc.render.filepath = path
    print("RENDER", name, path, flush=True)
    bpy.ops.render.render(write_still=True)

print("MERGE_JSON " + json.dumps(report, ensure_ascii=False), flush=True)
