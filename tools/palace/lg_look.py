"""皇宫精模 · 材质与环境光照（lg_look = "look dev"）

一个文件解决三件事，供 build_precise.py / build_massing.py --precise 直接调用：

    import lg_look
    MAT = lg_look.make_materials()      # 键名与 precise_lib.MAT 完全一致，可直接 update
    lg_look.setup_world(sc, hdri_path="tools/palace/assets/hdri_sky_sunny_2k.hdr")
    lg_look.setup_sun(sc)
    lg_look.setup_render(sc, res=1920, samples=128)
    lg_look.render(sc, "out.png")       # 失败自动退回 OIDN 再渲一次

设计口径
--------
* 全部程序化（无外部贴图），只有 HDR 是可选的；找不到 HDR 自动退回 Nishita 天空。
* 单位是米。屋顶瓦垄按 **UV（米制）** 做图案，U 周期 0.32 m、V 周期 0.30 m；
  网格没有 UV 时按世界法线做投影兜底（UV 缺失时 Cycles 返回 (0,0)，用它当开关）。
* 精模构件是「网格里存世界坐标、物体原点在原点」（见 precise_lib.mesh_from），
  所以 Object 空间 ≈ 世界空间；彩画用 Object X 的绝对米制模数分段，见 CAIHUA。
* view_transform = Standard：本机实测 AgX 会把宫墙红洗成粉色，Standard + 曝光 −0.2 才对。

彩画（和玺）几何约定
--------------------
额枋应当是一根**整盒子**（precise_lib.ring_beam 就是这样；beams() 是分段的，见报告）。
以 Object X=0 为枋心中心，按绝对米制往两端排：

    枋心 |x| < 1.30 | 金线 0.04 m | 藻头 1.34~2.30 | 金线 0.04 m | 箍头 2.34~PITCH/2

x 超过 PITCH/2 后按 PITCH 折返（三角形折），所以 90 m 长的阑额会得到一串对称的
彩画卷，而 6 m 的单根额枋正好一拍到底。改变 PITCH 即可对齐不同间宽。
"""

import json
import math
import os

import bpy
from mathutils import Vector

__all__ = [
    "MAT", "TILE_U", "TILE_V", "CAIHUA", "make_materials",
    "setup_world", "setup_sun", "setup_fill", "setup_render", "render",
    "review_settings", "project_uv_meters", "srgb",
]

# ============================================================== 常数 / 调色板

#: sRGB → 线性（下面调色板一律线性 RGB，Blender 的 default_value 就是线性）
def srgb(r, g=None, b=None):
    if g is None:
        r, g, b = (r, r, r) if isinstance(r, (int, float)) else r

    def f(c):
        c = c / 255.0 if c > 1.0 else c
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return (f(r), f(g), f(b))


#: 琉璃黄釉 —— 故宫黄琉璃：饱和、偏橙，不能是芥末黄
GLAZE_YELLOW = (0.480, 0.270, 0.010)
GLAZE_YELLOW_DARK = (0.300, 0.145, 0.006)
GLAZE_GREEN = (0.012, 0.135, 0.042)
ZHU_RED = (0.370, 0.044, 0.026)          # 朱红（柱）
ZHU_RED_WALL = (0.330, 0.038, 0.022)     # 宫墙，比柱略暗
BAI_YU = (0.600, 0.585, 0.525)           # 汉白玉
CAI_BLUE = (0.020, 0.088, 0.205)         # 石青
CAI_GREEN = (0.013, 0.130, 0.060)        # 石绿
GOLD_COL = (0.900, 0.585, 0.150)

#: 瓦垄几何：U 方向周期 = 垄距 0.32 m，V 方向 = 瓦长 0.30 m
TILE_U = 0.32
TILE_V = 0.30
TILE_TUBE = 0.30          # 筒瓦半宽 / 一垄（占 U 周期的比例）
TILE_BUMP = 0.0030        # 细部 Bump（米）：2~3 mm 的釉面细节
TILE_RIDGE = 0.050        # 筒瓦大起伏（米）：真实筒瓦凸起 4~6 cm，几何没有，只能假

#: 远距去摩尔纹：程序化凹凸没有 mipmap，60~200 m 会跳出雪花/绸纹
FADE_NEAR = 30.0          # 30 m 内凹凸全开
FADE_FAR = 150.0          # 150 m 外只剩 15%
FADE_FLOOR = 0.15

#: 和玺彩画模数（绝对米制，从 Object X=0 的枋心中心往两端排）
CAIHUA = dict(
    pitch=7.0,            # 折返周期（≈ 一间面阔）
    heart_half=1.30,      # 枋心半宽
    zhaotou_out=2.30,     # 藻头外沿
    gold=0.040,           # 分界金线宽
    gold_rough=0.22,
    paint_rough=0.46,
)

_DEFAULT_HDRIS = (
    "hdri_sky_sunny_2k.hdr",
    "hdri_sky_sunny.hdr",
    "hdri_sky_sunny_4k.hdr",
)

MAT = {}
_BUILT = False
_LAST_WORLD = {}          # setup_world 最近一次的返回，供 review_settings() 参考


# ============================================================== 节点小工具

def _is_sock(v):
    return isinstance(v, bpy.types.NodeSocket)


def _feed(g, sock, val):
    """把数值 / 元组 / 另一个 socket 接到 sock 上。"""
    if _is_sock(val):
        g.nt.links.new(val, sock)
        return
    if isinstance(val, (tuple, list)):
        if sock.type == "RGBA":
            v = tuple(val)
            sock.default_value = v if len(v) == 4 else (v[0], v[1], v[2], 1.0)
        elif sock.type == "VECTOR":
            sock.default_value = tuple(val)[:3]
        else:
            sock.default_value = float(val[0])
        return
    sock.default_value = float(val)


class Graph:
    """极薄的节点图 DSL：只管建节点、接线、返回 socket。"""

    def __init__(self, mat):
        mat.use_nodes = True
        self.mat = mat
        self.nt = mat.node_tree
        self.nt.nodes.clear()
        self.out = self.nt.nodes.new("ShaderNodeOutputMaterial")
        self.out.location = (980, 0)
        self.bsdf = self.nt.nodes.new("ShaderNodeBsdfPrincipled")
        self.bsdf.name = "Principled BSDF"      # 与 precise_lib._mat 的取用方式兼容
        self.bsdf.location = (700, 0)
        self.nt.links.new(self.bsdf.outputs["BSDF"], self.out.inputs["Surface"])

    def node(self, kind, loc=(0, 0), **props):
        n = self.nt.nodes.new(kind)
        n.location = loc
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def link(self, a, b):
        self.nt.links.new(a, b)

    def put(self, sock, val):
        _feed(self, sock, val)


def M(g, op, *args, clamp=False):
    n = g.node("ShaderNodeMath", operation=op, use_clamp=clamp)
    for i, v in enumerate(args[:3]):
        if v is not None:
            g.put(n.inputs[i], v)
    return n.outputs[0]





def MR(g, val, fmin, fmax, tmin=0.0, tmax=1.0, interp="LINEAR"):
    n = g.node("ShaderNodeMapRange", interpolation_type=interp)
    g.put(n.inputs["Value"], val)
    n.inputs["From Min"].default_value = fmin
    n.inputs["From Max"].default_value = fmax
    n.inputs["To Min"].default_value = tmin
    n.inputs["To Max"].default_value = tmax
    return n.outputs[0]


def STEP(g, val, lo=0.0, hi=1.0):
    """0→1 的平滑台阶（SMOOTHSTEP），用于所有分段界线。"""
    return MR(g, val, lo, hi, 0.0, 1.0, "SMOOTHSTEP")


def BAND(g, val, center, width):
    """|val-center| < width/2 → 1，边缘平滑（金线、瓦缝都用它）。"""
    d = M(g, "ABSOLUTE", M(g, "SUBTRACT", val, center))
    return M(g, "SUBTRACT", 1.0, STEP(g, d, width * 0.5, width * 0.5 + width * 0.35))


def NOISE(g, vec, scale=4.0, detail=6.0, rough=0.55, distortion=0.0, dims="3D"):
    n = g.node("ShaderNodeTexNoise", noise_dimensions=dims)
    g.put(n.inputs["Vector"], vec)
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough
    n.inputs["Distortion"].default_value = distortion
    return n.outputs["Factor"]


def VORONOI(g, vec, scale=3.0, feature="F1", metric="EUCLIDEAN"):
    n = g.node("ShaderNodeTexVoronoi", feature=feature, distance=metric)
    g.put(n.inputs["Vector"], vec)
    n.inputs["Scale"].default_value = scale
    return n.outputs["Distance"]


def MIXC(g, fac, c1, c2, blend="MIX", clamp=True):
    n = g.node("ShaderNodeMixRGB", blend_type=blend, use_clamp=clamp)
    g.put(n.inputs["Factor"], fac)
    g.put(n.inputs["Color1"], c1)
    g.put(n.inputs["Color2"], c2)
    return n.outputs["Color"]


def MIXF(g, fac, a, b):
    return M(g, "ADD", a, M(g, "MULTIPLY", M(g, "SUBTRACT", b, a), fac))


def BUMP(g, height, strength=0.6, distance=0.002, normal=None):
    n = g.node("ShaderNodeBump")
    g.put(n.inputs["Height"], height)
    g.put(n.inputs["Strength"], strength)
    g.put(n.inputs["Distance"], distance)
    if normal is not None:
        g.put(n.inputs["Normal"], normal)
    return n.outputs["Normal"]


def view_fade(g, near=FADE_NEAR, far=FADE_FAR, lo=FADE_FLOOR, hi=1.0):
    """按相机距离衰减的遮罩：near 内 1.0，far 外 lo。

    程序化凹凸没有 mipmap，远距离会闪雪花；把 Bump 强度和瓦缝对比乘上它就好。
    """
    cam = g.node("ShaderNodeCameraData")
    return MR(g, cam.outputs["View Distance"], near, far, hi, lo, "SMOOTHSTEP")


def AO(g, distance=0.35, samples=8, only_local=False, inside=False):
    n = g.node("ShaderNodeAmbientOcclusion", only_local=only_local, inside=inside,
               samples=samples)
    n.inputs["Distance"].default_value = distance
    return n.outputs["AO"]


def TEXCO(g):
    return g.node("ShaderNodeTexCoord")


def OBJ_XZ(g, tc):
    sep = g.node("ShaderNodeSeparateXYZ")
    g.link(tc.outputs["Object"], sep.inputs[0])
    return sep.outputs["X"], sep.outputs["Y"], sep.outputs["Z"]


# ---------------------------------------------------------------- 坐标 / 兜底

