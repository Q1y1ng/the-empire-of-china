"""宫城（皇宫）3D 体量白模 —— Blender 5.x 无头脚本，数据全部取自 palace_data.py。

用法：
    blender -b --factory-startup -P build_massing.py -- --out <输出目录> [--samples 128]

产物：
    palace_massing.blend     可直接在 GUI 里转着看
    palace_massing.glb       glTF（留给后续网页漫游）
    *.png                    鸟瞰 / 人视 / 正射总平面
口径：架空混合 —— 明官式为骨（庑殿顶、台基、城台门楼、角楼），
      殿身面阔进深为按设定占地反推的推定值，现代附楼为架空改造。
"""

import argparse
import json
import math
import os
import sys
import time

import bmesh
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import palace_data as D  # noqa: E402

# ------------------------------------------------------------------ 参数
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default=os.path.join(HERE, "..", "..", "docs", "assets"))
ap.add_argument("--samples", type=int, default=128)
ap.add_argument("--res", type=int, default=1600)
args = ap.parse_args(argv)
WORK = os.path.join(os.environ.get("TEMP", HERE), "palace_massing")
os.makedirs(WORK, exist_ok=True)
os.makedirs(args.out, exist_ok=True)

P = D.PALACE
HW, HD = P["width"] / 2, P["depth"] / 2
T, H = P["wall_t"], P["wall_h"]

# ------------------------------------------------------------------ 场景初始化
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.unit_settings.system = "METRIC"
sc.unit_settings.scale_length = 1.0
col = sc.collection


def material(name, rgb, rough=0.75, metal=0.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    return m


MAT = {
    "roof": material("琉璃黄", (0.70, 0.42, 0.045), 0.45),
    "wall": material("宫墙红", (0.42, 0.075, 0.06), 0.85),
    "citywall": material("城墙红", (0.38, 0.095, 0.075), 0.9),
    "stone": material("台基白", (0.66, 0.63, 0.55), 0.85),
    "ground": material("城外地面", (0.31, 0.30, 0.27), 0.95),
    "plaza": material("宫城地坪", (0.50, 0.47, 0.41), 0.95),
    "water": material("水面", (0.025, 0.09, 0.15), 0.06, 0.2),
    "green": material("绿地", (0.17, 0.27, 0.12), 0.95),
    "service": material("值房灰", (0.68, 0.66, 0.60), 0.9),
    "path": material("御道", (0.76, 0.73, 0.66), 0.9),
    "glass": material("现代玻璃", (0.16, 0.30, 0.40), 0.25, 0.15),
    "ridge": material("屋脊压顶", (0.32, 0.22, 0.09), 0.5),
}


def box(name, w, d, h, x, y, z0=0.0, mat=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, z0 + h / 2))
    ob = bpy.context.object
    ob.name = name
    ob.scale = (w, d, h)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        ob.data.materials.append(mat)
    return ob


def mesh_from(name, verts, faces, mat=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    if mat:
        ob.data.materials.append(mat)
    return ob


def hip_roof(name, w, d, h, x, y, z0, mat, overhang=3.0, ridge_cap=True):
    """庑殿顶：四坡。w2>=d2 时脊沿 x，否则脊沿 y。"""
    w2, d2 = w + 2 * overhang, d + 2 * overhang
    v = [(-w2 / 2, -d2 / 2, 0), (w2 / 2, -d2 / 2, 0), (w2 / 2, d2 / 2, 0), (-w2 / 2, d2 / 2, 0)]
    if w2 >= d2:
        rl = max(w2 - d2, 0.16 * w2)
        v += [(-rl / 2, 0, h), (rl / 2, 0, h)]
        f = [(0, 1, 5, 4), (2, 3, 4, 5), (1, 2, 5), (3, 0, 4)]
        cap = [(x - rl / 2, y - 1.1, z0 + h), (x + rl / 2, y - 1.1, z0 + h),
               (x + rl / 2, y + 1.1, z0 + h), (x - rl / 2, y + 1.1, z0 + h)]
    else:
        rl = max(d2 - w2, 0.16 * d2)
        v += [(0, -rl / 2, h), (0, rl / 2, h)]
        f = [(1, 2, 5, 4), (3, 0, 4, 5), (0, 1, 4), (2, 3, 5)]
        cap = [(x - 1.1, y - rl / 2, z0 + h), (x + 1.1, y - rl / 2, z0 + h),
               (x + 1.1, y + rl / 2, z0 + h), (x - 1.1, y + rl / 2, z0 + h)]
    ob = mesh_from(name, [(x + a, y + b, z0 + c) for a, b, c in v], f, mat)
    if ridge_cap:
        mesh_from(name + "_脊", cap + [(px, py, pz + 1.2) for px, py, pz in cap],
                  [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)],
                  MAT["ridge"])
    return ob


