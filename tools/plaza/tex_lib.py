"""可平铺贴图（砖石分缝 / 琉璃釉面）与盒式投影 UV。

背景：精模的砖缝、琉璃色差原本都是程序化节点（Brick / Wave），
glTF 不支持程序化节点，导出后只剩纯色 —— 交付文件里材质细节全丢。
这里把它们烘成 1K 可平铺 PNG（sRGB 编码，非色彩空间给法线），
再用世界坐标盒式投影生成 UV，保证贴图按米制比例平铺、不依赖展 UV。

对外接口：
    setup(MAT, texdir) -> {material_name: tile_m}      生成贴图并改写 4 个材质
    apply_uv(objects, tiles, default_tile=4.8)          给相关网格写 UVMap
"""

import os
import struct
import zlib

import bpy
import numpy as np

UV_NAME = "UVMap"


# ------------------------------------------------------------------ PNG 输出
def _write_png(path, arr):
    """arr: uint8 HxWx3（自上而下）→ 8bit RGB PNG。"""
    h, w, _ = arr.shape
    raw = b"".join(b"\x00" + arr[r].tobytes() for r in range(h))

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 6))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


def _srgb(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def _rgb8(linear):
    return (_srgb(linear) * 255.0 + 0.5).astype(np.uint8)


def _nrm8(height, strength=3.0):
    gy, gx = np.gradient(height.astype(np.float32))
    nx, ny = -gx * strength, -gy * strength
    nz = np.ones_like(height)
    n = np.sqrt(nx * nx + ny * ny + nz * nz)
    rgb = np.stack([nx / n, ny / n, nz / n], -1) * 0.5 + 0.5
    return (np.clip(rgb, 0, 1) * 255.0 + 0.5).astype(np.uint8)


# ------------------------------------------------------------------ 图案
def _brick(tile_m=4.8, res=1024, bw=2.4, bh=1.2, mortar=0.025,
           c1=(0.47, 0.45, 0.40), c2=(0.37, 0.35, 0.31), mc=(0.10, 0.09, 0.08)):
    """错缝砖：平铺尺寸 tile_m，返回 (albedo 线性, height)。"""
    px = res / tile_m
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float32)
    X = (xx + 0.5) / px
    Y = (yy + 0.5) / px

    row = np.floor(Y / bh).astype(np.int32)
    off = (row % 2) * (bw * 0.5)
    xr = np.mod(X + off, bw)
    yr = np.mod(Y, bh)
    d = np.minimum(np.minimum(xr, bw - xr), np.minimum(yr, bh - yr))
    m = mortar * 0.5
    is_brick = d > m

    col = np.floor((X + off) / bw).astype(np.int32)
    hsh = ((col.astype(np.int64) * 73856093) ^ (row.astype(np.int64) * 19349663)) & 0xFFFF
    t = ((hsh % 101) / 100.0).astype(np.float32)[..., None]
    alb = np.array(c1, np.float32) * (1 - t) + np.array(c2, np.float32) * t
    alb = np.where(is_brick[..., None], alb, np.array(mc, np.float32))

    rng = np.random.default_rng(7)
    alb = alb * (0.965 + 0.07 * rng.random((res, res, 1), dtype=np.float32))

    edge = np.clip((d - m) / 0.018, 0.0, 1.0)
    height = np.where(is_brick, 0.80 + 0.20 * edge, 0.0).astype(np.float32)
    return alb.astype(np.float32), height


def _glaze(tile_m=1.38, res=512, base=(0.06, 0.10, 0.085), amp=0.16):
    """琉璃釉面：低频色差 + 极浅的纵向流痕，避免与已建模的瓦垄叠出摩尔纹。"""
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float32)
    u, v = xx / res, yy / res

    def wave(fx, fy, ph):
        return np.sin(2 * np.pi * (fx * u + fy * v) + ph)

    n = (0.45 * wave(2, 1, 0.3) + 0.28 * wave(1, 3, 1.7)
         + 0.17 * wave(3, 2, 4.1) + 0.10 * wave(4, 5, 2.2))
    n = (n - n.min()) / (n.max() - n.min())

    tint = 0.88 + 0.24 * n
    alb = np.array(base, np.float32)[None, None, :] * tint[..., None]
    alb = alb * (0.98 + 0.04 * np.random.default_rng(11).random((res, res, 1), np.float32))

    streak = 0.5 + 0.5 * np.sin(2 * np.pi * 6 * u + 0.6 * wave(1, 4, 0.9))
    height = (0.5 + amp * 0.5 * streak * (n - 0.5) * 2.0).astype(np.float32)
    return np.clip(alb, 0, 1).astype(np.float32), height


# ------------------------------------------------------------------ Blender 材质
def _image(path, non_color=False):
    img = bpy.data.images.load(path, check_existing=True)
    if non_color:
        img.colorspace_settings.name = "Non-Color"
    if not img.packed_file:
        img.pack()
    return img