def surf_uv(g, tc=None):
    """返回 (u_m, v_m, use_uv)。

    u/v 单位米：有 UV 层时用 UV（本工程约定 UV 就是米：U 沿檐口、V 沿坡向）；
    没有 UV 层时 Cycles 的 UV 恒为 (0,0)，于是按世界法线做投影（U 沿檐向、V 沿坡向），
    仍是米制，图案连续。

    保险：物体自定义属性 ``lg_normalized_uv`` = 1 时强制走世界投影（给 UV 是 0~1
    归一化单位的旧网格用，见 tag_uv_units()）。不用量级猜测，因为量级猜测会在
    UV 原点附近切出一条横贯屋面的接缝。
    """
    tc = tc or TEXCO(g)
    sep = g.node("ShaderNodeSeparateXYZ")
    g.link(tc.outputs["UV"], sep.inputs[0])
    ux, uy = sep.outputs["X"], sep.outputs["Y"]
    has = M(g, "GREATER_THAN", M(g, "ADD", M(g, "ABSOLUTE", ux), M(g, "ABSOLUTE", uy)), 1e-3)
    tag = g.node("ShaderNodeAttribute", attribute_type="OBJECT",
                 attribute_name="lg_normalized_uv")
    forced = M(g, "GREATER_THAN", tag.outputs["Fac"], 0.5)
    use_uv = M(g, "MULTIPLY",
               M(g, "SUBTRACT", 1.0, forced), has)

    geo = g.node("ShaderNodeNewGeometry")
    s = g.node("ShaderNodeSeparateXYZ")
    g.link(geo.outputs["Normal"], s.inputs[0])
    nx = M(g, "ABSOLUTE", s.outputs["X"])
    ny = M(g, "ABSOLUTE", s.outputs["Y"])
    swap = M(g, "GREATER_THAN", nx, ny)          # 1 = 东西坡（脊线沿 Y）
    os_ = g.node("ShaderNodeSeparateXYZ")
    g.link(tc.outputs["Object"], os_.inputs[0])
    ox, oy = os_.outputs["X"], os_.outputs["Y"]
    u_fb = MIXF(g, swap, ox, oy)
    v_fb = MIXF(g, swap, oy, ox)
    u = MIXF(g, use_uv, u_fb, ux)
    v = MIXF(g, use_uv, v_fb, uy)
    return u, v, use_uv


def obj_coords(g, tc=None):
    tc = tc or TEXCO(g)
    return tc.outputs["Object"]


# ============================================================== 瓦作

def _tile_layers(g, u, v, pu=TILE_U, pv=TILE_V, tube=TILE_TUBE):
    """筒瓦圆弧 + 板瓦凹槽 + 瓦缝 + 每片瓦随机值。

    返回 (height, seam, rnd_value, rnd_color)：height 是 0..1 的凹凸场，seam 是瓦缝
    遮罩，rnd_* 是每片瓦的白噪声（±8% 明度/色相抖动用它们）。
    """
    su = M(g, "FRACT", M(g, "DIVIDE", u, pu))
    dd = M(g, "ABSOLUTE", M(g, "SUBTRACT", su, 0.5))       # 0 = 筒瓦正中
    t = M(g, "MINIMUM", M(g, "DIVIDE", dd, tube), 1.0)
    arc = M(g, "SQRT", M(g, "MAXIMUM", M(g, "SUBTRACT", 1.0, M(g, "MULTIPLY", t, t)), 0.0))
    p = M(g, "MAXIMUM", M(g, "SUBTRACT", M(g, "DIVIDE", dd, tube), 1.0), 0.0)
    pan = M(g, "MULTIPLY", p, -0.16)                        # 板瓦微凹
    sv = M(g, "FRACT", M(g, "DIVIDE", v, pv))
    sv_min = M(g, "MINIMUM", sv, M(g, "SUBTRACT", 1.0, sv))
    seam_v = M(g, "SUBTRACT", 1.0, STEP(g, sv_min, 0.010, 0.036))
    seam_u = M(g, "SUBTRACT", 1.0,
               STEP(g, M(g, "ABSOLUTE", M(g, "SUBTRACT", dd, tube)), 0.006, 0.022))
    seam = M(g, "MAXIMUM", seam_v, seam_u)
    height = M(g, "SUBTRACT", M(g, "ADD", M(g, "MULTIPLY", arc, 1.0), pan),
               M(g, "MULTIPLY", seam, 0.16))
    idx = g.node("ShaderNodeCombineXYZ")
    g.link(M(g, "FLOOR", M(g, "DIVIDE", u, pu)), idx.inputs[0])
    g.link(M(g, "FLOOR", M(g, "DIVIDE", v, pv)), idx.inputs[1])
    wn = g.node("ShaderNodeTexWhiteNoise", noise_dimensions="3D")
    g.link(idx.outputs[0], wn.inputs["Vector"])
    # Value 给明度、Color.r 给色相，两个随机都来自同一片瓦的索引
    return height, seam, wn.outputs["Value"], wn.outputs["Color"], arc


def _glaze_tile(g, base, dark, r_lo=0.28, r_hi=0.42, coat=0.12, bump=TILE_BUMP,
                dirt=0.55, pu=TILE_U, pv=TILE_V):
    """琉璃瓦（tile / tile2 / glazed_green 共用）。"""
    tc = TEXCO(g)
    u, v, _ = surf_uv(g, tc)
    obj = tc.outputs["Object"]
    height, seam, rnd_v, rnd_c, arc = _tile_layers(g, u, v, pu, pv)
    warm = MIXC(g, 1.0, base, (1.10, 0.92, 0.86), "MULTIPLY")   # 偏橙的同类釉色
    # 每片瓦：明度 ±8%，色相往暖/冷各偏一点
    tone = MIXC(g, M(g, "MULTIPLY", rnd_c, 0.55), base, warm)
    var = M(g, "MULTIPLY_ADD", rnd_v, 0.10, 0.95)
    col = MIXC(g, 1.0, tone, var, "MULTIPLY")
    col = MIXC(g, M(g, "MULTIPLY", M(g, "SUBTRACT", 1.0, rnd_c), 0.08), col, dark)
    fade = view_fade(g)
    # 筒瓦的圆背在真几何里没有：用凹凸 + 一道随弧高变化的明暗把它"画"出来
    shade = MR(g, height, -0.18, 1.0, 0.85, 1.12, "SMOOTHSTEP")
    shade = M(g, "MULTIPLY_ADD", M(g, "SUBTRACT", shade, 1.0), fade, 1.0)
    col = MIXC(g, 1.0, col, shade, "MULTIPLY")
    # 大尺度风化：十几米一档的明度起伏。每片瓦的随机只到 0.5 m 尺度，
    # 两百米外全被平均成一块"塑料金"，得靠低频把成片的深浅做出来。
    big = NOISE(g, obj, scale=0.055, detail=3.0, rough=0.5, distortion=0.12)
    col = MIXC(g, M(g, "MULTIPLY", STEP(g, big, 0.34, 0.70), 0.42), col,
               MIXC(g, 1.0, col, (0.58, 0.55, 0.50), "MULTIPLY"), "MIX")
    # 更大一档（70 m 上下）：整坡替换过的瓦色差，鸟瞰里才不会所有屋顶一个色
    huge = NOISE(g, obj, scale=0.0135, detail=2.0, rough=0.45, distortion=0.08)
    col = MIXC(g, M(g, "MULTIPLY", STEP(g, huge, 0.36, 0.72), 0.40), col,
               MIXC(g, 1.0, col, (0.80, 0.77, 0.72), "MULTIPLY"), "MIX")
    # 瓦缝：深色 + 高粗糙；远距离把对比压下去，免得整片屋面条纹闪烁
    seam_c = M(g, "MULTIPLY", seam, M(g, "MULTIPLY_ADD", fade, 0.42, 0.05))
    col = MIXC(g, seam_c, col, (0.075, 0.068, 0.055), "MULTIPLY")
    # 极淡的灰污（避免"全新塑料"）：低频噪声 + AO，都压在 10% 以内
    grime_n = NOISE(g, obj, scale=2.2, detail=8.0, rough=0.62, distortion=0.4)
    gr = M(g, "MULTIPLY", STEP(g, grime_n, 0.42, 0.78), 0.10)
    ao = AO(g, distance=0.30, samples=8)
    gr = M(g, "ADD", gr, M(g, "MULTIPLY", M(g, "SUBTRACT", 1.0, ao), 0.20 * dirt))
    col = MIXC(g, M(g, "MULTIPLY", gr, M(g, "SUBTRACT", 1.0, M(g, "MULTIPLY", seam, 0.4))),
               col, (0.140, 0.125, 0.100))
    # 粗糙度 0.28~0.42，瓦缝抬到 0.7
    rn = NOISE(g, obj, scale=7.0, detail=5.0, rough=0.5)
    rough = M(g, "ADD", M(g, "MULTIPLY_ADD", rn, r_hi - r_lo, r_lo),
              M(g, "MULTIPLY", seam, M(g, "MULTIPLY", fade, 0.30)))
    fine = NOISE(g, obj, scale=48.0, detail=4.0, rough=0.5)
    n_fine = BUMP(g, fine, strength=M(g, "MULTIPLY", fade, 0.60),  # 釉面 2~3 mm
                  distance=bump)
    n_ridge = BUMP(g, height,                                       # 筒瓦起伏（假的）
                   strength=M(g, "MULTIPLY", fade, 0.95),
                   distance=TILE_RIDGE, normal=n_fine)
    g.put(g.bsdf.inputs["Base Color"], col)
    g.put(g.bsdf.inputs["Roughness"], rough)
    g.bsdf.inputs["Metallic"].default_value = 0.0
    g.bsdf.inputs["Specular IOR Level"].default_value = 0.55
    g.bsdf.inputs["Coat Weight"].default_value = coat
    g.bsdf.inputs["Coat Roughness"].default_value = 0.06
    g.put(g.bsdf.inputs["Normal"], n_ridge)


def _gray_tile(g):
    """青瓦：暗灰、很哑、苔藓与灰尘用噪波混入，复用同一套瓦垄几何。"""
    tc = TEXCO(g)
    u, v, _ = surf_uv(g, tc)
    obj = tc.outputs["Object"]
    height, seam, rnd_v, rnd_c, arc = _tile_layers(g, u, v, 0.24, 0.22)
    base = (0.030, 0.034, 0.036)
    var = M(g, "MULTIPLY_ADD", rnd_v, 0.16, 0.90)
    col = MIXC(g, 1.0, base, var, "MULTIPLY")
    fade = view_fade(g, lo=0.20)
    shade = MR(g, height, -0.18, 1.0, 0.80, 1.15, "SMOOTHSTEP")
    col = MIXC(g, 1.0, col, M(g, "MULTIPLY_ADD", M(g, "SUBTRACT", shade, 1.0), fade, 1.0),
               "MULTIPLY")
    moss = STEP(g, NOISE(g, obj, scale=1.6, detail=8.0, rough=0.66, distortion=0.5),
                0.46, 0.78)
    dust = STEP(g, NOISE(g, obj, scale=5.0, detail=6.0, rough=0.6), 0.42, 0.72)
    col = MIXC(g, M(g, "MULTIPLY", moss, 0.55), col, (0.045, 0.075, 0.035))
    col = MIXC(g, M(g, "MULTIPLY", dust, 0.40), col, (0.115, 0.110, 0.098))
    col = MIXC(g, M(g, "MULTIPLY", seam, 0.6), col, (0.030, 0.030, 0.030), "MULTIPLY")
    ao = AO(g, distance=0.25, samples=6)
    col = MIXC(g, M(g, "MULTIPLY", M(g, "SUBTRACT", 1.0, ao), 0.45), col, (0.020, 0.022, 0.021))
    rough = M(g, "ADD", 0.72, M(g, "MULTIPLY", seam, M(g, "MULTIPLY", fade, 0.18)))
    g.put(g.bsdf.inputs["Base Color"], col)
    g.put(g.bsdf.inputs["Roughness"], rough)
    g.bsdf.inputs["Specular IOR Level"].default_value = 0.30
    g.put(g.bsdf.inputs["Normal"],
          BUMP(g, height, strength=M(g, "MULTIPLY", fade, 0.85),
               distance=TILE_RIDGE * 0.75))


