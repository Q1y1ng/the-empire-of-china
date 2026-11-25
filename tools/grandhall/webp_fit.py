"""把 %TEMP%/hall_fit 下的套合试验 PNG 转成 WebP q92 写入 docs/assets。"""
from __future__ import annotations

import os

from PIL import Image

SRC = os.path.join(os.environ["TEMP"], "hall_fit")
DST = r"E:\AI\帝国\docs\assets"
JOBS = [
    ("套合试验·正立面.png", "国家广场(2026)·大会堂套合试验·正立面.webp"),
]
for src, dst in JOBS:
    p = os.path.join(SRC, src)
    im = Image.open(p).convert("RGB")
    out = os.path.join(DST, dst)
    im.save(out, "WEBP", quality=92, method=6)
    print(dst, im.size, round(os.path.getsize(out) / 1024, 1), "KB", flush=True)
