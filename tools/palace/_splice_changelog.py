"""把一段 CHANGELOG 条目插到 '### 变更' 的下一行（保持文件原有的 CRLF，不整篇改写）。

用法： PYTHONIOENCODING=utf-8 py -3 tools/palace/_splice_changelog.py <条目.md>
条目里不要带行首空行；重复插入会被首行查重挡下。
"""
import io
import os
import sys

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
cl = os.path.join(root, "CHANGELOG.md")
src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.environ["TEMP"], "palace_massing", "round52.md")

entry = io.open(src, encoding="utf-8").read().replace("\r\n", "\n").replace("\n", "\r\n")
if not entry.endswith("\r\n"):
    entry += "\r\n"

b = io.open(cl, "rb").read()
anchor = "### 变更\r\n\r\n".encode("utf-8")
assert b.count(anchor) == 1, b.count(anchor)
if entry.split("\r\n")[0].encode("utf-8") in b:
    raise SystemExit("already inserted")
b = b.replace(anchor, anchor + entry.encode("utf-8"))
io.open(cl, "wb").write(b)
print("inserted", len(entry), "chars; file now", len(b), "bytes")
