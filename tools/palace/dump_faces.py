"""导出「轴对齐大面」表：每个构件的每张近轴面（面积 ≥ 0.5 m²）一行。

为什么只要轴对齐面：模型的墙、台基、地坪、瓦面绝大多数是盒子或平面多边形，
z-fighting 只发生在**同向、同平面**的两张面之间；斜屋面之间要共面得先共面同坡，
概率极低，先不管。

用法： blender -b palace_massing.blend -P tools/palace/dump_faces.py
输出： $TEMP/palace_massing/faces.csv
        name,axis,sign,const,u0,u1,v0,v1,area
"""
import os
import time

import bpy

WORK = os.path.join(os.environ.get("TEMP", "/tmp"), "palace_massing")
OUT = os.path.join(WORK, "faces.csv")
MIN_AREA = 0.5          # 世界面积下限（m²）
AX_TOL = 0.999          # |normal[axis]| 超过它才算轴对齐

t0 = time.time()
rows = []
npoly = 0
for ob in bpy.context.scene.objects:
    if ob.type != "MESH":
        continue
    mw = ob.matrix_world
    rot = mw.to_3x3()
    me = ob.data
    for p in me.polygons:
        npoly += 1
        n = rot @ p.normal
        ax = 0 if abs(n.x) >= abs(n.y) and abs(n.x) >= abs(n.z) else (
            1 if abs(n.y) >= abs(n.z) else 2)
        if abs(n[ax]) < AX_TOL:
            continue
        vs = [mw @ me.vertices[i].co for i in p.vertices]
        u, v = [i for i in (0, 1, 2) if i != ax]
        u0 = min(p_[u] for p_ in vs)
        u1 = max(p_[u] for p_ in vs)
        v0 = min(p_[v] for p_ in vs)
        v1 = max(p_[v] for p_ in vs)
        area = (u1 - u0) * (v1 - v0)
        if area < MIN_AREA:
            continue
        c = sum(p_[ax] for p_ in vs) / len(vs)
        rows.append((ob.name, ax, 1 if n[ax] > 0 else -1, c, u0, u1, v0, v1, area))

with open(OUT, "w", encoding="utf-8") as f:
    f.write("name,axis,sign,const,u0,u1,v0,v1,area\n")
    for r in rows:
        f.write("%s,%d,%d,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f\n" % r)
print("FACES_DONE 多边形 %d → 轴对齐大面 %d 行，%.1fs → %s"
      % (npoly, len(rows), time.time() - t0, OUT))
