"""解析 GLB 头与 JSON 块：核对 Draco 扩展、材质、贴图与外部依赖。"""
import io
import json
import os
import struct

p = r"E:\AI\帝国\docs\assets\国家广场(2026)·精模·含万人大礼堂.glb"
data = io.open(p, "rb").read()
magic, ver, length = struct.unpack_from("<4sII", data, 0)
assert magic == b"glTF", magic
off = 12
chunk_len, chunk_type = struct.unpack_from("<II", data, off)
js = json.loads(data[off + 8: off + 8 + chunk_len].decode("utf-8"))
print("version", ver, "bytes", length, "chunks_ok", chunk_type == 0x4E4F534A)
print("extensionsUsed", js.get("extensionsUsed"))
print("extensionsRequired", js.get("extensionsRequired"))
print("nodes", len(js.get("nodes", [])), "meshes", len(js.get("meshes", [])),
      "materials", len(js.get("materials", [])),
      "images", len(js.get("images", [])), "textures", len(js.get("textures", [])),
      "buffers", [b.get("uri", "<embedded>") for b in js.get("buffers", [])])
ext_img = [i for i, im in enumerate(js.get("images", [])) if "uri" in im]
print("images_with_external_uri", len(ext_img))
print("image_mimes", sorted({im.get("mimeType") for im in js.get("images", [])}))
scenes = js.get("scenes", [])
print("scenes", len(scenes), "root_nodes", len(scenes[0]["nodes"]) if scenes else 0)
print("asset", js.get("asset"))