def _load_material(m, albedo, normal, rough):
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type not in {"BSDF_PRINCIPLED", "OUTPUT_MATERIAL"}:
            nt.nodes.remove(n)
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = rough

    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = UV_NAME
    uv.location = (-620, 220)

    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = _image(albedo)
    tex.interpolation = "Smart"
    tex.location = (-380, 220)
    nt.links.new(uv.outputs["UV"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])

    ntex = nt.nodes.new("ShaderNodeTexImage")
    ntex.image = _image(normal, non_color=True)
    ntex.interpolation = "Smart"
    ntex.location = (-380, -120)
    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nmap.location = (-120, -120)
    nt.links.new(uv.outputs["UV"], ntex.inputs["Vector"])
    nt.links.new(ntex.outputs["Color"], nmap.inputs["Color"])
    nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])


def setup(MAT, texdir, brick_res=1024):
    """生成 4 套贴图并改写材质；返回 {材质名: 平铺尺寸(m)}。"""
    os.makedirs(texdir, exist_ok=True)

    specs = [
        ("stone", 4.8, dict(bw=2.4, bh=1.2, mortar=0.025,
                            c1=(0.47, 0.45, 0.40), c2=(0.37, 0.35, 0.31),
                            mc=(0.10, 0.09, 0.08)), 0.85),
        ("marble", 4.8, dict(bw=2.4, bh=1.2, mortar=0.020,
                             c1=(0.82, 0.80, 0.74), c2=(0.74, 0.72, 0.66),
                             mc=(0.30, 0.29, 0.27)), 0.7),
        ("paving", 4.8, dict(bw=2.4, bh=1.2, mortar=0.020,
                             c1=(0.54, 0.52, 0.46), c2=(0.46, 0.44, 0.39),
                             mc=(0.26, 0.25, 0.23)), 0.9),
    ]

    tiles = {}
    for key, tile_m, params, rough in specs:
        alb, hgt = _brick(tile_m=tile_m, res=brick_res, **params)
        name = key
        a_path = os.path.join(texdir, f"{name}_albedo.png")
        n_path = os.path.join(texdir, f"{name}_normal.png")
        _write_png(a_path, _rgb8(alb))
        _write_png(n_path, _nrm8(hgt, strength=2.6))
        _load_material(MAT[key], a_path, n_path, rough)
        tiles[MAT[key].name] = tile_m

    # 琉璃·青：釉面色差
    alb, hgt = _glaze(res=512)
    a_path = os.path.join(texdir, "roof_albedo.png")
    n_path = os.path.join(texdir, "roof_normal.png")
    _write_png(a_path, _rgb8(alb))
    _write_png(n_path, _nrm8(hgt, strength=0.8))
    _load_material(MAT["roof_tile"], a_path, n_path, 0.45)
    tiles[MAT["roof_tile"].name] = 1.38

    print("TEX", {k: round(v, 2) for k, v in tiles.items()}, flush=True)
    return tiles


# ------------------------------------------------------------------ UV
def apply_uv(objects, tiles, default_tile=4.8):
    """按世界坐标做盒式投影，写入 UVMap；只处理用到贴图材质的网格。"""
    tile_arr = np.array(sorted(set(tiles.values())), np.float32)
    n_ob = n_loop = 0
    for ob in objects:
        if ob.type != "MESH":
            continue
        me = ob.data
        if len(me.loops) == 0 or not ob.material_slots:
            continue
        names = [s.material.name if s.material else "" for s in ob.material_slots]
        if not any(n in tiles for n in names):
            continue

        npoly = len(me.polygons)
        nloop = len(me.loops)
        nvert = len(me.vertices)
        mi = np.empty(npoly, np.int32)
        me.polygons.foreach_get("material_index", mi)
        lt = np.empty(npoly, np.int32)
        me.polygons.foreach_get("loop_total", lt)
        fn = np.empty(npoly * 3, np.float32)
        me.polygons.foreach_get("normal", fn)
        fn = fn.reshape(npoly, 3)
        vidx = np.empty(nloop, np.int32)
        me.loops.foreach_get("vertex_index", vidx)
        co = np.empty(nvert * 3, np.float32)
        me.vertices.foreach_get("co", co)
        co = co.reshape(nvert, 3)

        mw = np.array(ob.matrix_world, np.float32)
        world = co @ mw[:3, :3].T + mw[:3, 3]

        poly_of_loop = np.repeat(np.arange(npoly), lt)
        ax = np.argmax(np.abs(fn[poly_of_loop]), axis=1)
        p = world[vidx]
        u = np.where(ax == 0, p[:, 1], p[:, 0])
        v = np.where(ax <= 1, p[:, 2], p[:, 1])

        per_poly = np.full(npoly, default_tile, np.float32)
        for i, nm in enumerate(names):
            if nm in tiles:
                per_poly[mi == i] = tiles[nm]
        uv = np.stack([u, v], 1) / np.repeat(per_poly, lt)[:, None]

        layer = me.uv_layers.get(UV_NAME) or me.uv_layers.new(name=UV_NAME)
        layer.data.foreach_set("uv", uv.astype(np.float32).ravel())

        n_ob += 1
        n_loop += nloop

    print(f"UV {n_ob} objects / {n_loop} loops", flush=True)