# ============================================================== 石作

def _marble(g, base=BAI_YU, veins=0.85, bump=0.0005, carve=False):
    """汉白玉 / 雕花汉白玉：低频噪声 + Voronoi 纹，侧面积灰比顶面重。"""
    tc = TEXCO(g)
    obj = tc.outputs["Object"]
    n1 = NOISE(g, obj, scale=1.6, detail=10.0, rough=0.62, distortion=0.55)
    n2 = NOISE(g, obj, scale=6.5, detail=8.0, rough=0.55, distortion=0.25)
    # 石纹：高度扭曲的细噪声线，比 Voronoi 细胞更接近真实大理石脉络
    mp = g.node("ShaderNodeMapping")
    g.link(obj, mp.inputs["Vector"])
    mp.inputs["Scale"].default_value = (1.0, 1.5, 0.75)
    nva = NOISE(g, mp.outputs["Vector"], scale=1.5, detail=12.0, rough=0.72, distortion=2.4)
    nvb = NOISE(g, obj, scale=4.6, detail=10.0, rough=0.68, distortion=1.7)
    vein = M(g, "MAXIMUM",
             M(g, "SUBTRACT", 1.0, STEP(g, M(g, "ABSOLUTE", M(g, "SUBTRACT", nva, 0.5)),
                                        0.004, 0.026)),
             M(g, "MULTIPLY",
               M(g, "SUBTRACT", 1.0, STEP(g, M(g, "ABSOLUTE", M(g, "SUBTRACT", nvb, 0.5)),
                                          0.003, 0.020)), 0.55))
    grain = M(g, "MULTIPLY_ADD", n2, 0.55, 0.22)
    col = MIXC(g, 1.0, base, (1.10, 1.06, 0.98), "MULTIPLY")   # 微暖高光面
    col = MIXC(g, M(g, "MULTIPLY", grain, 0.50), col, MIXC(g, 1.0, base, (0.86, 0.855, 0.84), "MULTIPLY"),
               "MIX")
    col = MIXC(g, M(g, "MULTIPLY", vein, 0.50 * veins), col, (0.345, 0.340, 0.318))
    # 侧面积灰 > 顶面积灰
    geo = g.node("ShaderNodeNewGeometry")
    sn = g.node("ShaderNodeSeparateXYZ")
    g.link(geo.outputs["Normal"], sn.inputs[0])
    side = M(g, "SUBTRACT", 1.0, M(g, "MAXIMUM", sn.outputs["Z"], 0.0))
    ao = AO(g, distance=0.45, samples=8)
    dirt = M(g, "ADD", M(g, "MULTIPLY", M(g, "SUBTRACT", 1.0, ao), 0.55),
             M(g, "MULTIPLY", side, 0.30))
    col = MIXC(g, M(g, "MULTIPLY", dirt, 0.55), col, (0.235, 0.225, 0.195))
    # 台面积垢：水平面按十几米一档的噪声压暗压黄（三台两百多米的台面不能是一张白纸）
    _wear = NOISE(g, obj, scale=0.062, detail=5.0, rough=0.55, distortion=0.3)
    _top = M(g, "MAXIMUM", M(g, "SUBTRACT", 1.0, side), 0.0)
    _wf = M(g, "MULTIPLY", _top, M(g, "MULTIPLY", STEP(g, _wear, 0.34, 0.74), 0.62))
    col = MIXC(g, _wf, col, (0.68, 0.655, 0.60), "MULTIPLY")
    # 大尺度色差：3~20 m 一档，远看（八米高台、两百米外）才有东西
    big = NOISE(g, obj, scale=0.11, detail=4.0, rough=0.5, distortion=0.2)
    col = MIXC(g, M(g, "MULTIPLY", STEP(g, big, 0.42, 0.72), 0.55), col,
               MIXC(g, 1.0, base, (0.80, 0.79, 0.76), "MULTIPLY"), "MIX")
    # 石活拼缝：横向面按 (x,y)、竖向面按 (x+y, z)，用 |nz| 混合——三台顶面也要有缝
    osp = g.node("ShaderNodeSeparateXYZ")
    g.link(obj, osp.inputs[0])

    def _brick(vec):
        b = g.node("ShaderNodeTexBrick")
        b.offset = 0.5
        b.squash = 1.0
        b.inputs["Scale"].default_value = 1.0
        b.inputs["Brick Width"].default_value = 1.20
        b.inputs["Row Height"].default_value = 0.60
        b.inputs["Mortar Size"].default_value = 0.014
        b.inputs["Mortar Smooth"].default_value = 0.3
        b.inputs["Color1"].default_value = (1, 1, 1, 1)
        b.inputs["Color2"].default_value = (0.9, 0.9, 0.9, 1)
        b.inputs["Mortar"].default_value = (0, 0, 0, 1)
        g.link(vec, b.inputs["Vector"])
        return b

    _c_h = g.node("ShaderNodeCombineXYZ")
    g.link(osp.outputs["X"], _c_h.inputs["X"])
    g.link(osp.outputs["Y"], _c_h.inputs["Y"])
    _c_v = g.node("ShaderNodeCombineXYZ")
    g.link(M(g, "ADD", osp.outputs["X"], osp.outputs["Y"]), _c_v.inputs["X"])
    g.link(osp.outputs["Z"], _c_v.inputs["Y"])
    br_h, br_v = _brick(_c_h.outputs[0]), _brick(_c_v.outputs[0])
    nz = M(g, "ABSOLUTE", sn.outputs["Z"])
    seam = M(g, "ADD", M(g, "MULTIPLY", br_h.outputs["Fac"], nz),
             M(g, "MULTIPLY", br_v.outputs["Fac"], M(g, "SUBTRACT", 1.0, nz)))
    col = MIXC(g, M(g, "MULTIPLY", seam, 0.30), col, (0.30, 0.29, 0.27), "MULTIPLY")
    rough = M(g, "MULTIPLY_ADD", NOISE(g, obj, 3.2, 6.0, 0.55),
              0.10, 0.34 if not carve else 0.40)
    g.put(g.bsdf.inputs["Base Color"], col)
    g.put(g.bsdf.inputs["Roughness"], rough)
    g.bsdf.inputs["Specular IOR Level"].default_value = 0.42
    h = M(g, "ADD", M(g, "ADD", M(g, "MULTIPLY", n2, 0.35),
                      M(g, "MULTIPLY", vein, 0.45)),
          M(g, "MULTIPLY", seam, -0.55))
    g.put(g.bsdf.inputs["Normal"], BUMP(g, h, strength=0.45 if not carve else 0.85,
                                        distance=bump if not carve else bump * 2.2))


def _stone(g, base, dirt=0.45, rough_lo=0.42, rough_hi=0.62):
    """石阶 / 台基石：比汉白玉粗、更脏。"""
    tc = TEXCO(g)
    obj = tc.outputs["Object"]
    n1 = NOISE(g, obj, scale=2.4, detail=9.0, rough=0.65, distortion=0.45)
    n2 = NOISE(g, obj, scale=14.0, detail=7.0, rough=0.6)
    vor = VORONOI(g, obj, scale=14.0, feature="DISTANCE_TO_EDGE")
    col = MIXC(g, 1.0, base, M(g, "MULTIPLY_ADD", n1, 0.42, 0.78), "MULTIPLY")
    crev = M(g, "SUBTRACT", 1.0, STEP(g, vor, 0.004, 0.022))
    col = MIXC(g, M(g, "MULTIPLY", crev, 0.22), col, (0.20, 0.195, 0.175))
    ao = AO(g, distance=0.40, samples=8)
    gr = M(g, "ADD", M(g, "MULTIPLY", M(g, "SUBTRACT", 1.0, ao), 0.7),
           M(g, "MULTIPLY", n2, 0.25))
    col = MIXC(g, M(g, "MULTIPLY", gr, dirt), col, (0.115, 0.110, 0.092))
    rough = M(g, "MULTIPLY_ADD", n2, rough_hi - rough_lo, rough_lo)
    g.put(g.bsdf.inputs["Base Color"], col)
    g.put(g.bsdf.inputs["Roughness"], rough)
    g.bsdf.inputs["Specular IOR Level"].default_value = 0.35
    g.put(g.bsdf.inputs["Normal"], BUMP(g, M(g, "ADD", n2, M(g, "MULTIPLY", n1, 0.5)),
                                        strength=0.5, distance=0.0012))


# ============================================================== 木作 / 油作

def _wood(g, base, rough=0.52, grain=0.16, coat=0.10):
    """木纹沿 Z 拉长（柱、墙、板都用它）。"""
    tc = TEXCO(g)
    mp = g.node("ShaderNodeMapping")
    g.link(tc.outputs["Object"], mp.inputs["Vector"])
    mp.inputs["Scale"].default_value = (3.0, 3.0, 0.35)      # Z 方向拉长 → 顺纹
    mp.inputs["Rotation"].default_value = (0.0, 0.0, 0.0)
    n = NOISE(g, mp.outputs["Vector"], scale=5.0, detail=9.0, rough=0.62, distortion=1.4)
    rings = M(g, "SINE", M(g, "MULTIPLY", n, 42.0))
    gr = M(g, "MULTIPLY_ADD", rings, 0.5, 0.5)                # 0..1 木纹场（粗）
    fine = NOISE(g, mp.outputs["Vector"], scale=46.0, detail=6.0, rough=0.6)
    gr = M(g, "ADD", M(g, "MULTIPLY", gr, 0.74), M(g, "MULTIPLY", fine, 0.26))
    fmul = M(g, "MULTIPLY_ADD", gr, 2.0 * grain, 1.0 - grain)  # 1-grain .. 1+grain
    col = MIXC(g, 1.0, base, fmul, "MULTIPLY")
    # 雨痕：竖向拉长的噪声（柱、墙常年淋雨，纯色面最"塑料"）
    mp2 = g.node("ShaderNodeMapping")
    g.link(tc.outputs["Object"], mp2.inputs["Vector"])
    mp2.inputs["Scale"].default_value = (7.5, 7.5, 0.42)
    st = NOISE(g, mp2.outputs["Vector"], scale=2.2, detail=7.0, rough=0.58,
               distortion=0.25)
    col = MIXC(g, 1.0, col, M(g, "MULTIPLY_ADD", st, 0.22, 0.89), "MULTIPLY")
    # 墙脚积灰：地面往上 1.7 m 内压暗压脏（object 坐标 z 即离地高度）
    osp2 = g.node("ShaderNodeSeparateXYZ")
    g.link(tc.outputs["Object"], osp2.inputs[0])
    foot = M(g, "SUBTRACT", 1.0, STEP(g, osp2.outputs["Z"], 0.2, 1.7))
    col = MIXC(g, M(g, "MULTIPLY", foot, 0.50), col, (0.42, 0.37, 0.32), "MULTIPLY")
    g.put(g.bsdf.inputs["Base Color"], col)
    rn = NOISE(g, mp.outputs["Vector"], scale=2.0, detail=6.0)
    g.put(g.bsdf.inputs["Roughness"], M(g, "MULTIPLY_ADD", rn, 0.10, rough))
    g.bsdf.inputs["Specular IOR Level"].default_value = 0.45
    g.bsdf.inputs["Coat Weight"].default_value = coat
    g.bsdf.inputs["Coat Roughness"].default_value = 0.12
    g.put(g.bsdf.inputs["Normal"], BUMP(g, gr, strength=0.18, distance=0.0004))


