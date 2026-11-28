"""manifest 读写：一份口径，两个生产者（build_hall.py / shots.py）共用。

schema（2026-11-28 与作品会话来定）：
    {"mode": "precise|massing", "objects": <int>, "triangles": <int>,
     "seats": <int|null>, "items": [{"name","group","tris","min":[3],"max":[3]}]}

历史兼容：本目录第一版 shots.py 曾用 `{objects:[...], bbox:{min,max}}`。
`load()` 两种都认，但写出一律用上面这套——否则两个生产者各写一种，
diff 出来的“改了哪些物体”就会对不上。
"""
from __future__ import annotations

import json


def load(path):
    """→ (doc, items, totals)；items 统一成 {name, group, tris, min, max}。"""
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    raw = doc.get("items")
    if raw is None and isinstance(doc.get("objects"), list):
        raw = doc["objects"]
    items = []
    for it in raw or []:
        if "bbox" in it:
            mn, mx = it["bbox"]["min"], it["bbox"]["max"]
        else:
            mn, mx = it["min"], it["max"]
        items.append({"name": it["name"], "group": it.get("group") or "hall",
                      "tris": it.get("tris", 0),
                      "min": list(mn), "max": list(mx)})
    totals = {
        "objects": doc["objects"] if isinstance(doc.get("objects"), int) else len(items),
        "tris": (doc.get("triangles")
                 or (doc.get("totals") or {}).get("tris")
                 or sum(i["tris"] for i in items)),
        "seats": doc.get("seats"),
    }
    return doc, items, totals


def save(path, mode, items, seats=None, extra=None):
    """按统一 schema 落盘。"""
    doc = {"mode": mode, "objects": len(items),
           "triangles": sum(i["tris"] for i in items), "seats": seats,
           "items": sorted(items, key=lambda d: d["name"])}
    if extra:
        doc.update(extra)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    return doc
