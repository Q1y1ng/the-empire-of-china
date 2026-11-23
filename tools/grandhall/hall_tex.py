"""万人大礼堂精模的可平铺贴图与盒式投影 UV。

背景与 `tools/plaza/tex_lib.py` 相同：glTF 不支持程序化节点，石材分缝、
大理石纹、地毯绒面、木纹、金饰拉丝若用节点画，导出的 glb 里只剩纯色。
这里把它们烘成 1K 可平铺 PNG（sRGB 给 albedo，Non-Color 给法线），
再用**世界坐标盒式投影**写 UVMap：按米制平铺、不依赖展 UV、不随缩放走样。

对外接口：
    setup(MAT, texdir) -> {材质名: 平铺尺寸(m)}
    apply_uv(objects, tiles)
"""

from __future__ import annotations

import os
import struct
import zlib

import bpy
import numpy as np

UV_NAME = "UVMap"


# ------------------------------------------------------------------ PNG
def _write_png(path, arr):
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


def _rgb8(lin):
    return (_srgb(lin) * 255.0 + 0.5).astype(np.uint8)


def _nrm8(height, strength=3.0):
    gy, gx = np.gradient(height.astype(np.float32))
    nx, ny = -gx * strength, -gy * strength
    nz = np.ones_like(height)
    n = np.sqrt(nx * nx + ny * ny + nz * nz)
    return (np.clip(np.stack([nx / n, ny / n, nz / n], -1) * 0.5 + 0.5, 0, 1) * 255.0
            + 0.5).astype(np.uint8)


# ------------------------------------------------------------------ 图案
def _panels(tile_m=4.8, res=1024, bw=1.2, bh=1.2, mortar=0.008,
            base=(0.44, 0.13, 0.11), var=0.10, mc=(0.16, 0.09, 0.08),
            vein=0.0):
    """分缝板材：bw×bh 板、错缝，逐板色差 + 可选石纹。"""
    px = res / tile_m
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float32)
    X, Y = (xx + 0.5) / px, (yy + 0.5) / px
    row = np.floor(Y / bh).astype(np.int32)
    off = (row % 2) * (bw * 0.5)
    xr = np.mod(X + off, bw)
    yr = np.mod(Y, bh)
    d = np.minimum(np.minimum(xr, bw - xr), np.minimum(yr, bh - yr))
    m = mortar * 0.5
    slab = d > m

    col = np.floor((X + off) / bw).astype(np.int64)
    hsh = ((col * 73856093) ^ (row.astype(np.int64) * 19349663)) & 0xFFFF
    t = ((hsh % 101) / 100.0).astype(np.float32)[..., None]
    alb = np.array(base, np.float32) * (1.0 - var + 2 * var * t)

    if vein > 0:
        u, v = X / tile_m * 6.0, Y / tile_m * 6.0
        w = (np.sin(6.1 * u + 2.3 * v) * np.sin(3.7 * v + 1.1 * u)
             + 0.5 * np.sin(11.0 * u - 4.0 * v))
        alb = alb * (1.0 + vein * (w[..., None]))

    rng = np.random.default_rng(7)
    alb = alb * (0.985 + 0.03 * rng.random((res, res, 1), dtype=np.float32))
    alb = np.where(slab[..., None], alb, np.array(mc, np.float32))
    edge = np.clip((d - m) / 0.006, 0.0, 1.0)
    height = np.where(slab, 0.85 + 0.15 * edge, 0.0).astype(np.float32)
    return np.clip(alb, 0, 1).astype(np.float32), height


def _plank(tile_m=2.4, res=512, n=6, base=(0.26, 0.13, 0.06), mc=(0.06, 0.03, 0.02)):
    """木地板／台面：长条板 + 木纹。"""
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float32)
    u, v = xx / res, yy / res
    bh = 1.0 / n
    row = np.floor(v / bh).astype(np.int32)
    vr = v - row * bh
    gap = np.minimum(vr, bh - vr)
    board = gap > 0.004
    grain = (np.sin(90 * u + 8 * np.sin(6 * v + row))
             + 0.6 * np.sin(170 * u + 3 * v)) * 0.5
    alb = np.array(base, np.float32)[None, None, :] * (0.86 + 0.28 * grain[..., None])
    hsh = ((row.astype(np.int64) * 73856093) & 0xFFFF).astype(np.float32)[..., None] / 65535.0
    alb = alb * (0.92 + 0.16 * hsh)
    alb = np.where(board[..., None], alb, np.array(mc, np.float32))
    height = np.where(board, 0.8 + 0.2 * np.clip(gap / 0.01, 0, 1), 0.0).astype(np.float32)
    return np.clip(alb, 0, 1).astype(np.float32), height