def _paint(g, base, rough=(0.45, 0.56), coat=0.10, grime=0.25, grain=0.0):
    """红漆 / 彩画实色：轻微噪声起伏 + 极淡积灰。"""
    tc = TEXCO(g)
    obj = tc.outputs["Object"]
    rn = NOISE(g, obj, scale=3.4, detail=6.0, rough=0.5, distortion=0.2)
    col = base
    if grain > 0:
        mp = g.node("ShaderNodeMapping")
        g.link(obj, mp.inputs["Vector"])
        mp.inputs["Scale"].default_value = (2.0, 2.0, 0.30)
        gn = NOISE(g, mp.outputs["Vector"], scale=6.0, detail=8.0, rough=0.6, distortion=1.2)
        col = MIXC(g, 1.0, base,
                   M(g, "MULTIPLY_ADD", gn, grain * 2.0, 1.0 - grain), "MULTIPLY")
    col = MIXC(g, M(g, "MULTIPLY", rn, 0.10), col, (0.0, 0.0, 0.0), "MIX")
    ao = AO(g, distance=0.30, samples=6)
    col = MIXC(g, M(g, "MULTIPLY", M(g, "SUBTRACT", 1.0, ao), grime), col,
               (0.055, 0.045, 0.038))
    g.put(g.bsdf.inputs["Base Color"], col)
    g.put(g.bsdf.inputs["Roughness"], M(g, "MULTIPLY_ADD", rn, rough[1] - rough[0], rough[0]))
    g.bsdf.inputs["Specular IOR Level"].default_value = 0.5
    g.bsdf.inputs["Coat Weight"].default_value = coat
    g.bsdf.inputs["Coat Roughness"].default_value = 0.10
    g.put(g.bsdf.inputs["Normal"], BUMP(g, rn, strength=0.10, distance=0.0003))


# ============================================================== 和玺彩画

def _glaze_plain(g, base, dark, rough=(0.26, 0.38), grime=0.55, coat=0.12):
    """无花纹琉璃釉：正脊 / 垂脊 / 鸱吻 / 当沟 / 瓦当这些没有 UV 的瓦件用它。

    关键是**一点周期性条纹都没有**：只有釉面细颗粒、按 0.30 m 网格的 ±6% 明度抖动、
    AO 积灰。吃 tile 的瓦垄图案会渲成一道道竖条，很假，所以单独给一件。
    """
    tc = TEXCO(g)
    obj = tc.outputs["Object"]
    idx = g.node("ShaderNodeCombineXYZ")
    for axis, comp in enumerate(("X", "Y", "Z")):
        sp = g.node("ShaderNodeSeparateXYZ")
        g.link(obj, sp.inputs[0])
        g.link(M(g, "FLOOR", M(g, "DIVIDE", sp.outputs[comp], 0.30)), idx.inputs[axis])
    wn = g.node("ShaderNodeTexWhiteNoise", noise_dimensions="3D")
    g.link(idx.outputs[0], wn.inputs["Vector"])
    var = M(g, "MULTIPLY_ADD", wn.outputs["Value"], 0.12, 0.94)       # ±6%
    col = MIXC(g, 1.0, base, var, "MULTIPLY")
    col = MIXC(g, M(g, "MULTIPLY", wn.outputs["Color"], 0.10), col, dark)
    gr = STEP(g, NOISE(g, obj, 1.8, 8.0, 0.6, distortion=0.4), 0.42, 0.78)
    ao = AO(g, distance=0.30, samples=8)
    gr = M(g, "ADD", M(g, "MULTIPLY", gr, 0.16),
           M(g, "MULTIPLY", M(g, "SUBTRACT", 1.0, ao), 0.30 * grime))
    col = MIXC(g, M(g, "MULTIPLY", gr, 0.55), col, (0.135, 0.120, 0.098))
    rn = NOISE(g, obj, 5.0, 6.0, 0.55)
    g.put(g.bsdf.inputs["Base Color"], col)
    g.put(g.bsdf.inputs["Roughness"],
          M(g, "ADD", M(g, "MULTIPLY_ADD", rn, rough[1] - rough[0], rough[0]),
            M(g, "MULTIPLY", gr, 0.14)))
    g.bsdf.inputs["Specular IOR Level"].default_value = 0.55
    g.bsdf.inputs["Coat Weight"].default_value = coat
    g.bsdf.inputs["Coat Roughness"].default_value = 0.06
    fade = view_fade(g)
    g.put(g.bsdf.inputs["Normal"],
          BUMP(g, NOISE(g, obj, 40.0, 4.0, 0.5),
               strength=M(g, "MULTIPLY", fade, 0.55), distance=TILE_BUMP))


def _caihua_finish(g, col, gold, tc=None):
    """和玺彩画共用收尾：贴金、旧化、粗糙度 / 金属度 / 凹凸。"""
    P = CAIHUA
    col = MIXC(g, gold, col, GOLD_COL)
    # 旧化：极淡积灰 + 檐下 AO
    ao = AO(g, distance=0.35, samples=8)
    gr = M(g, "ADD", M(g, "MULTIPLY", M(g, "SUBTRACT", 1.0, ao), 0.35),
           M(g, "MULTIPLY", NOISE(g, (tc or TEXCO(g)).outputs["Object"], 2.0, 8.0, 0.6),
                     0.16))
    col = MIXC(g, M(g, "MULTIPLY", gr, 0.55), col, (0.075, 0.070, 0.058))
    rough = MIXF(g, gold, P["paint_rough"], P["gold_rough"])
    rough = M(g, "ADD", rough, M(g, "MULTIPLY", gr, 0.12))
    g.put(g.bsdf.inputs["Base Color"], col)
    g.put(g.bsdf.inputs["Roughness"], rough)
    g.link(gold, g.bsdf.inputs["Metallic"])
    g.bsdf.inputs["Specular IOR Level"].default_value = 0.5
    g.put(g.bsdf.inputs["Normal"], BUMP(g, M(g, "SUBTRACT", 1.0, gold),
                                       strength=0.20, distance=0.0009))


def _caihua(g, heart, zhaotou, kuto):
    """和玺彩画（Object X 版）：绝对米制分段，适合没有 UV 的整根额枋。

    枋心（青地金龙感）| 金线 | 藻头（另一色 + 旋子点）| 金线 | 箍头（实色）
    x 超过 pitch/2 后三角形折返，长阑额得到一串对称彩画卷。
    额枋有 UV（U 沿长度 0..1）时优先用 `caihua_uv_*`，能自适应不同间宽。
    """
    P = CAIHUA
    tc = TEXCO(g)
    ox, oy, oz = OBJ_XZ(g, tc)
    # q = |mod(x + P/2, P) - P/2|：0 在枋心正中，P/2 在折返处
    t = M(g, "FLOORED_MODULO", M(g, "ADD", ox, P["pitch"] * 0.5), P["pitch"])
    q = M(g, "ABSOLUTE", M(g, "SUBTRACT", t, P["pitch"] * 0.5))

    gw = P["gold"]
    g1 = BAND(g, q, P["heart_half"] + gw * 0.5, gw)        # 枋心 / 藻头 之间
    g2 = BAND(g, q, P["zhaotou_out"] + gw * 0.5, gw)        # 藻头 / 箍头 之间
    gold_line = M(g, "MAXIMUM", g1, g2)

    in_heart = M(g, "SUBTRACT", 1.0, STEP(g, q, P["heart_half"] - gw * 0.5,
                                          P["heart_half"] + gw * 0.5))
    in_zhao = M(g, "MINIMUM",
                STEP(g, q, P["heart_half"] + gw * 0.5, P["heart_half"] + gw * 1.6),
                M(g, "SUBTRACT", 1.0, STEP(g, q, P["zhaotou_out"] - gw * 0.5,
                                           P["zhaotou_out"] + gw * 0.5)))
    # 底色：箍头打底，再盖藻头，再盖枋心（三段互斥）
    col = MIXC(g, in_zhao, kuto, zhaotou)
    col = MIXC(g, in_heart, col, heart)

    # 枋心：内嵌深色框 + 细金线卷草（不画龙）
    inner = M(g, "SUBTRACT", 1.0, STEP(g, q, P["heart_half"] - 0.16,
                                       P["heart_half"] - 0.10))
    col = MIXC(g, M(g, "MULTIPLY", inner, 0.55),
               col, MIXC(g, 1.0, heart, (0.55, 0.58, 0.62), "MULTIPLY"))
    # 卷草金线：z 方向周期 + x 正弦摆动
    zz = M(g, "FRACT", M(g, "DIVIDE", oz, 0.22))
    wob = M(g, "MULTIPLY_ADD", M(g, "SINE", M(g, "MULTIPLY", ox, 2.6)), 0.16, 0.5)
    orn = BAND(g, M(g, "ABSOLUTE", M(g, "SUBTRACT", zz, wob)), 0.0, 0.10)
    orn = M(g, "MULTIPLY", orn, in_heart)
    # 藻头：旋子（金点）
    dx = M(g, "ABSOLUTE", M(g, "SUBTRACT", M(g, "FRACT", M(g, "DIVIDE", ox, 0.46)), 0.5))
    dz = M(g, "ABSOLUTE", M(g, "SUBTRACT", M(g, "FRACT", M(g, "DIVIDE", oz, 0.26)), 0.5))
    rr = M(g, "SQRT", M(g, "ADD", M(g, "MULTIPLY", dx, dx), M(g, "MULTIPLY", dz, dz)))
    dots = M(g, "MULTIPLY", M(g, "SUBTRACT", 1.0, STEP(g, rr, 0.10, 0.16)), in_zhao)
    gold = M(g, "MAXIMUM", gold_line, M(g, "MAXIMUM", M(g, "MULTIPLY", orn, 0.85),
                                       M(g, "MULTIPLY", dots, 0.75)))
    _caihua_finish(g, col, gold, tc)