def gable_roof(name, w, d, h, x, y, z0, mat, overhang=2.2):
    """悬山顶：两坡，屋脊沿长边。"""
    w2, d2 = w + 2 * overhang, d + 2 * overhang
    swap = d2 > w2
    if swap:
        w2, d2 = d2, w2
    v = [(-w2 / 2, -d2 / 2, 0), (w2 / 2, -d2 / 2, 0), (w2 / 2, d2 / 2, 0), (-w2 / 2, d2 / 2, 0),
         (-w2 / 2, 0, h), (w2 / 2, 0, h)]
    f = [(0, 1, 5, 4), (3, 2, 5, 4), (0, 4, 3), (1, 2, 5)]
    if swap:                                   # 脊改沿 y：交换本地 x/y
        v = [(b, a, c) for a, b, c in v]
    return mesh_from(name, [(x + a, y + b, z0 + c) for a, b, c in v], f, mat)


def add_hall(h):
    """殿身 + 台基 + 屋顶（+ 月台 / 门楼）。"""
    w, d = h["w"], h["d"]
    z0 = 0.0
    if h.get("base"):
        b = h["base"]
        box(h["name"] + "_台基", b["w"], b["d"], b["h"], h["cx"], h["cy"], 0.0, MAT["stone"])
        z0 = b["h"]
    if h.get("terrace"):
        t = h["terrace"]
        box(h["name"] + "_月台", t["w"], t["d"], t["h"], h["cx"], t["cy"], 0.0, MAT["stone"])

    body_h = h["h"]
    if h["kind"] == "gate":
        body_mat = MAT["citywall"]
    elif h["kind"] == "modern":
        body_mat = MAT["glass"]
    else:
        body_mat = MAT["wall"]
    box(h["name"], w, d, body_h, h["cx"], h["cy"], z0, body_mat)

    top = z0 + body_h
    roof = h.get("roof", "hip")
    if roof == "hip":
        hip_roof(h["name"] + "_屋顶", w, d, max(0.22 * min(w, d) + 1.2, 4.0),
                 h["cx"], h["cy"], top, MAT["roof"])
    elif roof == "gable":
        gable_roof(h["name"] + "_屋顶", w, d, max(0.26 * min(w, d) + 1.0, 3.2),
                   h["cx"], h["cy"], top, MAT["roof"])
    elif roof == "flat":
        box(h["name"] + "_顶", w, d, 0.9, h["cx"], h["cy"], top, MAT["ridge"])

    if h.get("tower"):
        t = h["tower"]
        tz = z0 + body_h
        box(h["name"] + "_门楼", t["w"], t["d"], t["h"], h["cx"], h["cy"], tz, MAT["wall"])
        ttop = tz + t["h"]
        rh = max(0.24 * min(t["w"], t["d"]) + 0.8, 2.6)
        if h.get("tower_roof") == "gable":
            gable_roof(h["name"] + "_门楼顶", t["w"], t["d"], rh, h["cx"], h["cy"], ttop,
                       MAT["roof"], overhang=2.0)
        else:
            hip_roof(h["name"] + "_门楼顶", t["w"], t["d"], rh, h["cx"], h["cy"], ttop,
                     MAT["roof"], overhang=2.0)
        top = ttop
    return top


# ------------------------------------------------------------------ 地面 / 护城河
box("城外地面", 3000, 3000, 0.4, 0, 0, -0.4, MAT["ground"])
box("宫城地坪", P["width"] + T, P["depth"] + T, 0.6, 0, 0, -0.3, MAT["plaza"])

mw = P["moat_w"]
for nm, (w_, d_, x_, y_) in {
    "南": (2 * (HW + T / 2 + mw), mw, 0, -HD - T / 2 - mw / 2),
    "北": (2 * (HW + T / 2 + mw), mw, 0, HD + T / 2 + mw / 2),
    "东": (mw, 2 * (HD + T / 2), HW + T / 2 + mw / 2, 0),
    "西": (mw, 2 * (HD + T / 2), -HW - T / 2 - mw / 2, 0),
}.items():
    box("护城河" + nm, w_, d_, 1.6, x_, y_, -1.2, MAT["water"])
    # 河岸压石
    box("河岸" + nm, w_ + 3, d_ + 3, 0.35, x_, y_, -0.35, MAT["stone"])

for b in D.BRIDGES:
    box(b["name"], b["w"], b["d"], 1.2, b["cx"], b["cy"], -0.4, MAT["stone"])
    for s in (-1, 1):
        off = (b["w"] / 2 - 1.2) * s
        box(b["name"] + "_栏", 2.0, b["d"], 1.3, b["cx"] + off, b["cy"], 0.8, MAT["stone"])

p = D.PATH
box("御道", p["x1"] - p["x0"], p["y1"] - p["y0"], 0.25, 0, (p["y0"] + p["y1"]) / 2, 0.0, MAT["path"])

# ------------------------------------------------------------------ 城墙 + 角楼
openings = {g["side"]: g["opening"] for g in D.GATES}


def wall_bar(name, w, d, x, y):
    box(name, w, d, H, x, y, 0.0, MAT["citywall"])
    box(name + "_顶", w + 1.2, d + 1.2, 0.7, x, y, H, MAT["ridge"])


for side, y in (("S", -HD), ("N", HD)):
    gw = openings[side]
    seg = HW + T / 2 - gw / 2
    wall_bar(f"城墙{side}1", seg, T, -(gw / 2 + seg / 2), y)
    wall_bar(f"城墙{side}2", seg, T, gw / 2 + seg / 2, y)
