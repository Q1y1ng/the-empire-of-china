# -*- coding: utf-8 -*-
"""把 Markdown 编译成指定页的 PNG 预览（排版调参用，不产出 PDF）。

用法：
    py -3 tools/preview_pages.py 中华帝国设定全书(2026).md --pages 2,33,40
    py -3 tools/preview_pages.py 中华帝国设定集·全卷合订本(2026).md --pages 5 --style roster
输出：%TEMP%/empire_preview/preview-<页码>.png
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("md")
    ap.add_argument("--pages", default="1")
    ap.add_argument("--style", default="setting", choices=["setting", "roster"])
    ap.add_argument("--dpi", default="160")
    args = ap.parse_args()

    from build_setting_book import (TYPST_ROSTER_INJECT, TYPST_SETTING_INJECT,
                                fix_divider, fix_escaped_bold, fix_figure)

    inject = TYPST_SETTING_INJECT if args.style == "setting" else TYPST_ROSTER_INJECT
    md = args.md if os.path.isabs(args.md) else os.path.join(ROOT, args.md)
    outdir = os.path.join(tempfile.gettempdir(), "empire_preview")
    os.makedirs(outdir, exist_ok=True)
    tmp_typ = os.path.join(outdir, "preview.typ")
    subprocess.run(["pandoc", "-f", "gfm", "--wrap=none", md, "-t", "typst", "-o", tmp_typ], check=True)
    with open(tmp_typ, encoding="utf-8") as fh:
        body = fh.read()
    with open(tmp_typ, "w", encoding="utf-8") as fh:
        fh.write(inject + fix_figure(fix_divider(fix_escaped_bold(body))))
    out = os.path.join(outdir, "preview-{p}.png")
    subprocess.run(["typst", "compile", "--format", "png", "--ppi", args.dpi,
                    "--pages", args.pages, tmp_typ, out], check=True)
    for p in args.pages.split(","):
        path = os.path.join(outdir, f"preview-{p.strip()}.png")
        print(f"[预览] {path} ({os.path.getsize(path) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