def _caihua_uv(g, heart, zhaotou, kuto, edge_v=0.12, kuto_u=0.07, gline=0.006):
    """和玺彩画（UV 版）：U 沿构件长度 0..1、V 沿高度 0..1，自适应每间宽度。

    分段（U）：箍头 <0.07 与 >0.93 → 金线 0.006 → 藻头 0.07~0.26 → 枋心 0.26~0.74 …
    横向（V）：上下 edge_v 为压边（压一档深色 + 上下金线），彩画上下本来就有箍头线。
    """
    tc = TEXCO(g)
    sep = g.node("ShaderNodeSeparateXYZ")
    g.link(tc.outputs["UV"], sep.inputs[0])
    u, v = sep.outputs["X"], sep.outputs["Y"]

    # ---- U 方向三段
    in_kuto = M(g, "MAXIMUM",
                M(g, "SUBTRACT", 1.0, STEP(g, u, kuto_u - gline, kuto_u + gline * 1.5)),
                STEP(g, u, 1.0 - kuto_u - gline * 1.5, 1.0 - kuto_u + gline))
    in_zhao_l = M(g, "MULTIPLY",
                  STEP(g, u, kuto_u - gline, kuto_u + gline * 1.5),
                  M(g, "SUBTRACT", 1.0, STEP(g, u, 0.254, 0.266)))
    in_zhao_r = M(g, "MULTIPLY",
                  STEP(g, u, 0.734, 0.746),
                  M(g, "SUBTRACT", 1.0, STEP(g, u, 1.0 - kuto_u - gline * 1.5,
                                             1.0 - kuto_u + gline)))
    in_zhao = M(g, "MAXIMUM", in_zhao_l, in_zhao_r)
    in_heart = M(g, "SUBTRACT", 1.0, M(g, "MINIMUM", M(g, "ADD", in_kuto, in_zhao), 1.0))

    gold_line = M(g, "MAXIMUM",
                  M(g, "MAXIMUM", BAND(g, u, kuto_u, gline * 2.0),
                    BAND(g, u, 1.0 - kuto_u, gline * 2.0)),
                  M(g, "MAXIMUM", BAND(g, u, 0.07, gline * 2.0),
                    BAND(g, u, 0.93, gline * 2.0)))

    col = MIXC(g, in_zhao, kuto, zhaotou)
    col = MIXC(g, in_heart, col, heart)

    # 枋心内嵌深色框（青地金龙感）：中间 0.30~0.70 × 0.20~0.80 压一档
    inner_u = M(g, "MULTIPLY", STEP(g, u, 0.28, 0.30),
                M(g, "SUBTRACT", 1.0, STEP(g, u, 0.70, 0.72)))
    inner_v = M(g, "MULTIPLY", STEP(g, v, 0.18, 0.20),
                M(g, "SUBTRACT", 1.0, STEP(g, v, 0.80, 0.82)))
    inner = M(g, "MULTIPLY", M(g, "MULTIPLY", inner_u, inner_v), in_heart)
    col = MIXC(g, M(g, "MULTIPLY", inner, 0.45), col,
               MIXC(g, 1.0, heart, (0.62, 0.62, 0.62), "MULTIPLY"))

    # ---- V 方向压边（上下 12%）
    v_edge = M(g, "MAXIMUM",
               M(g, "SUBTRACT", 1.0, STEP(g, v, edge_v - 0.012, edge_v + 0.012)),
               STEP(g, v, 1.0 - edge_v - 0.012, 1.0 - edge_v + 0.012))
    v_gold = M(g, "MAXIMUM", BAND(g, v, edge_v, 0.012), BAND(g, v, 1.0 - edge_v, 0.012))
    col = MIXC(g, M(g, "MULTIPLY", v_edge, 0.75), col,
               MIXC(g, 1.0, kuto, (0.62, 0.62, 0.62), "MULTIPLY"))

    # ---- 枋心云纹（很淡的一条波形带，压在龙身下面当底色层次）
    ux = M(g, "MULTIPLY", u, 8.0)
    vz = M(g, "MULTIPLY", v, 0.85)
    zz = M(g, "FRACT", M(g, "DIVIDE", vz, 0.22))
    wob = M(g, "MULTIPLY_ADD", M(g, "SINE", M(g, "MULTIPLY", ux, 2.6)), 0.16, 0.5)
    orn = BAND(g, M(g, "ABSOLUTE", M(g, "SUBTRACT", zz, wob)), 0.0, 0.10)
    orn = M(g, "MULTIPLY", orn, in_heart)
    # ---- 藻头旋子（清式「一整二破」）：藻头内一个整圆 + 两端各半个圆
    # 沿枋长：左右两个藻头的中心分别落在 u 轴向两侧 2.704 m 处（8 m 开间折算），
    # 藻头宽 1.472 m；把 |du| 折回藻头局部坐标后，圆心在局部 0 与 ±1（±1 就是半个）。
    du_m = M(g, "SUBTRACT", ux, 4.0)
    pu = M(g, "DIVIDE", M(g, "SUBTRACT", M(g, "ABSOLUTE", du_m), 2.704), 1.472)
    cu = M(g, "ABSOLUTE", M(g, "SUBTRACT", M(g, "FRACT", M(g, "ADD", pu, 0.5)), 0.5))
    dxm = M(g, "MULTIPLY", cu, 1.472)
    dzm = M(g, "MULTIPLY", M(g, "SUBTRACT", v, 0.5), 0.85)
    rr = M(g, "SQRT", M(g, "ADD", M(g, "MULTIPLY", dxm, dxm),
                       M(g, "MULTIPLY", dzm, dzm)))
    rim = BAND(g, rr, 0.300, 0.012)          # 外缘金圈（旋子轮廓）
    ring2 = BAND(g, rr, 0.212, 0.010)        # 道瓣圈
    ring3 = BAND(g, rr, 0.132, 0.009)        # 内瓣圈
    core = M(g, "SUBTRACT", 1.0, STEP(g, rr, 0.048, 0.062))   # 花心
    swirl = M(g, "MAXIMUM", M(g, "MAXIMUM", rim, ring2),
              M(g, "MAXIMUM", ring3, core))
    dots = M(g, "MULTIPLY", swirl, in_zhao)
    # ---- 枋心金龙（写意）：细身 S 形 + 头 + 四爪 + 尾叉，只落在枋心范围内。
    # 和玺彩画的枋心本来就是「青地金龙」；先前那条金带太粗，读成一条缎子。
    uu = M(g, "MULTIPLY", M(g, "SUBTRACT", u, 0.26), 1.0 / 0.48)
    vv = M(g, "MULTIPLY", M(g, "SUBTRACT", v, 0.18), 1.0 / 0.64)
    sp = M(g, "MULTIPLY_ADD", M(g, "SINE", M(g, "MULTIPLY", uu, 6.60)), 0.125, 0.50)
    dv = M(g, "ABSOLUTE", M(g, "SUBTRACT", vv, sp))
    dbody = M(g, "SUBTRACT", 1.0, STEP(g, dv, 0.056, 0.084))     # 细身（约 6 cm）
    hdu = M(g, "SUBTRACT", uu, 0.150)
    hdv = M(g, "SUBTRACT", vv, 0.600)
    hd = M(g, "SQRT", M(g, "ADD", M(g, "MULTIPLY", hdu, hdu),
                       M(g, "MULTIPLY", hdv, hdv)))
    dhead = M(g, "SUBTRACT", 1.0, STEP(g, hd, 0.100, 0.148))
    # 四爪 + 尾叉：若干小团块，靠它们把「一条带子」读成「一条龙」
    limb = None
    for (lu, side) in ((0.315, 1), (0.455, -1), (0.600, 1), (0.735, -1)):
        su = M(g, "SUBTRACT", uu, lu)
        sv = M(g, "ADD", sp, side * 0.128)
        sw = M(g, "SUBTRACT", vv, sv)
        ld = M(g, "SQRT", M(g, "ADD", M(g, "MULTIPLY", su, su),
                           M(g, "MULTIPLY", sw, sw)))
        blob = M(g, "SUBTRACT", 1.0, STEP(g, ld, 0.030, 0.052))
        limb = blob if limb is None else M(g, "MAXIMUM", limb, blob)
    for side in (1, -1):
        tu = M(g, "SUBTRACT", uu, 0.885)
        tv = M(g, "SUBTRACT", vv, M(g, "ADD", sp, side * 0.105))
        tt = M(g, "SQRT", M(g, "ADD", M(g, "MULTIPLY", tu, tu),
                          M(g, "MULTIPLY", tv, tv)))
        blob = M(g, "SUBTRACT", 1.0, STEP(g, tt, 0.024, 0.044))
        limb = blob if limb is None else M(g, "MAXIMUM", limb, blob)
    dragon = M(g, "MAXIMUM", M(g, "MAXIMUM", dbody, dhead), limb)
    dragon = M(g, "MULTIPLY", dragon, inner)
    gold = M(g, "MAXIMUM",
             M(g, "MAXIMUM", M(g, "MAXIMUM", gold_line, v_gold),
               M(g, "MAXIMUM", M(g, "MULTIPLY", orn, 0.22),
                 M(g, "MULTIPLY", dots, 0.82))),
             M(g, "MULTIPLY", dragon, 0.95))
    _caihua_finish(g, col, gold, tc)


# ============================================================== 杂项材质

def _metal(g, base, rough=0.26, var=0.10, tint=None):
    tc = TEXCO(g)
    n = NOISE(g, tc.outputs["Object"], 6.0, 6.0, 0.55)
    col = MIXC(g, 1.0, base, M(g, "MULTIPLY_ADD", n, var * 2.0, 1.0 - var), "MULTIPLY")
    if tint:
        col = MIXC(g, 0.25, col, tint)
    g.put(g.bsdf.inputs["Base Color"], col)
    g.put(g.bsdf.inputs["Roughness"], M(g, "MULTIPLY_ADD", n, 0.10, rough - 0.05))
    g.bsdf.inputs["Metallic"].default_value = 1.0


def _bronze(g):
    tc = TEXCO(g)
    obj = tc.outputs["Object"]
    n = NOISE(g, obj, 3.5, 8.0, 0.6, distortion=0.6)
    pat = STEP(g, NOISE(g, obj, 2.0, 9.0, 0.65, distortion=0.8), 0.46, 0.72)
    col = MIXC(g, 1.0, (0.130, 0.098, 0.055), M(g, "MULTIPLY_ADD", n, 0.5, 0.75), "MULTIPLY")
    col = MIXC(g, M(g, "MULTIPLY", pat, 0.75), col, (0.042, 0.105, 0.078))
    g.put(g.bsdf.inputs["Base Color"], col)
    g.put(g.bsdf.inputs["Roughness"], M(g, "MULTIPLY_ADD", pat, 0.30, 0.30))
    g.bsdf.inputs["Metallic"].default_value = 1.0
    g.put(g.bsdf.inputs["Normal"], BUMP(g, n, 0.25, 0.0008))


