"""一条命令自查：断言 → 只出受影响的图。

    py -3 tools/audit/check.py                    # 断言 + 16 站位接触表（~13 s）
    py -3 tools/audit/check.py --no-shots         # 只算数（<1 s，适合每改一次就跑）
    py -3 tools/audit/check.py --diff prev.json   # 只出“相对 prev 有变化”的机位
    py -3 tools/audit/check.py --fail-on-warn     # 待裁项也算失败（CI / 收尾前）

为什么要有这一层：散着五个脚本没人会天天敲。作品会话的闭环是
「改一个数 → 跑 30 s 构建 → 想看一眼」，所以这里必须一条命令把
“数对不对”和“该看哪几张”一起给出来。

退出码：0 全过；1 断言失败；2 环境/参数问题。
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

try:                      # MSYS bash 里控制台是 UTF-8，Python 默认 cp936 会输出乱码
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DEFAULT_MANIFEST = os.path.join(ROOT, "build", "hall_manifest.json")
PY = sys.executable


def run(script, extra):
    cmd = [PY, os.path.join(HERE, script)] + extra
    proc = subprocess.run(cmd, timeout=1200)
    return proc.returncode


def affected(prev, cur):
    """用 manifest.py 的同一套口径算受影响机位（视锥 + 分组可见）。"""
    sys.path.insert(0, HERE)
    import manifest_io
    from manifest import stations_for
    _, new_items, _ = manifest_io.load(cur)
    _, old_items, _ = manifest_io.load(prev)
    old = {i["name"]: i for i in old_items}
    new = {i["name"]: i for i in new_items}
    changed = [n for n in new if n not in old
               or new[n]["tris"] != old[n]["tris"]
               or any(abs(a - b) > 0.002 for k in ("min", "max")
                      for a, b in zip(new[n][k], old[n][k]))]
    groups = {(new[n]["group"] or "hall") for n in changed}
    return stations_for(groups, new_items) if groups else []


def acceptance_summary():
    """验收账本里还没守住的条目数（A 路子的日常读数）。"""
    path = os.path.join(HERE, "acceptance.json")
    if not os.path.exists(path):
        return
    import json as _json
    with open(path, encoding="utf-8") as fh:
        doc = _json.load(fh)
    open_n = sum(1 for i in doc["items"] if i.get("status") == "open")
    spec = sum(1 for i in doc["items"] if i.get("status") == "spec")
    if open_n or spec:
        print(f"\n验收账本：{open_n} 条未守住、{spec} 条待裁"
              f"（py -3 tools/audit/acceptance.py --open）")


def run_geom(blend):
    """Blender 侧几何自检，返回 0/1。"""
    if not os.path.exists(blend):
        print(f"找不到 .blend：{blend}", file=sys.stderr)
        return 2
    out = os.path.join(os.environ.get("TEMP", "."), "grandhall_geom.json")
    blender = os.environ.get("BLENDER_EXE",
                             r"E:\SteamLibrary\steamapps\common\Blender\blender.exe")
    cmd = [blender, "-b", blend, "--factory-startup", "-P",
           os.path.join(HERE, "geom.py"), "--", "--out", out]
    proc = subprocess.run(cmd, timeout=1200, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    for line in (proc.stdout or "").splitlines():
        if line.startswith("GEOM"):
            print(line, flush=True)
    if "GEOM_DONE" not in (proc.stdout or ""):
        print(proc.stderr[-2000:], file=sys.stderr)
        print("几何自检没跑完（Blender 脚本报错也返回 0，这里按 GEOM_DONE 判定）",
              file=sys.stderr)
        return 1
    import json as _json
    try:
        with open(out, encoding="utf-8") as fh:
            doc = _json.load(fh)
    except Exception:
        return 1
    fresh = doc.get("overlap_total", 0)
    float_n = len(doc.get("floating", []))
    inv = len(doc.get("inverted", []))
    dup = len(doc.get("duplicate_bbox", []))
    print(f"  未登记互穿 {fresh} 对（白名单另计 {doc.get('overlap_known', 0)}）、"
          f"悬空 {float_n}、法线内翻 {inv}、重合 {dup}")
    for p in doc.get("overlap", [])[:5]:
        print(f"    · {p['a']} × {p['b']}（bbox 面 {p['bbox_faces']}）")
    return 1 if (float_n or inv or dup) else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=DEFAULT_MANIFEST)
    ap.add_argument("--no-shots", action="store_true")
    ap.add_argument("--diff", default="", help="上一个 manifest；只出有变化的机位")
    ap.add_argument("--geom", action="store_true",
                    help="另跑几何自检（互穿/悬空/法线/重合，需 Blender + .blend，约 3 s）")
    ap.add_argument("--blend", default=os.path.join(os.environ.get("LOCALAPPDATA", ""),
                                                    "Temp", "grandhall",
                                                    "grandhall_precise.blend"))
    ap.add_argument("--fail-on-warn", action="store_true")
    ap.add_argument("--res", type=int, default=1280)
    args = ap.parse_args()

    t0 = time.time()
    print("=" * 62)
    print("① 断言（不需要 Blender）")
    print("=" * 62, flush=True)
    a = [os.path.join(HERE, "asserts.py"), "--manifest", args.manifest]
    if args.fail_on_warn:
        a.append("--fail-on-warn")
    rc = run("asserts.py", a[1:])
    if rc == 2:
        return 2

    if args.geom:
        print("\n" + "=" * 62)
        print("①b 几何自检（Blender）")
        print("=" * 62, flush=True)
        rc_geom = run_geom(args.blend)
        rc = rc or rc_geom

    if args.no_shots:
        print(f"\n（跳过出图，共 {time.time() - t0:.1f} s）")
        return rc

    print("\n" + "=" * 62)
    print("② 接触表")
    print("=" * 62, flush=True)
    shots = ["--res", str(args.res)]
    if args.diff:
        if not os.path.exists(args.diff):
            print(f"--diff 指向的 manifest 不存在：{args.diff}", file=sys.stderr)
            return 2
        names = affected(args.diff, args.manifest)
        if not names:
            print("相对上一份 manifest 没有几何变化 —— 一张图都不用重出。")
            return rc
        print(f"只出受影响机位 {len(names)} 个：{'，'.join(names)}")
        shots += ["--only", ",".join(names)]
    run("run_shots.py", shots)

    print(f"\n合计 {time.time() - t0:.1f} s"
          f"（断言 rc={rc}；接触表见 $TEMP/grandhall_shots/contact.png）")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
