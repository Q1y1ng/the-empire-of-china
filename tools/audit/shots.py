"""接触表：在**已保存的 .blend** 上出 Workbench 快速图，并可选导出 manifest.json。

设计口径（与作品会话 2026-11-28 商定）：
  * 站位不复制——从 `build_hall.py` 的 `SHOTS` 读（见 shots_table.py），
    他们改机位，这里自动跟。
  * 不再付 40 s 构建费：接收一个 .blend，只开图。所以 build 一次、看图多次。
  * Workbench 只判“关系”（净空、悬空、过道、朝向），**不判“好不好看”**：
    它给的是 viewport 色 + cavity + 阴影，没有 PBR/URP/ACES。
  * 分辨率默认 1280×720：640×360 看不出 2 cm 缝与 40 cm 悬空。

用法（由 run_shots.py 调用，也可手动）：
    blender.exe -b grandhall_precise.blend -P shots.py -- \
        --out "$TEMP/grandhall_shots" [--only 座椅落地,二层净空] \
        [--res 1280] [--manifest manifest.json] [--keep-png]

产物：<out>/<机位名>.png ；manifest: {blend, blender, generated, shots, objects[]}
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import bpy
from mathutils import Vector

try:                      # MSYS bash 里控制台是 UTF-8，Python 默认 cp936 会输出乱码
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from shots_table import load_shots  # noqa: E402

# ------------------------------------------------------------------ 参数
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--only", default="")
ap.add_argument("--res", type=int, default=1280)
ap.add_argument("--manifest", default="")
ap.add_argument("--color", choices=("group", "material"), default="group",
                help="group=按分组上色（判关系）；material=材质视口色（判材质配色）")
ap.add_argument("--exposure", type=float, default=0.7,
                help="Workbench 室内偏暗，默认 +0.7 EV；Standard 变换下生效")
ap.add_argument("--keep-png", action="store_true",
                help="保留单张 PNG（默认保留，此开关仅为兼容）")
args = ap.parse_args(argv)
args.out = os.path.abspath(args.out)
os.makedirs(args.out, exist_ok=True)

sc = bpy.context.scene
EXPOSURE = args.exposure


# ------------------------------------------------------------------ 视图色
def sync_viewport_colors():
    """Workbench 的 MATERIAL 色走 material.diffuse_color，而精模材质是节点图。

    纯色节点材质：把 Principled 的 Base Color 抄到 diffuse_color，
    否则整栋楼在 Workbench 里是一个灰。贴图驱动的材质不动（抄不出效果）。
    """
    done = 0
    for m in bpy.data.materials:
        if not m.use_nodes or not m.node_tree:
            continue
        bsdf = m.node_tree.nodes.get("Principled BSDF")
        if bsdf is None:
            continue
        inp = bsdf.inputs.get("Base Color")
        if inp is None or inp.is_linked:
            continue
        rgba = tuple(inp.default_value)
        if len(rgba) == 3:
            rgba = (*rgba, 1.0)
        m.diffuse_color = rgba
        done += 1
    print(f"VIEWPORT_COLORS {done}", flush=True)


def setup_workbench(res, ar, color="group"):
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "STUDIO"
    sh.color_type = "OBJECT" if color == "group" else "MATERIAL"
    sh.show_shadows = True
    sh.show_cavity = True
    try:
        sh.cavity_type = "BOTH"
        sh.cavity_ridge_factor = 1.0
        sh.cavity_valley_factor = 1.0
        sh.curvature_ridge_factor = 1.5
        sh.curvature_valley_factor = 1.5
        sh.shadow_intensity = 0.55
    except Exception as exc:          # 版本差异不致命
        print("SHADING_PARTIAL", exc, flush=True)
    try:
        sh.background_type = "VIEWPORT"
        sh.background_color = (0.055, 0.058, 0.065)
    except Exception:
        pass
    try:
        sc.display.render_aa = "8"
    except Exception:
        pass
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = EXPOSURE
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.image_settings.color_depth = "8"
    sc.render.resolution_x = res
    sc.render.resolution_y = int(round(res / ar))
    sc.render.resolution_percentage = 100
    print(f"ENGINE WORKBENCH {res}x{int(round(res / ar))}", flush=True)


# ------------------------------------------------------------------ 分组配色
# Workbench 的 OBJECT 色：目的是“分得清构件”，不是好看。已知分组给固定色相，
# 其余按名字散列取色；明度统一压在 0.5–0.8，否则 cavity 与阴影会被亮色吃掉。
import colorsys  # noqa: E402

KNOWN_HUE = {
    "shell": 0.08, "wall_rear": 0.08, "wall_n": 0.07, "wall_s": 0.09,
    "floor": 0.60, "foyer_floor": 0.58,
    "seat0": 0.55, "seat1": 0.52, "seat2": 0.49,
    "bal1": 0.38, "bal2": 0.34, "rear": 0.30,
    "stage": 0.02, "dome": 0.13,
    "foyer_glass": 0.50, "foyer_wall": 0.72, "foyer_col": 0.68,
    "foyer_door": 0.04, "foyer_ceil": 0.75, "foyer_lamp": 0.16,
}


def color_of(group):
    if group in KNOWN_HUE:
        h = KNOWN_HUE[group]
        s, v = 0.55, 0.78
    else:
        idx = sum((i + 7) * ord(c) for i, c in enumerate(group))
        h = (idx * 0.61803398875) % 1.0
        s, v = 0.45, 0.72
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (r, g, b, 1.0)


def paint_groups():
    n = 0
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        o.color = color_of(o.get("group") or "hall")
        n += 1
    print(f"OBJECT_COLORS {n}", flush=True)


def get_camera():
    cam = bpy.data.objects.get("Cam")
    if cam is None or cam.type != "CAMERA":
        data = bpy.data.cameras.new("Cam")
        data.clip_start, data.clip_end = 0.5, 20000.0
        cam = bpy.data.objects.new("Cam", data)
        sc.collection.objects.link(cam)
    sc.camera = cam
    return cam


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def hide_groups(spec):
    hid = set(spec.get("hide", ()))
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        g = o.get("group")
        if g is not None:
            o.hide_render = g in hid


# ------------------------------------------------------------------ manifest
def dump_manifest(path):
    """与 build_hall.py --manifest 同一 schema（manifest_io.save）。

    shots.py 不认识座席数，seats 留 null；模式从 .blend 文件名推断。
    """
    import manifest_io
    t0 = time.time()
    items = []
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        mw = o.matrix_world
        lo = [1e18] * 3
        hi = [-1e18] * 3
        for c in o.bound_box:
            w = mw @ Vector(c)
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
        me = o.data
        me.calc_loop_triangles()
        items.append({
            "name": o.name,
            "group": o.get("group") or "hall",
            "tris": len(me.loop_triangles),
            "min": [round(v, 3) for v in lo],
            "max": [round(v, 3) for v in hi],
        })
    mode = "precise" if "precise" in os.path.basename(bpy.data.filepath) else "massing"
    doc = manifest_io.save(path, mode, items, seats=None,
                           extra={"blend": bpy.data.filepath,
                                  "blender": bpy.app.version_string,
                                  "generated": time.strftime("%Y-%m-%dT%H:%M:%S")})
    print("MANIFEST", path, doc["objects"], doc["triangles"],
          round(time.time() - t0, 1), "s", flush=True)


# ------------------------------------------------------------------ 主流程
AR = 16 / 9
table = load_shots()
only = [s.strip() for s in args.only.split(",") if s.strip()]
sync_viewport_colors()
paint_groups()
setup_workbench(args.res, AR, args.color)
cam = get_camera()

renders = {}
for name, spec in table:
    if only and not any(k in name for k in only):
        continue
    hide_groups(spec)
    ar = spec.get("ar", AR)
    sc.render.resolution_x = args.res
    sc.render.resolution_y = int(round(args.res / ar))
    cam.location = spec["loc"]
    if spec.get("ortho"):
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = spec["ortho"]
    else:
        cam.data.type = "PERSP"
        cam.data.lens = spec.get("lens", 35)
    look_at(cam, spec["target"])
    path = os.path.join(args.out, f"{name}.png")
    sc.render.filepath = path
    t = time.time()
    bpy.ops.render.render(write_still=True)
    renders[name] = round(time.time() - t, 2)
    print("SHOT", name, renders[name], "s", flush=True)

for o in bpy.data.objects:
    if o.type == "MESH":
        o.hide_render = False

if args.manifest:
    dump_manifest(os.path.abspath(args.manifest))

print("RESULT " + json.dumps({"renders": renders, "out": args.out},
                             ensure_ascii=False), flush=True)