def _brick(g, base=(0.105, 0.092, 0.080)):
    """青砖：卧砖错缝 + 灰缝。0.24 × 0.07 m 常见尺寸。"""
    tc = TEXCO(g)
    ox, oy, oz = OBJ_XZ(g, tc)
    row = M(g, "FLOOR", M(g, "DIVIDE", oz, 0.072))
    off = M(g, "MULTIPLY", M(g, "FLOORED_MODULO", row, 2.0), 0.12)
    uu = M(g, "DIVIDE", M(g, "ADD", ox, off), 0.24)
    fu = M(g, "MINIMUM", M(g, "FRACT", uu), M(g, "SUBTRACT", 1.0, M(g, "FRACT", uu)))
    fv = M(g, "MINIMUM", M(g, "FRACT", M(g, "DIVIDE", oz, 0.072)),
           M(g, "SUBTRACT", 1.0, M(g, "FRACT", M(g, "DIVIDE", oz, 0.072))))
    mortar = M(g, "MAXIMUM", M(g, "SUBTRACT", 1.0, STEP(g, fu, 0.012, 0.030)),
               M(g, "SUBTRACT", 1.0, STEP(g, fv, 0.020, 0.050)))
    bn = g.node("ShaderNodeTexWhiteNoise", noise_dimensions="3D")
    cidx = g.node("ShaderNodeCombineXYZ")
    g.link(M(g, "FLOOR", uu), cidx.inputs[0])
    g.link(row, cidx.inputs[1])
    g.link(cidx.outputs[0], bn.inputs["Vector"])
    var = M(g, "MULTIPLY_ADD", bn.outputs["Value"], 0.35, 0.80)
    col = MIXC(g, 1.0, base, var, "MULTIPLY")
    col = MIXC(g, M(g, "MULTIPLY", mortar, 0.85), col, (0.145, 0.140, 0.132))
    n = NOISE(g, tc.outputs["Object"], 12.0, 8.0, 0.65)
    col = MIXC(g, M(g, "MULTIPLY", n, 0.35), col, (0.055, 0.050, 0.046))
    g.put(g.bsdf.inputs["Base Color"], col)
    g.put(g.bsdf.inputs["Roughness"], M(g, "MULTIPLY_ADD", mortar, 0.22, 0.72))
    g.bsdf.inputs["Specular IOR Level"].default_value = 0.3
    g.put(g.bsdf.inputs["Normal"], BUMP(g, M(g, "ADD", mortar, M(g, "MULTIPLY", n, 0.5)),
                                        strength=0.55, distance=0.0035))


def _glass(g):
    g.bsdf.inputs["Base Color"].default_value = (0.16, 0.24, 0.24, 1.0)
    g.bsdf.inputs["Roughness"].default_value = 0.055
    g.bsdf.inputs["Metallic"].default_value = 0.0
    g.bsdf.inputs["IOR"].default_value = 1.46
    for k, v in (("Transmission Weight", 0.85), ("Coat Weight", 0.25)):
        if k in g.bsdf.inputs:
            g.bsdf.inputs[k].default_value = v


def _plaque(g):
    """匾：深蓝漆地 + 金框（框在几何里）。"""
    _paint(g, (0.014, 0.021, 0.042), rough=(0.30, 0.38), coat=0.35, grime=0.18)


# ============================================================== 材质表

def _mat(name):
    """取或新建材质；已存在则原地重建节点（旧物体上的引用自动升级）。"""
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
    return m


def make_materials():
    """建全套材质，返回 MAT（键名与 precise_lib.MAT 一致，可直接 update）。"""
    global MAT, _BUILT
    out = {}

    def add(key, dbname, fn):
        m = _mat(dbname)
        g = Graph(m)
        fn(g)
        m.use_backface_culling = False
        out[key] = m

    # ---- 瓦作
    add("tile", "琉璃黄", lambda g: _glaze_tile(g, GLAZE_YELLOW, GLAZE_YELLOW_DARK,
                                                r_lo=0.22, r_hi=0.36, coat=0.18, dirt=0.5))
    add("tile2", "琉璃黄·暗", lambda g: _glaze_tile(g, GLAZE_YELLOW_DARK,
                                                    (0.250, 0.105, 0.010),
                                                    r_lo=0.34, r_hi=0.50, coat=0.10,
                                                    dirt=0.9))
    add("glazed_green", "琉璃绿", lambda g: _glaze_tile(g, GLAZE_GREEN,
                                                       (0.008, 0.085, 0.028),
                                                       coat=0.13, dirt=0.8))
    add("glaze_plain", "琉璃黄·素面",
        lambda g: _glaze_plain(g, GLAZE_YELLOW, GLAZE_YELLOW_DARK,
                               rough=(0.20, 0.30), grime=0.55, coat=0.20))
    add("glaze_plain_dark", "琉璃黄·素面暗",
        lambda g: _glaze_plain(g, (0.360, 0.195, 0.007), (0.185, 0.080, 0.003),
                               rough=(0.24, 0.36), grime=0.95, coat=0.14))
    add("tile_gray", "青瓦", _gray_tile)
    # ---- 石作
    add("stone", "汉白玉", lambda g: _marble(g, veins=1.45, bump=0.0011))
    add("marble_carved", "汉白玉·雕花", lambda g: _marble(g, veins=1.75, bump=0.0016,
                                                          carve=True))
    add("stone2", "石阶", lambda g: _stone(g, (0.470, 0.450, 0.400), dirt=0.55,
                                           rough_lo=0.46, rough_hi=0.66))
    add("citywall", "城墙红", lambda g: _brick(g, base=(0.150, 0.045, 0.033)))
    # ---- 木作 / 油作
    add("column", "朱红柱", lambda g: _wood(g, ZHU_RED, rough=0.48, grain=0.10, coat=0.12))
    add("wall", "朱红墙", lambda g: _wood(g, ZHU_RED_WALL, rough=0.54, grain=0.22, coat=0.05))
    add("red_lacquer", "红漆", lambda g: _paint(g, (0.330, 0.036, 0.023),
                                                rough=(0.34, 0.44), coat=0.30, grime=0.20))
    add("wood_dark", "深色木", lambda g: _wood(g, (0.050, 0.030, 0.019), rough=0.56,
                                               grain=0.30, coat=0.04))
    add("door", "隔扇", lambda g: _wood(g, (0.150, 0.045, 0.026), rough=0.48,
                                        grain=0.26, coat=0.12))
    add("lattice", "格心", lambda g: _wood(g, (0.215, 0.130, 0.062), rough=0.46,
                                           grain=0.28, coat=0.06))
    add("soffit", "椽望", lambda g: _wood(g, (0.115, 0.082, 0.058), rough=0.78,
                                          grain=0.35, coat=0.0))
    # 隔扇格心背板：透空的菱花后面是殿内，几乎见不到光；不压暗就会透出砖红墙，
    # 整排隔扇在正立面上读成一大片糊红（曾是最显眼的"不像现实"）
    add("window_void", "格心背板", lambda g: _wood(g, (0.030, 0.024, 0.019),
                                                  rough=0.88, grain=0.08, coat=0.0))
    add("plaque", "匾", _plaque)
    add("dou", "斗拱", _dou)
    # ---- 彩画
    add("cai_blue", "彩画青", lambda g: _paint(g, CAI_BLUE, rough=(0.42, 0.54),
                                               coat=0.06, grime=0.30))
    add("cai_green", "彩画绿", lambda g: _paint(g, CAI_GREEN, rough=(0.42, 0.54),
                                                coat=0.06, grime=0.30))
    add("caihua_blue", "和玺彩画·青", lambda g: _caihua(g, CAI_BLUE, CAI_GREEN, CAI_BLUE))
    add("caihua_green", "和玺彩画·绿", lambda g: _caihua(g, CAI_GREEN, CAI_BLUE, CAI_GREEN))
    add("caihua_uv_blue", "和玺彩画·青·UV",
        lambda g: _caihua_uv(g, CAI_BLUE, CAI_GREEN, CAI_BLUE))
    add("caihua_uv_green", "和玺彩画·绿·UV",
        lambda g: _caihua_uv(g, CAI_GREEN, CAI_BLUE, CAI_GREEN))
    # ---- 金属
    add("gold", "金", lambda g: _metal(g, GOLD_COL, rough=0.24))
    add("metal", "金属", lambda g: _metal(g, (0.500, 0.510, 0.530), rough=0.30))
    add("bronze", "古铜", _bronze)
    add("glass", "玻璃", _glass)
    add("brick", "青砖", lambda g: _brick(g))

    MAT.clear()
    MAT.update(out)
    _BUILT = True
    return MAT


def _dou(g):
    """斗拱：青绿底 + 描金边。

    檐下几乎全是阴影，底色压太低会渲成一条黑带（整座殿最显眼的就是它，很假）。
    做法：
      * 底色按 lead 口径提到 0.045~0.13，每攒再用 Object Info.Random 偏一点色；
      * 描金边不用 Pointiness（低模盒子上每个顶点都是凸角，整攒会全变金），
        改用 Bevel 法线与面法线的夹角：只有棱上才偏 → 5~8 mm 的金线；
      * 法线朝下压暗一档（假地面反弹），暗部仍有体积。
    """
    tc = TEXCO(g)
    obj = tc.outputs["Object"]
    n = NOISE(g, obj, 2.6, 8.0, 0.6, distortion=0.5)
    col = MIXC(g, STEP(g, n, 0.52, 0.72), (0.235, 0.520, 0.455), (0.245, 0.575, 0.360))
    # 每攒（每个物体实例）微调色相，避免一片死平
    oi = g.node("ShaderNodeObjectInfo")
    col = MIXC(g, M(g, "MULTIPLY", oi.outputs["Random"], 0.35),
               col, (0.205, 0.420, 0.290))
    # 描金边：面法线 · Bevel 法线 < 1 的地方就是棱
    geo = g.node("ShaderNodeNewGeometry")
    bev = g.node("ShaderNodeBevel", samples=2)
    _set_first_attr(bev, ("radius",), 0.008)
    if "Radius" in bev.inputs:
        bev.inputs["Radius"].default_value = 0.008
    dot = g.node("ShaderNodeVectorMath", operation="DOT_PRODUCT")
    g.link(geo.outputs["Normal"], dot.inputs[0])
    g.link(bev.outputs["Normal"], dot.inputs[1])
    gold = M(g, "SUBTRACT", 1.0, STEP(g, M(g, "ADD", dot.outputs["Value"], 0.006),
                                     0.950, 0.996))
    # 檐影里真金（Metallic 1）会吸成黑线：用暖象牙金 + 半金属，暗部才看得见
    col = MIXC(g, gold, col, (0.560, 0.480, 0.300))
    # 朝下的面压暗（假地面反弹），朝上的面略提
    sn = g.node("ShaderNodeSeparateXYZ")
    g.link(geo.outputs["Normal"], sn.inputs[0])
    bounce = M(g, "MULTIPLY_ADD", sn.outputs["Z"], 0.22, 0.92)
    col = MIXC(g, 1.0, col, bounce, "MULTIPLY")
    ao = AO(g, distance=0.22, samples=8)
    col = MIXC(g, M(g, "MULTIPLY", M(g, "SUBTRACT", 1.0, ao), 0.22), col,
               (0.035, 0.038, 0.030))
    g.put(g.bsdf.inputs["Base Color"], col)
    rough = M(g, "MULTIPLY_ADD", n, 0.10, 0.42)
    g.put(g.bsdf.inputs["Roughness"], MIXF(g, gold, rough, 0.30))
    g.link(M(g, "MULTIPLY", gold, 0.55), g.bsdf.inputs["Metallic"])
    g.bsdf.inputs["Specular IOR Level"].default_value = 0.4
    g.put(g.bsdf.inputs["Normal"], BUMP(g, n, 0.15, 0.0006))


