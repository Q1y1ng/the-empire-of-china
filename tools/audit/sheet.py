"""把 shots.py 出的单张 PNG 拼成一张接触表（Pillow，纯 py3，不进 Blender）。

为什么拼一张：agent 一次只能“读”有限张图，13 张分开看既慢又容易漏；
拼成 3 列一张，一眼看完所有站位的关系对不对。

用法：
    py -3 sheet.py --dir "$TEMP/grandhall_shots" --out contact.png [--cols 3] [--width 640]

自动从 `shots_table.load_shots()` 取站位顺序与机位参数（焦距/正交），
所以标签里的“26 mm”“ortho 246”与实际渲染一致，不会写死。
"""
from __future__ import annotations

import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFont

try:                      # MSYS bash 里控制台是 UTF-8，Python 默认 cp936 会输出乱码
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from shots_table import load_shots  # noqa: E402

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\arial.ttf",
]


def pick_font(size):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cols", type=int, default=3)
    ap.add_argument("--width", type=int, default=640, help="每格宽度（px）")
    ap.add_argument("--quality", type=int, default=92)
    args = ap.parse_args()

    table = load_shots()
    items = []
    for name, spec in table:
        path = os.path.join(args.dir, f"{name}.png")
        if not os.path.exists(path):
            continue
        if spec.get("ortho"):
            tag = f"ortho {spec['ortho']:g}"
        else:
            tag = f"{spec.get('lens', 35):g} mm"
        if spec.get("hide"):
            tag += " · hide:" + ",".join(spec["hide"])
        items.append((name, tag, path))

    if not items:
        print("没有可拼的图（先跑 shots.py）", file=sys.stderr)
        return 1

    pad, label_h, header_h = 6, 26, 34
    cell_w = args.width
    with Image.open(items[0][2]) as probe:
        cell_h = int(round(cell_w * probe.height / probe.width))

    cols = max(1, args.cols)
    rows = (len(items) + cols - 1) // cols
    W = cols * cell_w + (cols + 1) * pad
    H = header_h + rows * (cell_h + label_h) + (rows + 1) * pad
    sheet = Image.new("RGB", (W, H), (14, 15, 18))
    draw = ImageDraw.Draw(sheet)
    f_head, f_name, f_tag = pick_font(18), pick_font(17), pick_font(14)

    draw.text((pad + 2, 8),
              f"接触表 {len(items)} 机位 · Workbench（只判关系，不判观感）",
              font=f_head, fill=(226, 232, 240))

    for i, (name, tag, path) in enumerate(items):
        r, c = divmod(i, cols)
        x = pad + c * (cell_w + pad)
        y = header_h + pad + r * (cell_h + label_h + pad)
        with Image.open(path) as im:
            im = im.convert("RGB").resize((cell_w, cell_h), Image.LANCZOS)
            sheet.paste(im, (x, y))
        draw.rectangle([x, y, x + cell_w - 1, y + cell_h - 1], outline=(58, 62, 70))
        draw.text((x, y + cell_h + 3), f"{i + 1:02d} {name}", font=f_name,
                  fill=(240, 244, 248))
        draw.text((x, y + cell_h + 3), "", font=f_tag, fill=(0, 0, 0))
        tw = draw.textlength(tag, font=f_tag)
        draw.text((x + cell_w - tw - 2, y + cell_h + 5), tag,
                  font=f_tag, fill=(148, 163, 184))

    sheet.save(args.out, quality=args.quality)
    if args.out.lower().endswith(".png"):
        sheet.save(args.out, optimize=True)
    print(f"SHEET {args.out} {W}x{H} {len(items)} 格")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
