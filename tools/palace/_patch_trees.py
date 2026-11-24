"""把树的落位改成「先查禁区再种」：树冠不许穿进墙身、瓦帽与城门。

改法：
1. add_wall() / wall_bar() 把各自的平面矩形登记进 _KEEP（墙身与瓦帽一起算）；
2. 城门按 STRUCTS 的门洞 + 两翼墙算一个禁区；
3. _plant() 先查禁区（含树冠最大半径），命中就跳过；索引与计数改由 _plant 自己管。
"""
import io
import re

P = r"E:\AI\帝国\tools\palace\build_massing.py"
s = io.open(P, encoding="utf-8").read()

# 1) 禁区表 + 登记函数，插在 add_wall 之前
anchor = "def add_wall(name, x0, x1, y0, y1, h=WH, mat=None):"
assert s.count(anchor) == 1
keep_block = (
    "# 树冠禁区：墙身/瓦帽/城门的平面矩形。行道树原来是按「离墙 3.5 m」摆的，\n"
    "# 而树冠最大半径到 4.2 m —— 于是树冠从墙帽里长出来（体检里 71 段墙的瓦\n"
    "# 帽被 树·冠 整个盖住）。改成按禁区查，树自己避开墙。\n"
    "_KEEP = []\n"
    "\n"
    "\n"
    "def keep_add(x0, x1, y0, y1):\n"
    "    _KEEP.append((min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)))\n"
    "\n"
    "\n"
) + anchor
s = s.replace(anchor, keep_block, 1)

# 2) add_wall 里登记矩形（函数体首行之后）
old = """    mat = mat or MAT["wall"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2"""
new = """    mat = mat or MAT["wall"]
    keep_add(x0, x1, y0, y1)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2"""
assert s.count(old) == 1
s = s.replace(old, new, 1)

# 3) wall_bar 登记城墙矩形
old = """def wall_bar(name, w, d, x, y, along_x=True):
    box(name, w, d, H, x, y, 0.0, MAT["citywall"])"""
new = """def wall_bar(name, w, d, x, y, along_x=True):
    keep_add(x - w / 2, x + w / 2, y - d / 2, y + d / 2)
    box(name, w, d, H, x, y, 0.0, MAT["citywall"])"""
assert s.count(old) == 1
s = s.replace(old, new, 1)

# 4) _plant：改成自己管索引 + 查禁区
old = '''def _plant(i, x, y):
    """种一棵树：把几何塞进两个大数组，最后只建 2 个网格。

    原来每棵树用 bpy.ops 建 1 柱 + 3 球 = 4 个对象，700 多棵就是 2,800 次算子
    调用，构建时间全耗在这上面（构建从 3 分钟涨到 10 分钟的主因）。
    """
    sv = 0.78 + 0.50 * ((i * 37) % 11) / 10.0'''
new = '''_PIDX = [0]


def _plant(x, y):
    """种一棵树：把几何塞进两个大数组，最后只建 2 个网格。

    原来每棵树用 bpy.ops 建 1 柱 + 3 球 = 4 个对象，700 多棵就是 2,800 次算子
    调用，构建时间全耗在这上面（构建从 3 分钟涨到 10 分钟的主因）。

    落位前先查 _KEEP：树冠最大水平半径 ≈ 3.1×1.28 + 1.5 ≈ 4.3 m，
    命中任何墙/城门的禁区就跳过（宁可少一棵树，也不让树从墙帽里长出来）。
    """
    for (kx0, kx1, ky0, ky1) in _KEEP:
        if kx0 - 4.3 < x < kx1 + 4.3 and ky0 - 4.3 < y < ky1 + 4.3:
            return False
    i = _PIDX[0]
    _PIDX[0] += 1
    sv = 0.78 + 0.50 * ((i * 37) % 11) / 10.0'''
assert s.count(old) == 1
s = s.replace(old, new, 1)

# _plant 末尾补 return True
old = """        for (a_, b_, c_) in _ICO_F:
            _LF.append((b + a_, b + b_, b + c_))"""
new = """        for (a_, b_, c_) in _ICO_F:
            _LF.append((b + a_, b + b_, b + c_))
    return True"""
assert s.count(old) == 1
s = s.replace(old, new, 1)

# 5) 调用点：去掉 _planted 计数
s = re.sub(r"(_plant)\(_planted, ([^)]*)\)\n([ \t]*)_planted \+= 1", r"\1(\2)", s)
s = s.replace("""_planted = 0
for x, y in D.trees():
    _plant(_planted, x, y)""", """for x, y in D.trees():
    _plant(x, y)""")
s = s.replace('print("TREES", _planted,', 'print("TREES", _PIDX[0],')

# 6) 城门禁区：在城门循环之后登记
old = """ct = D.CORNER_TOWER"""
new = """for _g in D.GATES:
    _st = _GATE_ST[_g["name"]]
    if _g["side"] in ("S", "N"):
        keep_add(_st["cx"] - _st["w"] / 2 - PL.GATE_WING,
                 _st["cx"] + _st["w"] / 2 + PL.GATE_WING,
                 _st["cy"] - _st["d"] / 2, _st["cy"] + _st["d"] / 2)
    else:
        keep_add(_st["cx"] - _st["d"] / 2, _st["cx"] + _st["d"] / 2,
                 _st["cy"] - _st["w"] / 2 - PL.GATE_WING,
                 _st["cy"] + _st["w"] / 2 + PL.GATE_WING)

ct = D.CORNER_TOWER"""
assert s.count(old) == 1
s = s.replace(old, new, 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("patched tree keep-out")