# ============================================================== 世界 / 光照

def _sky_sun_rotation(az_deg):
    """把「罗盘方位角」换算成 Nishita 天空的 sun_rotation。

    本机实测（Blender 5.3 MULTIPLE_SCATTERING，720×360 全景标定）：sun_rotation=0 时
    太阳在正北（罗盘 0°），+90° 时在正东 → sun_rotation 就是罗盘方位角本身。
    """
    return math.radians(az_deg % 360.0)


def sun_direction(az=228.0, elev=36.0):
    """罗盘方位角（0=北，90=东）+ 高度角 → 指向太阳的单位向量（+y 北、+x 东、+z 上）。"""
    a, e = math.radians(az), math.radians(elev)
    return Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))


#: HDR 像素经度 → 天空经度的固定偏移。实测（720×360 全景 + 方位标记标定）：
#: Blender 的环境采样比图像像素经度整体转了 +90°，跟贴图无关，是采样器约定。
_HDRI_AZ_OFFSET = 90.0


def _detect_hdri_sun(img):
    """从 HDRI 像素里找最亮方向 → (天空罗盘方位角, 高度角)；读不到就返回 None。

    映射（720×360 全景实测，含方位标记锚定）：
        az_raw = ((x+0.5)/W − 0.5)·360 ，az_sky = az_raw + 90
        elev   = ((y+0.5)/H − 0.5)·180（y 自下往上）
    """
    try:
        import numpy as np
    except Exception:
        return None
    try:
        w, h = img.size
        if not w or not h or not img.pixels:
            return None
        buf = np.empty(w * h * 4, dtype=np.float32)
        img.pixels.foreach_get(buf)
        a = buf.reshape(h, w, 4)
        lum = a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722
        iy, ix = np.unravel_index(int(np.argmax(lum)), lum.shape)
        az = ((((ix + 0.5) / w) - 0.5) * 360.0 + _HDRI_AZ_OFFSET) % 360.0
        elev = (((iy + 0.5) / h) - 0.5) * 180.0
        return round(float(az), 2), round(float(elev), 2)
    except Exception:
        return None


def _suppress_env_sun(nt, color_socket, k=0.45, threshold=2.0):
    """压掉 HDR 自带的太阳盘：只对亮过 threshold 的部分按 1/(1+excess·k) 压。

    天空环境光（亮度 ~1）几乎不动，太阳盘（亮度几百）被压到很低，
    于是"HDRI + 太阳灯"同时开也只有一个太阳，屋面不会烧成白纸。
    返回可接 Background.Color 的 socket。
    """
    dot = nt.nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    dot.location = (170, -260)
    nt.links.new(color_socket, dot.inputs[0])
    dot.inputs[1].default_value = (0.2126, 0.7152, 0.0722)
    sub = nt.nodes.new("ShaderNodeMath")
    sub.operation = "SUBTRACT"
    sub.location = (330, -260)
    nt.links.new(dot.outputs["Value"], sub.inputs[0])
    sub.inputs[1].default_value = threshold
    exc = nt.nodes.new("ShaderNodeMath")
    exc.operation = "MAXIMUM"
    exc.location = (490, -260)
    nt.links.new(sub.outputs[0], exc.inputs[0])
    exc.inputs[1].default_value = 0.0
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY_ADD"
    mul.location = (650, -260)
    nt.links.new(exc.outputs[0], mul.inputs[0])
    mul.inputs[1].default_value = k
    mul.inputs[2].default_value = 1.0
    div = nt.nodes.new("ShaderNodeMath")
    div.operation = "DIVIDE"
    div.location = (810, -260)
    div.inputs[0].default_value = 1.0
    nt.links.new(mul.outputs[0], div.inputs[1])
    scale = nt.nodes.new("ShaderNodeVectorMath")
    scale.operation = "SCALE"
    scale.location = (960, -180)
    nt.links.new(color_socket, scale.inputs[0])
    nt.links.new(div.outputs[0], scale.inputs["Scale"])
    return scale.outputs["Vector"]


def setup_world(scene, hdri_path=None, strength=None, fallback_sky=True,
                az=228.0, elev=36.0, hdri_rotation=None, align_sun=True,
                sun_suppress=0.45):
    """世界环境：优先 HDRI；没有就程序化 Nishita 天空（还是能出实景感）。

    hdri_path 可以是绝对路径；也可以只给文件名，函数会去 tools/palace/assets/ 找。
    strength=None（默认）→ 用安全值：有 HDR 时 0.80（HDR 的太阳已被压掉，只剩环境光），
    纯程序化 Nishita 天空时 0.04
    （本机实测 Nishita 天空辐射 ≈ 12× 这张 2k HDR：给 1.0 一片白，给 0.11 仍偏亮）。
    传数字就按你给的来（想压暗/提亮自己调）。

    align_sun=True 时自动把 HDR 的太阳转到 az（否则会和太阳灯打两套影子），
    并把检测到的 hdri_sun 一并返回——**太阳灯的 elev 请对齐这个高度角**。

    sun_suppress>0 时把 HDR 自带的太阳盘压掉（只压高亮，天空环境光不动），
    这样"HDRI + 太阳灯"同时开也不会变成两个太阳、不会把屋面烧成白纸。
    返回 dict（实际用了哪条路径、强度、天光太阳角度），便于日志。
    """
    path, tried = _resolve_hdri(hdri_path)
    if strength is None:
        strength = 0.80 if path else 0.04
    world = scene.world
    if world is None:
        world = bpy.data.worlds.new("LG_World")
        scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    out.location = (600, 0)
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.location = (400, 0)
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    bg.inputs["Strength"].default_value = strength

    used = "procedural_sky"
    hdri_sun = None
    rotation = hdri_rotation
    if path:
        env = nt.nodes.new("ShaderNodeTexEnvironment")
        env.location = (0, 0)
        env.image = bpy.data.images.load(path, check_existing=True)
        hdri_sun = _detect_hdri_sun(env.image)
        if rotation is None:
            rotation = 0.0
            if align_sun and hdri_sun:
                rotation = (az - hdri_sun[0]) % 360.0
                if abs(rotation) > 180.0:
                    rotation -= 360.0
        mapping = nt.nodes.new("ShaderNodeMapping")
        mapping.location = (-240, 0)
        mapping.inputs["Rotation"].default_value = (0.0, 0.0, math.radians(rotation))
        texco = nt.nodes.new("ShaderNodeTexCoord")
        texco.location = (-460, 0)
        nt.links.new(texco.outputs["Generated"], mapping.inputs["Vector"])
        nt.links.new(mapping.outputs["Vector"], env.inputs["Vector"])
        col = env.outputs["Color"]
        if sun_suppress:
            col = _suppress_env_sun(nt, col, sun_suppress, threshold=2.0)
        nt.links.new(col, bg.inputs["Color"])
        used = "hdri"
    elif fallback_sky:
        sky = nt.nodes.new("ShaderNodeTexSky")
        sky.location = (-60, 0)
        _set_first_attr(sky, ("sky_type",), "MULTIPLE_SCATTERING")
        sky.sun_disc = False                    # 太阳由 setup_sun 的灯负责
        sky.sun_elevation = math.radians(elev)
        _set_first_attr(sky, ("sun_rotation",), _sky_sun_rotation(az))
        sky.altitude = 60.0
        _set_first_attr(sky, ("dust_density", "aerosol_density"), 1.2)
        nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    else:
        # 最后兜底：两层纯色渐变（完全没有实景感，仅防崩）
        tc = nt.nodes.new("ShaderNodeTexCoord")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(tc.outputs["Generated"], sep.inputs[0])
        ramp = nt.nodes.new("ShaderNodeMapRange")
        nt.links.new(sep.outputs["Z"], ramp.inputs["Value"])
        ramp.inputs["From Min"].default_value = -0.05
        ramp.inputs["From Max"].default_value = 0.55
        mix = nt.nodes.new("ShaderNodeMixRGB")
        nt.links.new(ramp.outputs[0], mix.inputs["Factor"])
        mix.inputs["Color1"].default_value = (0.42, 0.52, 0.66, 1.0)
        mix.inputs["Color2"].default_value = (0.10, 0.22, 0.50, 1.0)
        nt.links.new(mix.outputs["Color"], bg.inputs["Color"])
        used = "flat_gradient"
    world["lg_look"] = used
    info = {"world": used, "hdri": path, "strength": strength,
            "hdri_rotation": round(rotation, 2) if rotation is not None else None,
            "hdri_sun": hdri_sun, "sun_suppress": sun_suppress,
            "sun_rotation_deg": az, "tried": tried}
    _LAST_WORLD.clear()
    _LAST_WORLD.update(info)
    return info


def _resolve_hdri(hdri_path):
    """只给文件名时去 assets 目录找；找不到就返回 None（走程序化兜底）。

    hdri_path 传 "-" / "none" / "off" / "proc" 表示**明确不要 HDRI**，直接用程序化天空。
    """
    if isinstance(hdri_path, str) and hdri_path.strip().lower() in (
            "-", "none", "off", "no", "proc", "procedural"):
        return None, []
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = []
    if hdri_path:
        candidates.append(hdri_path)
        if not os.path.isabs(hdri_path):
            candidates += [os.path.join(here, "assets", hdri_path),
                           os.path.join(here, hdri_path)]
    else:
        candidates += [os.path.join(here, "assets", n) for n in _DEFAULT_HDRIS]
    for c in candidates:
        if c and os.path.exists(c):
            return os.path.abspath(c), candidates
    return None, candidates


def _set_first_attr(obj, names, value):
    for n in names:
        if hasattr(obj, n):
            try:
                setattr(obj, n, value)
                return True
            except Exception:
                pass
    return False


def setup_sun(scene, energy=3.2, angle_deg=2.5, az=228, elev=36,
              color=(1.0, 0.96, 0.90), name="LG_Sun"):
    """主光：太阳。方位角按罗盘（0=北，90=东，180=南），高度角 36° ≈ 北京冬日午后。

    返回 (物体, 光照参数)。
    """
    d = sun_direction(az, elev)
    ob = bpy.data.objects.get(name)
    if ob is None:
        ld = bpy.data.lights.new(name, type="SUN")
        ob = bpy.data.objects.new(name, ld)
        scene.collection.objects.link(ob)
    ob.data.energy = energy
    ob.data.angle = math.radians(angle_deg)
    ob.data.color = color
    ob.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    ob.location = d * 60.0
    return ob


