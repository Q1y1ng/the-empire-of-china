"""断言自检：篡改 manifest，确认对应的断言**真的会红**。

    py -3 tools/audit/selftest.py                        # 用 build/hall_manifest.json
    py -3 tools/audit/selftest.py --manifest X.json

为什么要有这一层：一条永远 PASS 的断言比没有更糟——它让人以为查过了。
所以每条断言都得能被「已知的真实缺陷形态」弄红。这里把缺陷注入 manifest 副本，
要求目标断言 FAIL、原样 PASS。

新增断言时，至少在这里补一条能弄红它的注入；跑不通说明断言的判据写虚了。
（`seat.forward` 的 5 条注入对应作者 2026-11-28 抓到的「主席团九椅背对观众」，
  以及模板翻半圈、零向量、两端口径不同源这三种同族缺陷。）

退出码：0 全部符合预期；1 有注入没被抓到（断言虚设）；2 环境/文件问题。
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DEFAULT_MANIFEST = os.path.join(ROOT, "build", "hall_manifest.json")
ASSERTS = os.path.join(HERE, "asserts.py")


def _groups(doc, key):
    return [g for g in doc["seat_facing"]["groups"] if g["group"] == key]


def _flip(doc, key):
    for g in _groups(doc, key):
        for s in g["samples"]:
            s[2], s[3], s[4] = -s[2], -s[3], -s[4]


def _turn90(doc, key):
    g = _groups(doc, key)[0]
    s = g["samples"][len(g["samples"]) // 2]
    s[2], s[3] = -s[3], s[2]


def _zero(doc, key):
    s = _groups(doc, key)[0]["samples"][0]
    s[2] = s[3] = 0.0


def _shrink_report(doc, key):
    _groups(doc, key)[0]["cos_max"] = 0.5


def _aim_lie(doc, key):
    _groups(doc, key)[0]["aim"] = "focus"


CASES = [
    ("seat.forward", "主席团椅背翻到 +x 侧（朝向 −x）", lambda d: _flip(d, "主席团座椅")),
    ("seat.forward", "整套池座模板翻半圈", lambda d: _flip(d, "座席0")),
    ("seat.forward", "单座绕轴转 90°", lambda d: _turn90(d, "座席1")),
    ("seat.forward", "朝向退化成零向量", lambda d: _zero(d, "座席0")),
    ("seat.forward", "构建端报告区间被改小", lambda d: _shrink_report(d, "座席2")),
    ("seat.forward", "role 与基准方向不匹配", lambda d: _aim_lie(d, "主席团座椅")),
]


def run_asserts(path):
    proc = subprocess.run([sys.executable, ASSERTS, "--manifest", path],
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=300)
    return proc.returncode, proc.stdout


def verdict(out, name):
    """从断言输出里取某条断言的 PASS/FAIL 字。"""
    for line in out.splitlines():
        if line.startswith("[") and name in line:
            return line[1:line.index("]")].strip()
    return "?"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=DEFAULT_MANIFEST)
    args = ap.parse_args()
    if not os.path.exists(args.manifest):
        print(f"找不到 manifest：{args.manifest}", file=sys.stderr)
        return 2

    src = json.load(open(args.manifest, encoding="utf-8"))
    if not (src.get("seat_facing") or {}).get("groups"):
        print("manifest 里没有 seat_facing——先按最新代码重建一次", file=sys.stderr)
        return 2

    tmp = os.path.join(tempfile.gettempdir(), "hall_manifest_selftest.json")
    bad = 0

    rc, out = run_asserts(args.manifest)
    base = verdict(out, "seat.forward")
    ok = rc == 0 and base == "PASS"
    print(f"[{'OK ' if ok else 'BAD'}] 对照：原样 manifest → seat.forward {base}（exit {rc}）")
    bad += 0 if ok else 1

    for name, what, mutate in CASES:
        doc = copy.deepcopy(src)
        mutate(doc)
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False)
        rc, out = run_asserts(tmp)
        got = verdict(out, name)
        ok = rc != 0 and got == "FAIL"
        print(f"[{'OK ' if ok else 'BAD'}] 注入「{what}」→ {name} {got}（exit {rc}）")
        bad += 0 if ok else 1

    print(f"\n合计：{len(CASES) + 1 - bad} 符合预期 / {bad} 未被抓住")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