for side, x in (("E", HW), ("W", -HW)):
    gw = openings[side]
    seg = HD + T / 2 - gw / 2
    wall_bar(f"城墙{side}1", T, seg, x, -(gw / 2 + seg / 2))
    wall_bar(f"城墙{side}2", T, seg, x, gw / 2 + seg / 2)

ct = D.CORNER_TOWER
for sx in (-1, 1):
    for sy in (-1, 1):
        box("角楼", ct["w"], ct["d"], ct["h"], sx * HW, sy * HD, 0.0, MAT["citywall"])
        hip_roof("角楼顶", ct["w"], ct["d"], 5.0, sx * HW, sy * HD, ct["h"], MAT["roof"], overhang=2.0)

# ------------------------------------------------------------------ 值房 / 琼苑
for i, (cx, cy, w, d, hh) in enumerate(D.service_blocks()):
    box(f"值房{i:02d}", w, d, hh, cx, cy, 0.0, MAT["service"])
    gable_roof(f"值房{i:02d}_顶", w, d, 1.8, cx, cy, hh, MAT["roof"], overhang=1.0)

g = next(z for z in D.ZONES if z["key"] == "garden")
box("琼苑", g["x1"] - g["x0"], g["y1"] - g["y0"], 0.5, (g["x0"] + g["x1"]) / 2,
    (g["y0"] + g["y1"]) / 2, 0.25, MAT["green"])

# ------------------------------------------------------------------ 殿宇
for h in D.HALLS:
    add_hall(h)

# ------------------------------------------------------------------ 相机 / 灯光
cam_data = bpy.data.cameras.new("Cam")
cam_data.clip_start = 1.0
cam_data.clip_end = 40000.0          # 默认 100 m，米制大场景必改
cam = bpy.data.objects.new("Cam", cam_data)
col.objects.link(cam)
sc.camera = cam


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


sun_d = bpy.data.lights.new("Sun", type="SUN")
sun_d.energy = 2.6
sun_d.angle = math.radians(4)
sun = bpy.data.objects.new("Sun", sun_d)
col.objects.link(sun)
sun.rotation_euler = (math.radians(40), math.radians(0), math.radians(225))

sc.world = bpy.data.worlds.new("World")
sc.world.use_nodes = True
bg = sc.world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.60, 0.72, 0.90, 1.0)
bg.inputs[1].default_value = 0.45

sc.render.engine = "CYCLES"
sc.cycles.device = "GPU"
sc.cycles.samples = args.samples
sc.cycles.use_denoising = True
sc.cycles.max_bounces = 6
sc.render.image_settings.file_format = "PNG"
sc.view_settings.view_transform = "Standard"
sc.view_settings.exposure = -0.25

# ------------------------------------------------------------------ 出图
AR = 16 / 9
shots = [
    ("鸟瞰·东南", dict(loc=(820, -980, 520), target=(0, 10, 0), lens=45)),
    ("鸟瞰·正南", dict(loc=(0, -1950, 800), target=(0, 30, 0), lens=55)),
    ("鸟瞰·中轴", dict(loc=(90, -820, 175), target=(0, -70, 0), lens=58)),
    ("人视·金瓯殿", dict(loc=(120, -300, 10.0), target=(-15, -178, 20), lens=35)),
]

results = {}
for name, s in shots:
    cam.location = s["loc"]
    cam_data.type = "PERSP"
    cam_data.lens = s["lens"]
    look_at(cam, s["target"])
    sc.render.resolution_x = args.res
    sc.render.resolution_y = int(args.res / AR)
    path = os.path.join(WORK, f"massing_{name}.png")
    sc.render.filepath = path
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    results[name] = {"s": round(time.time() - t0, 1), "bytes": os.path.getsize(path)}
    print("RENDER", name, results[name])

cam_data.type = "ORTHO"
cam_data.ortho_scale = 1480
cam.location = (0, 0, 4000)
cam.rotation_euler = (0, 0, 0)
sc.render.resolution_x, sc.render.resolution_y = (1400, 1780)
path = os.path.join(WORK, "massing_正射总平面.png")
sc.render.filepath = path
t0 = time.time()
bpy.ops.render.render(write_still=True)
results["正射总平面"] = {"s": round(time.time() - t0, 1), "bytes": os.path.getsize(path)}
cam_data.type = "PERSP"

# （素模一版因白对白看不出体量，已弃用；要看形体用鸟瞰图）

# ------------------------------------------------------------------ 导出
blend = os.path.join(WORK, "palace_massing.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend)
glb = os.path.join(WORK, "palace_massing.glb")
bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", export_apply=True)

tris = 0
for o in col.objects:
    if o.type == "MESH":
        o.data.calc_loop_triangles()
        tris += len(o.data.loop_triangles)

print("RESULT " + json.dumps({
    "renders": results, "objects": len(col.objects), "triangles": tris,
    "blend": blend, "glb": glb, "glb_mb": round(os.path.getsize(glb) / 1e6, 2),
}, ensure_ascii=False))
