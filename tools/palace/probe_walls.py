"""只做枚举：列出 blend 里所有名字带「墙 / 垛 / 台明」的对象前缀统计。

用法：
  blender -b palace_massing.blend -P tools/palace/probe_walls.py
"""
import bpy
import collections
import os
import sys

PREFIX = 2  # 按「·」切分取前 N 段当作类名


def key(n):
    parts = n.split("·")
    return "·".join(parts[:PREFIX]) if len(parts) > 1 else parts[0]


cnt = collections.Counter()
by_kind = collections.Counter()
for ob in bpy.context.scene.objects:
    if ob.type != "MESH":
        continue
    n = ob.name
    by_kind[ob.name.split("·")[0][:6]] += 1
    if ("墙" in n) or ("垛" in n) or ("台明" in n):
        cnt[key(n)] += 1

print("=== 对象总数 %d ===" % len(bpy.context.scene.objects))
print("=== 名字含 墙/垛/台明 的类 ===")
for k, v in sorted(cnt.items(), key=lambda kv: -kv[1]):
    print("%6d  %s" % (v, k))

print("=== 全部前缀 top40 ===")
for k, v in by_kind.most_common(40):
    print("%6d  %s" % (v, k))

out = os.path.join(os.environ.get("TEMP", "/tmp"), "palace_massing", "walls_probe.txt")
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w", encoding="utf-8") as f:
    f.write("total %d\n" % len(bpy.context.scene.objects))
    for k, v in sorted(cnt.items(), key=lambda kv: -kv[1]):
        f.write("%6d  %s\n" % (v, k))
print("PROBE_DONE", out)
