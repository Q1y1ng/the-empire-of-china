"""一条命令出接触表：`py -3 tools/audit/run_shots.py`

做的事：
  1. 把 .blend 复制到临时目录（它每次构建都被覆盖，别在渲染时被人写坏）；
  2. 调 Blender 无头跑 shots.py（Workbench，16 站位，默认 1280×720）；
  3. 调 sheet.py 拼成一张 contact.png。

为什么复制：作品会话说 `.blend` 在 `%LOCALAPPDATA%\\Temp\\grandhall\\`，
每次构建覆盖。并发时直接读会读到半截文件。

常用：
    py -3 tools/audit/run_shots.py                     # 全部站位
    py -3 tools/audit/run_shots.py --only 座椅落地,二层净空
    py -3 tools/audit/run_shots.py --manifest "$TEMP/gm/manifest.json"
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time

try:                      # MSYS bash 里控制台是 UTF-8，Python 默认 cp936 会输出乱码
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DEFAULT_BLEND = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp",
                             "grandhall", "grandhall_precise.blend")
DEFAULT_BLENDER = r"E:\SteamLibrary\steamapps\common\Blender\blender.exe"
TIMEOUT = 900


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blend", default=DEFAULT_BLEND)
    ap.add_argument("--out", default=os.path.join(os.environ.get("TEMP", "."),
                                                  "grandhall_shots"))
    ap.add_argument("--res", type=int, default=1280)
    ap.add_argument("--color", choices=("group", "material"), default="group")
    ap.add_argument("--exposure", type=float, default=0.7)
    ap.add_argument("--only", default="")
    ap.add_argument("--manifest", default="")
    ap.add_argument("--no-copy", action="store_true")
    ap.add_argument("--no-sheet", action="store_true")
    ap.add_argument("--blender", default=os.environ.get("BLENDER_EXE", DEFAULT_BLENDER))
    args = ap.parse_args()

    if not os.path.exists(args.blender):
        print(f"找不到 Blender：{args.blender}\n用 --blender 或 BLENDER_EXE 指定", file=sys.stderr)
        return 2
    if not os.path.exists(args.blend):
        print(f"找不到 .blend：{args.blend}\n先跑一次 build_hall.py，或用 --blend 指定",
              file=sys.stderr)
        return 2

    blend = args.blend
    if not args.no_copy:
        stage = os.path.join(args.out, "_blend")
        os.makedirs(stage, exist_ok=True)
        blend = os.path.join(stage, os.path.basename(args.blend))
        shutil.copy2(args.blend, blend)

    os.makedirs(args.out, exist_ok=True)
    # 清掉上一轮的 PNG：Blender 出错时返回码仍是 0，否则 sheet.py 会拿旧图拼，
    # 让人以为“这轮跑过了”（踩过一次）。
    for fn in os.listdir(args.out):
        if fn.endswith(".png"):
            os.remove(os.path.join(args.out, fn))
    cmd = [args.blender, "-b", blend, "--factory-startup", "-P",
           os.path.join(HERE, "shots.py"), "--", "--out", args.out,
           "--res", str(args.res), "--color", args.color,
           "--exposure", str(args.exposure)]
    if args.only:
        cmd += ["--only", args.only]
    if args.manifest:
        cmd += ["--manifest", args.manifest]

    t0 = time.time()
    print("RUN", " ".join(f'"{c}"' if " " in c else c for c in cmd), flush=True)
    proc = subprocess.run(cmd, timeout=TIMEOUT, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    for line in (proc.stdout or "").splitlines():
        if line.startswith(("SHOT", "ENGINE", "RESULT", "MANIFEST", "VIEWPORT",
                            "OBJECT_COLORS", "SHADING", "Error", "Traceback")):
            print(line, flush=True)
    if proc.returncode != 0 or "RESULT " not in (proc.stdout or ""):
        print(proc.stderr[-3000:], file=sys.stderr)
        print(f"BLENDER 失败 rc={proc.returncode}（注意：Blender 脚本报错时也返回 0）",
              file=sys.stderr)
        return 1

    print(f"BLENDER OK {time.time() - t0:.1f} s")

    if not args.no_sheet:
        out = os.path.join(args.out, "contact.png")
        rc = subprocess.call([sys.executable, os.path.join(HERE, "sheet.py"),
                              "--dir", args.out, "--out", out])
        if rc != 0:
            return rc
        print(f"SHEET {out}")
    print(f"TOTAL {time.time() - t0:.1f} s  →  {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
