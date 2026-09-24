# -*- coding: utf-8 -*-
"""州级行政机关「部」→「厅」：仅改州级行政机构名与对应官称。"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1] / "设定"

# 州级行政组成机关词根（不含政治口「组织」）
STEMS = [
    "经济发展",
    "财政",
    "教育",
    "科技工业",
    "公安",
    "民政",
    "司法",
    "人力资源和社会保障",
    "自然资源与生态环境",
    "自然资源",
    "生态环境",
    "住房与城乡建设",
    "交通运输",
    "交通",
    "水利与农业粮食",
    "水利",
    "农业粮食",
    "商务与贸易",
    "商务",
    "贸易",
    "宣传",
    "文化旅游",
    "文化",
    "旅游",
    "卫生健康",
    "卫生",
    "应急",
    "市场监督",
    "市场监督管理",
    "国有资产监督管理",
    "国有资产",
    "审计",
    "医疗保障",
    "医疗",
    "退役军人事务",
    "退役",
    "国防动员",
    "国防",
    "对外贸易",
    "科技",
    "工业",
    "发展改革",
    "发展",
]

# 长词根优先，避免「财政」吃掉「财政部办公厅」之类的边界问题
STEMS = sorted(set(STEMS), key=len, reverse=True)

# 可能的州名前缀（含「州」本身与各专名）
STATE_PREFIX = r"(?:[一-鿿]{0,6}州)"

files = sorted(ROOT.rglob("*.md"))
total = 0
changed_files = []

for path in files:
    text = path.read_text(encoding="utf-8")
    orig = text

    # 1) 官称：州…X部部长 → 州…X厅厅长（先做，避免变成「厅部长」）
    for s in STEMS:
        text = re.sub(
            rf"({STATE_PREFIX}{re.escape(s)})部部长",
            r"\1厅厅长",
            text,
        )
        # 「华北州财政部长」式：部+长（无「部」重复）
        text = re.sub(
            rf"({STATE_PREFIX}{re.escape(s)})部长",
            r"\1厅长",
            text,
        )

    # 2) 机构名：州…X部 → 州…X厅（后面不再跟「委/署/局/会/办/校/院」等）
    for s in STEMS:
        text = re.sub(
            rf"({STATE_PREFIX}{re.escape(s)})部(?![委署局会办校院科室队站所集团银行公司])",
            r"\1厅",
            text,
        )

    # 3) 专名里夹的：「（州财政部·卷六现任）」已由 2 覆盖
    # 「部长向州长负责」→「厅长向州长负责」（仅州宣传语境；若已改过厅长则跳过）
    text = text.replace("州宣传厅（州政府管辖，部长向州长负责", "州宣传厅（州政府管辖，厅长向州长负责")
    text = text.replace("州宣传厅**由州政府管辖**，部长向州长负责", "州宣传厅**由州政府管辖**，厅长向州长负责")
    text = text.replace("州宣传部（州政府管辖，部长向州长负责", "州宣传厅（州政府管辖，厅长向州长负责")
    text = text.replace("州宣传部**由州政府管辖**，部长向州长负责", "州宣传厅**由州政府管辖**，厅长向州长负责")

    # 4) 审计链缩写
    text = text.replace("帝国审计院→州审计部", "帝国审计院→州审计厅")
    text = text.replace("帝国审计院 → 州审计部", "帝国审计院 → 州审计厅")

    if text != orig:
        path.write_text(text, encoding="utf-8")
        n = sum(1 for a, b in zip(orig.splitlines(), text.splitlines()) if a != b)
        # 粗略：行数差可能为 0（同行替换），用字符差近似
        changed_files.append((path.name, abs(len(text) - len(orig))))
        total += 1

print(f"changed_files={total}")
for name, delta in changed_files:
    print(f"  {name}  Δchars≈{delta}")
