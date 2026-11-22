"""Headless verification for palace HDR assets (Blender 5.3).

Loads each downloaded .hdr into a World > Environment Texture node, renders a
480x270 sphere + ground plane with Cycles (world lighting only), then re-opens
the saved PNG and reports pixel statistics so a black/blank render cannot pass
silently.

Usage:
  blender -b --factory-startup -P verify_hdri.py -- <asset_dir> <out_dir>
"""

import sys
import os

import bpy
import numpy as np

TAG = "[verify]"


def log(msg):
    print("%s %s" % (TAG, msg), flush=True)


def parse_args():
    argv = sys.argv
    rest = argv[argv.index("--") + 1:] if "--" in argv else []
    asset_dir = rest[0] if len(rest) > 0 else "."
    out_dir = rest[1] if len(rest) > 1 else asset_dir
    return asset_dir, out_dir


def clear_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)


def make_material(name, color, roughness, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def build_scene():
    clear_scene()
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 64
    scene.cycles.use_denoising = False
    scene.render.resolution_x = 480
    scene.render.resolution_y = 270
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    # Keep the metric interpretable (no AgX tone curve). Pure-sky HDRIs carry a
    # very bright sun disc, so at exposure 0 the Standard transform clips to
    # white; -2.5 EV keeps the mid-tones inside 0..1 so the PNG is reviewable.
    try:
        scene.view_settings.view_transform = "Standard"
        scene.view_settings.exposure = -2.5
    except Exception as exc:  # pragma: no cover
        log("view_transform not set: %r" % (exc,))

    # ground
    bpy.ops.mesh.primitive_plane_add(size=24.0, location=(0.0, 0.0, 0.0))
    ground = bpy.context.active_object
    ground.name = "ground"
    ground.data.materials.append(make_material("m_ground", (0.22, 0.21, 0.20), 0.85))

    # sphere
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.2, segments=64, ring_count=32,
                                         location=(0.0, 0.0, 1.2))
    sphere = bpy.context.active_object
    sphere.name = "sphere"
    bpy.ops.object.shade_smooth()
    sphere.data.materials.append(make_material("m_sphere", (0.80, 0.79, 0.76), 0.35))

    # camera
    bpy.ops.object.empty_add(location=(0.0, 0.0, 0.95))
    target = bpy.context.active_object
    target.name = "cam_target"
    bpy.ops.object.camera_add(location=(4.6, -4.6, 2.9))
    cam = bpy.context.active_object
    cam.data.lens = 50.0
    con = cam.constraints.new(type="TRACK_TO")
    con.target = target
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"
    scene.camera = cam
    return scene


def build_world():
    scene = bpy.context.scene
    world = bpy.data.worlds.new("palace_world")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    bg.inputs["Strength"].default_value = 1.0
    nt.links.new(env.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    return env


def image_stats(img):
    """Return (mean_rgb, max_rgb, nonzero_frac) of an image datablock."""
    px = img.size[0] * img.size[1] * 4
    buf = np.empty(px, dtype=np.float32)
    img.pixels.foreach_get(buf)
    return buf


def srgb_to_255(lin):
    lin = np.clip(lin, 0.0, 1.0)
    enc = np.where(lin <= 0.0031308, lin * 12.92,
                   1.055 * np.power(lin, 1.0 / 2.4) - 0.055)
    return enc * 255.0


def inventory_textures(asset_dir):
    """Load every tex_* map so Blender-side read problems show up as evidence."""
    names = sorted(n for n in os.listdir(asset_dir) if n.startswith("tex_"))
    log("texture inventory (%d files):" % len(names))
    for n in names:
        p = os.path.join(asset_dir, n)
        try:
            img = bpy.data.images.load(p, check_existing=False)
        except Exception as exc:
            log("  FAILED %s: %r" % (n, exc))
            continue
        log("  %-32s %dx%d channels=%d colorspace=%s depth=%s" % (
            n, img.size[0], img.size[1], img.channels,
            img.colorspace_settings.name, img.depth))


def report_png(path):
    img = bpy.data.images.load(path, check_existing=False)
    buf = image_stats(img)
    arr = buf.reshape(-1, 4)[:, :3]
    lin = arr.astype(np.float64)
    mean255 = float(srgb_to_255(lin).mean())
    mx = float(lin.max())
    bright_frac = float((lin.max(axis=1) > 0.02).mean())
    clip_frac = float((lin >= 0.999).all(axis=1).mean())
    return {
        "size": (img.size[0], img.size[1]),
        "mean_linear": float(lin.mean()),
        "mean_srgb_255": mean255,
        "max_linear": mx,
        "frac_above_0.02": bright_frac,
        "frac_clipped": clip_frac,
    }


def report_hdr(path):
    img = bpy.data.images.load(path, check_existing=False)
    buf = image_stats(img)
    arr = buf.reshape(-1, 4)[:, :3].astype(np.float64)
    return {
        "size": (img.size[0], img.size[1]),
        "is_float": bool(img.is_float),
        "mean": float(arr.mean()),
        "max": float(arr.max()),
        "frac_zero": float((arr.max(axis=1) <= 1e-6).mean()),
    }


def main():
    asset_dir, out_dir = parse_args()
    os.makedirs(out_dir, exist_ok=True)
    inventory_textures(asset_dir)
    scene = build_scene()
    env = build_world()

    hdrs = [
        ("hdri_sky_sunny_2k.hdr", "verify.png"),
        ("hdri_sky_overcast_2k.hdr", "verify_overcast.png"),
    ]

    failures = []
    for hdr_name, png_name in hdrs:
        hdr_path = os.path.join(asset_dir, hdr_name)
        if not os.path.isfile(hdr_path):
            failures.append("%s missing" % hdr_name)
            log("MISSING %s" % hdr_path)
            continue

        log("loading HDR: %s" % hdr_path)
        hdr_img = bpy.data.images.load(hdr_path, check_existing=False)
        env.image = hdr_img
        hdr_stats = report_hdr(hdr_path)
        log("  hdr size=%dx%d float=%s mean=%.5f max=%.3f zero_frac=%.3f" % (
            hdr_stats["size"][0], hdr_stats["size"][1], hdr_stats["is_float"],
            hdr_stats["mean"], hdr_stats["max"], hdr_stats["frac_zero"]))
        if hdr_stats["max"] <= 0.0:
            failures.append("%s decodes to all zeros" % hdr_name)

        out_path = os.path.join(out_dir, png_name)
        scene.render.filepath = out_path
        log("rendering -> %s" % out_path)
        bpy.ops.render.render(write_still=True)

        if not os.path.isfile(out_path):
            failures.append("%s not written" % png_name)
            continue
        st = report_png(out_path)
        log("  png %dx%d mean_linear=%.5f mean_sRGB/255=%.2f max=%.4f bright_frac=%.3f clipped=%.3f" % (
            st["size"][0], st["size"][1], st["mean_linear"], st["mean_srgb_255"],
            st["max_linear"], st["frac_above_0.02"], st["frac_clipped"]))
        if st["mean_srgb_255"] < 8.0:
            failures.append("%s too dark (mean_sRGB=%.2f)" % (png_name, st["mean_srgb_255"]))
        if st["frac_above_0.02"] < 0.30:
            failures.append("%s mostly black (bright_frac=%.3f)" % (
                png_name, st["frac_above_0.02"]))

    if failures:
        log("RESULT: FAIL")
        for f in failures:
            log("  - %s" % f)
        sys.exit(1)
    log("RESULT: PASS (all HDRI renders non-black)")


if __name__ == "__main__":
    main()
