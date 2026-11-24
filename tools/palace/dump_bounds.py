"""把整个场景的世界包围盒导出成 CSV，供纯 Python 审计脚本反复分析（不必再开 Blender）。

用法：
  blender -b palace_massing.blend -P tools/palace/dump_bounds.py
"""
import bpy
import os
from mathutils import Vector

WORK = os.path.join(os.environ.get("TEMP", "/tmp"), "palace_massing")
os.makedirs(WORK, exist_ok=True)
out = os.path.join(WORK, "bounds.csv")

n = 0
with open(out, "w", encoding="utf-8") as f:
    f.write("name,x0,x1,y0,y1,z0,z1,rot_deg,tris\n")
    dg = bpy.context.evaluated_depsgraph_get()
    for ob in bpy.context.scene.objects:
        if ob.type != "MESH":
            continue
        mw = ob.matrix_world
        cs = [mw @ Vector(c) for c in ob.bound_box]
        xs = [c.x for c in cs]
        ys = [c.y for c in cs]
        zs = [c.z for c in cs]
        me = ob.data
        nt = len(me.loop_triangles) if me.loop_triangles else len(me.polygons)
        f.write("%s,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.2f,%d\n" % (
            ob.name.replace(",", "，"),
            min(xs), max(xs), min(ys), max(ys), min(zs), max(zs),
            ob.matrix_world.to_euler().z * 57.2957795, nt))
        n += 1

print("DUMP_DONE %d 件 → %s" % (n, out))
