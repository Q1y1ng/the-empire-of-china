"""校验按开间布攒：柱头科是否落在柱轴上、攒距是否均匀、四角是否只有角科。"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, r"E:\AI\帝国\tools\palace")
import lg_dougong as DG  # noqa: E402


def edges(bays):
    out, x = [], 0.0
    total = sum(bays)
    out.append(-total / 2)
    for b in bays:
        x += b
        out.append(-total / 2 + x)
    return out


for (w, d, nb, mb) in ((90.0, 50.0, 11, 5), (48.0, 30.0, 7, 4), (18.0, 12.0, 3, 3)):
    unit = max(0.070, min(0.170, w / 545.0))
    sp = 11.0 * unit
    xs, ys = edges([w / nb] * nb), edges([d / mb] * mb)
    slots = DG.ring_layout_bays(w, d, sp, xs, ys)
    old = DG.ring_layout(w, d, sp)
    print("=" * 70)
    print("hall %.0f x %.0f  斗口 %.3f  目标中距 %.2f  开间 %.2f" % (w, d, unit, sp, w / nb))
    print("  旧方案（每边等分）：%d 攒；新方案（按柱）：%d 攒" % (len(old), len(slots)))
    # 柱轴对齐检查：南侧每一攒的 x 必须落在 xs 上或两柱之间等分点
    south = sorted(s[0] for s in slots if s[1] < 0 and s[4] == 0)
    colx = [round(v, 3) for v in xs[1:-1]]
    hit = sum(1 for x in south if round(x, 3) in colx)
    print("  南侧 %d 攒，其中 %d 攒正对柱轴" % (len(south), hit))
    gaps = [round(south[i + 1] - south[i], 3) for i in range(len(south) - 1)]
    print("  南侧攒距：%s" % sorted(set(gaps))[:6])
    hits = sum(1 for s in slots if s[4] == 2)
    print("  角科 %d 攒（应为 4）" % hits)
    # 柱头科落位：每个 interior 柱位两个方向各一攒
    assert hits == 4, hits
    for x in xs[1:-1]:
        assert any(abs(s[0] - x) < 1e-6 and s[1] < 0 for s in slots), ("缺柱头科", x)
    print("  OK 柱头科 %d 个柱位全部有攒；无柱位缺攒" % len(xs[1:-1]))
print("SELFTEST_OK")
