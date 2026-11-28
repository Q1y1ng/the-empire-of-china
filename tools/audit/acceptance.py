"""验收账本：作者说的每一条，变成一条可执行的账。

为什么需要它：作者一天走进模型 5 次，每次说的话都是**规格**——
“座椅没贴合”“二层过不去”“后区太空”。这些话不进代码，就只能等下一次
再被说一遍。账本把它们钉成：一条原话 → 一个类型 → 一条断言（或一个待裁项）。

于是“提效”变成复利：作者提过 N 条，构建时机器挡 N 条，作者只需要看新的。

用法：
    py -3 tools/audit/acceptance.py                 # 全部条目（按状态分组）
    py -3 tools/audit/acceptance.py --open          # 只看还没守住的
    py -3 tools/audit/acceptance.py --close A-001   # 标记已解决（需 --status）
    py -3 tools/audit/acceptance.py --add "原话" --kind 关系 --assert xxx

退出码：0；有 open 项且 --strict 时 1。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

try:                      # MSYS bash 里控制台是 UTF-8，Python 默认 cp936 会输出乱码
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
BOOK = os.path.join(HERE, "acceptance.json")
STATUS = ("open", "asserted", "fixed", "spec")
KINDS = ("几何", "关系", "规格", "语义")


def load(path=BOOK):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save(doc, path=BOOK):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)


def counts(doc):
    c = {s: 0 for s in STATUS}
    for it in doc["items"]:
        c[it.get("status", "open")] = c.get(it.get("status", "open"), 0) + 1
    return c


def open_items(doc):
    return [it for it in doc["items"] if it.get("status") in ("open", "spec")]


def render(doc, only_open=False):
    items = open_items(doc) if only_open else doc["items"]
    order = {"open": 0, "spec": 1, "asserted": 2, "fixed": 3}
    items = sorted(items, key=lambda x: (order.get(x.get("status"), 9), x["id"]))
    for it in items:
        a = it.get("assert") or "（无断言）"
        print(f"{it['id']}  [{it.get('status','?'):8s}] {it.get('kind','?'):3s}  {it['date']}")
        print(f"    “{it['quote']}”")
        print(f"    → {a}" + (f"   {it['note']}" if it.get("note") else ""))
    c = counts(doc)
    print(f"\n合计 {len(doc['items'])} 条："
          + "，".join(f"{k} {v}" for k, v in c.items() if v))
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", default=BOOK)
    ap.add_argument("--open", action="store_true")
    ap.add_argument("--strict", action="store_true", help="有 open/spec 就返回 1")
    ap.add_argument("--json", default="")
    ap.add_argument("--add", default="")
    ap.add_argument("--kind", default="关系", choices=KINDS)
    ap.add_argument("--assert", dest="assertion", default=None)
    ap.add_argument("--note", default="")
    ap.add_argument("--close", default="", help="条目 id")
    ap.add_argument("--status", default="fixed", choices=STATUS)
    args = ap.parse_args()

    doc = load(args.book)

    if args.add:
        n = max([int(i["id"].split("-")[1]) for i in doc["items"]] or [0]) + 1
        doc["items"].append({"id": f"A-{n:03d}",
                             "date": time.strftime("%Y-%m-%d"),
                             "quote": args.add, "kind": args.kind,
                             "assert": args.assertion, "status": "open",
                             "note": args.note})
        save(doc, args.book)
        print(f"已加 A-{n:03d}")

    if args.close:
        hit = [i for i in doc["items"] if i["id"] == args.close]
        if not hit:
            print(f"没有 {args.close}", file=sys.stderr)
            return 2
        hit[0]["status"] = args.status
        save(doc, args.book)
        print(f"{args.close} → {args.status}")

    render(doc, only_open=args.open)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"counts": counts(doc), "open": open_items(doc)},
                      fh, ensure_ascii=False, indent=1)

    if args.strict and open_items(doc):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