def setup_fill(scene, size=20.0, energy=350.0, loc=None, az=228.0, elev=14.0,
               color=(0.92, 0.95, 1.0), name="LG_Fill", target=None):
    """补光：20×20 m 面光，只抬暗部。

    注意能量单位是瓦：20 m 见方的面光源在 30 m 外，350 W 的辐照度才 ~0.03 W/m²，
    属于"看得见一点点"的量级（原来写的 0.3 W 在这个尺度下完全不可见）。
    小场景（缩比模型）就传小一点的 size/energy，或者直接给 loc/target。
    """
    d = sun_direction(az, elev)
    ob = bpy.data.objects.get(name)
    if ob is None:
        ld = bpy.data.lights.new(name, type="AREA")
        ob = bpy.data.objects.new(name, ld)
        scene.collection.objects.link(ob)
    ob.data.shape = "SQUARE"
    ob.data.size = size
    ob.data.energy = energy
    ob.data.color = color
    ob.location = loc if loc else (d * 45.0 + Vector((0.0, 0.0, 12.0)))
    if target is not None:
        ob.rotation_euler = (Vector(target) - ob.location).to_track_quat("-Z", "Y").to_euler()
    else:
        ob.rotation_euler = (-d).to_track_quat("Z", "Y").to_euler()
    return ob


# ============================================================== 渲染

def _gpu_device_type():
    """启用 GPU 并返回实际用上的后端名（OPTIX / CUDA / …）；失败返回 None。"""
    addon = bpy.context.preferences.addons.get("cycles")
    if addon is None:
        return None
    prefs = addon.preferences
    for kind in ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL"):
        try:
            prefs.compute_device_type = kind
            prefs.get_devices()
        except Exception:
            continue
        gpus = [d for d in prefs.devices if d.type == kind]
        if not gpus:
            continue
        for d in prefs.devices:
            d.use = (d.type == kind)
        return kind
    return None


def _set_denoiser(cycles, want="OPTIX"):
    for name in (want, "OPENIMAGEDENOISE"):
        try:
            cycles.denoiser = name
            return name
        except Exception:
            continue
    return None


def setup_render(scene, res=1920, samples=128, exposure=-0.2, transparent=False,
                 aspect=9.0 / 16.0, denoiser="OPTIX"):
    """Cycles + GPU + OptiX 降噪 + Standard 色彩管理（AgX 会把宫墙红洗成粉色）。

    res 是宽度；aspect 默认 16:9。返回 dict，可直接打进日志。
    """
    sc = scene
    sc.render.engine = "CYCLES"
    c = sc.cycles
    dev_kind = _gpu_device_type()
    c.device = "GPU" if dev_kind else "CPU"
    c.samples = int(samples)
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.02
    c.use_denoising = True
    c.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    _set_first_attr(c, ("denoising_prefilter",), "ACCURATE")
    dn = _set_denoiser(c, denoiser)
    c.max_bounces = 6
    c.diffuse_bounces = 3
    c.glossy_bounces = 3
    c.transmission_bounces = 4
    c.transparent_max_bounces = 8
    _set_first_attr(c, ("sample_clamp_indirect", "clamp_indirect"), 3.0)
    _set_first_attr(c, ("sample_clamp_direct",), 0.0)
    c.caustics_reflective = False
    c.caustics_refractive = False
    c.blur_glossy = 1.0
    c.seed = 0
    _set_first_attr(c, ("film_transparent_glass", "film_transparent_glass"), False)
    sc.render.film_transparent = bool(transparent)
    sc.render.resolution_x = int(res)
    sc.render.resolution_y = int(round(res * aspect))
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
    sc.render.image_settings.color_depth = "8"
    _set_first_attr(sc.render.image_settings, ("color_management",), "FOLLOW_SCENE")
    sc.render.use_persistent_data = True
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = float(exposure)
    sc.view_settings.gamma = 1.0
    return {"engine": "CYCLES", "device": c.device, "gpu_backend": dev_kind,
            "samples": int(samples), "denoiser": dn, "max_bounces": c.max_bounces,
            "clamp_indirect": getattr(c, "sample_clamp_indirect", None),
            "view_transform": sc.view_settings.view_transform,
            "exposure": sc.view_settings.exposure,
            "res": [sc.render.resolution_x, sc.render.resolution_y],
            "transparent": bool(transparent)}


def render(scene, filepath, quiet=True):
    """渲一张；OptiX 降噪跑挂了就退回 OIDN 重来一次。返回 (耗时, 路径, 后端)。"""
    import time

    scene.render.filepath = filepath
    t0 = time.time()
    try:
        bpy.ops.render.render(write_still=True)
    except Exception as exc:                                    # pragma: no cover
        print("LG_LOOK render failed (%s) -> retry with OIDN" % exc)
        scene.cycles.denoiser = "OPENIMAGEDENOISE"
        bpy.ops.render.render(write_still=True)
    dt = time.time() - t0
    if not quiet:
        print("LG_LOOK RENDER %s %.1fs" % (os.path.basename(filepath), dt))
    return dt, filepath, getattr(scene.cycles, "denoiser", None)


# ============================================================== 给 lead 的参数

def review_settings():
    """建议的曝光 / 白平衡 / 光照参数，lead 直接抄。"""
    info = _LAST_WORLD
    return {
        "view_transform": "Standard",
        "look": "None",
        "exposure": -0.20,
        "white_balance_kelvin": 5600,
        "white_balance_gain": [1.0, 1.0, 0.99],     # 需要时乘到 sun 颜色上
        "lighting_presets": {
            "A_hdri_plus_sun": {
                "world_strength": 0.80, "sun_energy": 3.0, "sun_suppress": 0.45,
                "exposure": -0.20,
                "实测": "960×540 / 64spp：高光占比 0.0%，整幅线性均值 0.26，屋面不烧白",
                "用": "推荐。setup_world 的 strength=None 默认就是这套（有 HDR 时 0.80）；"
                     "sun_suppress 默认 0.45 就够，不用再动",
            },
            "B_hdri_only": {
                "world_strength": 1.0, "sun_energy": 0.0, "sun_suppress": 0.0,
                "exposure": -0.20,
                "实测": "高光占比 0.0%，线性均值 0.35（更亮更平）",
                "用": "关掉太阳灯，纯 HDR 照明。省一盏灯，但阴影全来自 HDR，"
                     "檐下会偏平、边缘软",
            },
            "C_两盏太阳（别这么干）": {
                "world_strength": 1.0, "sun_energy": 3.4, "sun_suppress": 0.0,
                "exposure": -0.20,
                "实测": "高光占比 4.1%（屋面烧成白纸）",
                "用": "HDR 强度拉满 + 太阳灯也拉满 = 两盏太阳，Standard 一剪就没层次",
            },
            "屋面偏暗怎么办": "先 exposure −0.20 → −0.15，再 sun 3.0 → 3.4；"
                              "world 最多到 0.55，再多只是灰雾",
        },
        "world": {"strength": 0.80, "hdri_rotation_deg": "auto（对齐到 sun az）",
                  "fallback": "Nishita MULTIPLE_SCATTERING",
                  "detected": info.get("hdri_sun")},
        "sun": {"energy": 3.2, "angle_deg": 2.5, "az": 228.0,
                "elev": 36.0 if not info.get("hdri_sun") else info["hdri_sun"][1],
                "color": [1.0, 0.96, 0.90],
                "note": "用 HDR 时 elev 要等于 HDR 检测到的高度角（setup_world 返回的 "
                        "hdri_sun[1]），否则两套影子会错开"},
        "fill": {"size": 20.0, "energy": 350.0, "elev": 14.0, "color": [0.92, 0.95, 1.0]},
        "render": {"samples": 128, "max_bounces": 6, "clamp_indirect": 3.0,
                   "denoiser": "OPTIX", "transparent": False},
        "tile": {"uv_contract": "UV 单位米：U 沿檐口、V 沿坡向；无 UV 走世界法线投影",
                 "period_u_m": TILE_U, "period_v_m": TILE_V,
                 "ridge_bump_mm": round(TILE_RIDGE * 1000, 1),
                 "fine_bump_mm": round(TILE_BUMP * 1000, 1),
                 "uv_override": "物体自定义属性 lg_normalized_uv=1 可强制退回投影"},
        "anti_moire": {"near_m": FADE_NEAR, "far_m": FADE_FAR, "floor": FADE_FLOOR,
                       "fades": "Bump Strength / 瓦缝色对比 / 瓦缝粗糙度"},
        "glaze_plain": {"keys": ["glaze_plain", "glaze_plain_dark"],
                        "roughness": [0.20, 0.30], "coat": 0.20,
                        "jitter": "±6% / 0.30 m 网格", "bump": "3 mm 细颗粒，无周期条纹",
                        "用于": "正脊/垂脊/鸱吻/当沟/瓦当（没有 UV 的瓦件）"},
        "caihua": dict(CAIHUA),
        "caihua_uv": {"keys": ["caihua_uv_blue", "caihua_uv_green"],
                      "segment": "箍头 U<0.07 / >0.93；藻头 0.07~0.26 与 0.74~0.93；"
                                 "枋心 0.26~0.74；金线宽 0.006（U 单位）",
                      "v_edge": "上下 12% 压边 + 金线",
                      "用于": "额枋有 UV（U 沿长度 0..1、V 沿高度 0..1）时优于 Object X 版"},
        "dou": {"paint": [(0.165, 0.375, 0.330), (0.175, 0.410, 0.255)],
                "edge": "(0.56,0.48,0.30) 暖象牙金，Metallic 0.55·edge（真金在檐影里发黑）",
                "ao": 0.22, "roughness": [0.42, 0.52],
                "实测": "檐下 480×270 特写：青绿像素线性均值 0.101、p50 0.075（旧版 <0.03）"},
        "materials": sorted(MAT.keys()),
        "notes": [
            "AgX 把朱红洗成粉色：必须 Standard + 曝光 −0.2。",
            "太阳在西南（az=228）打侧光，南立面才有体积；东南向会平。",
            "彩画调依赖额枋是单根盒子；beams() 分段盒子会把彩画卷重复一遍。",
            "瓦垄用 UV（米制，U=0.32/V=0.30）；没 UV 的网格按法线投影兜底。",
        ],
    }


# ============================================================== 小工具

def project_uv_meters(ob, name="UVMap"):
    """给屋顶网格补一套米制 UV（U 沿檐向、V 沿坡向），和材质的兜底投影一致。

    只在网格没有 UV 层时动手；已有的 UV 一律不动。返回是否新建。
    """
    me = ob.data
    if me.uv_layers:
        return False
    uvl = me.uv_layers.new(name=name)
    mw = ob.matrix_world
    for poly in me.polygons:
        n = poly.normal
        swap = abs(n.x) > abs(n.y)          # 东西坡：U 取 Y
        for li in poly.loop_indices:
            co = mw @ me.vertices[me.loops[li].vertex_index].co
            uvl.data[li].uv = (co.y, co.x) if swap else (co.x, co.y)
    uvl.active_render = True
    return True


def tag_uv_units(ob, normalized=False):
    """把「这套 UV 是 0~1 归一化单位」的物体打上标记，材质会自动退回世界投影。

    ob 可以是单个物体、列表或集合（Collection）。
    """
    if hasattr(ob, "objects"):                  # Collection
        objs = list(ob.objects)
    elif isinstance(ob, (list, tuple)):
        objs = list(ob)
    else:
        objs = [ob]
    for o in objs:
        if normalized:
            o["lg_normalized_uv"] = 1.0
        elif "lg_normalized_uv" in o:
            del o["lg_normalized_uv"]
    return len(objs)