def _fabric(tile_m=0.6, res=512, base=(0.30, 0.035, 0.045)):
    """座椅织物：经纬 + 绒面噪点。"""
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float32)
    u, v = xx / res, yy / res
    wf = 0.5 + 0.5 * np.sin(2 * np.pi * 160 * u)
    wt = 0.5 + 0.5 * np.sin(2 * np.pi * 160 * v)
    weave = (wf * wt) ** 1.6
    rng = np.random.default_rng(3)
    noise = rng.random((res, res), dtype=np.float32)
    alb = np.array(base, np.float32)[None, None, :] * (0.60 + 0.75 * weave[..., None])
    alb = alb * (0.94 + 0.12 * noise[..., None])
    return np.clip(alb, 0, 1).astype(np.float32), (0.5 + 0.5 * weave).astype(np.float32)


def _gold(tile_m=1.2, res=512, base=(0.62, 0.42, 0.06)):
    """镏金：细拉丝 + 低频色差。"""
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float32)
    u, v = xx / res, yy / res
    brush = 0.5 + 0.5 * np.sin(2 * np.pi * 220 * u + 3 * np.sin(2 * np.pi * 3 * v))
    slow = 0.5 + 0.5 * np.sin(2 * np.pi * 2 * v + 1.3 * np.sin(2 * np.pi * u))
    alb = np.array(base, np.float32)[None, None, :] * (0.86 + 0.16 * slow[..., None]
                                                       + 0.10 * brush[..., None])
    return np.clip(alb, 0, 1).astype(np.float32), (0.5 + 0.35 * brush).astype(np.float32)


# ------------------------------------------------------------------ Blender
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
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = rough

    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = UV_NAME
    uv.location = (-620, 220)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = _image(albedo)
    tex.interpolation = "Smart"
    tex.location = (-380, 220)
    nt.links.new(uv.outputs["UV"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])

    ntex = nt.nodes.new("ShaderNodeTexImage")
    ntex.image = _image(normal, non_color=True)
    ntex.interpolation = "Smart"
    ntex.location = (-380, -120)
    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nmap.location = (-120, -120)
    nt.links.new(uv.outputs["UV"], ntex.inputs["Vector"])
    nt.links.new(ntex.outputs["Color"], nmap.inputs["Color"])
    nt.links.new(nmap.outputs["Normal"], b.inputs["Normal"])


SPECS = [
    # key,          平铺(m), 图案,       参数,                                                   粗糙
    ("floor", 4.8, _panels, dict(bw=1.2, bh=1.2, mortar=0.006,
                                 base=(0.46, 0.17, 0.14), var=0.12,
                                 mc=(0.18, 0.10, 0.09), vein=0.10), 0.22),
    ("wall", 4.8, _panels, dict(bw=2.4, bh=1.2, mortar=0.006,
                                base=(0.74, 0.72, 0.66), var=0.05,
                                mc=(0.42, 0.41, 0.38)), 0.32),
    ("ceil", 4.8, _panels, dict(bw=1.2, bh=1.2, mortar=0.004,
                                base=(0.80, 0.77, 0.70), var=0.03,
                                mc=(0.62, 0.60, 0.55)), 0.65),
    ("stage", 2.4, _plank, dict(n=6), 0.45),
    ("seat", 0.6, _fabric, dict(), 0.85),
    ("gold", 1.2, _gold, dict(), 0.28),
]


def setup(MAT, texdir, res=1024):
    """生成贴图并改写材质；返回 {材质名: 平铺尺寸(m)}，供 apply_uv 用。"""
    os.makedirs(texdir, exist_ok=True)
    tiles = {}
    for key, tile_m, fn, params, rough in SPECS:
        m = MAT.get(key)
        if m is None:
            continue
        alb, hgt = fn(tile_m=tile_m, res=res if key != "seat" else 512, **params)
        a = os.path.join(texdir, f"{key}_albedo.png")
        n = os.path.join(texdir, f"{key}_normal.png")
        _write_png(a, _rgb8(alb))
        _write_png(n, _nrm8(hgt, strength=2.2 if key != "seat" else 1.2))
        _load_material(m, a, n, rough)
        tiles[m.name] = tile_m
        print(f"TEX {key} tile={tile_m} m", flush=True)
    return tiles


# ------------------------------------------------------------------ UV
def apply_uv(objects, tiles, default_tile=4.8):
    tile_arr = np.array(sorted(set(tiles.values())), np.float32)
    n_ob = n_loop = 0
    for ob in objects:
        if ob.type != "MESH":
            continue
        me = ob.data
        if len(me.loops) == 0 or not ob.material_slots:
            continue
        names = [s.material.name if s.material else "" for s in ob.material_slots]
        if not any(nm in tiles for nm in names):
            continue

        npoly, nloop, nvert = len(me.polygons), len(me.loops), len(me.vertices)
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
