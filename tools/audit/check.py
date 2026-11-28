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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=DEFAULT_MANIFEST)
    ap.add_argument("--no-shots", action="store_true")
    ap.add_argument("--diff", default="", help="上一个 manifest；只出有变化的机位")
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
