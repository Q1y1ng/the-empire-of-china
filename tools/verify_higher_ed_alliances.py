from pathlib import Path
import re

text = Path(r"E:\AI\帝国\设定\全国高等教育设定(2026).md").read_text(encoding="utf-8")

for term in ["国立大学联合体", "全国一流大学", "全国一流学科", "联盟五档"]:
    print(f"residual {term}:", text.count(term))


def count_school_rows(section: str) -> list[str]:
    rows = []
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        if re.match(r"^\|\s*序\s*\|", line) or re.match(r"^\|\s*校名\s*\|", line):
            continue
        if re.match(r"^\|[\s\-:|]+\|$", line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 2 and cells[0] and not cells[0].startswith("**"):
            rows.append(cells[0])
    return rows


m3 = re.search(r"### 三、W45.*?\n### 四、", text, re.S)
rows3 = count_school_rows(m3.group(0))
print("W45 non-C9 rows:", len(rows3))
print("sample:", rows3[:3], "...", rows3[-3:])

m5 = re.search(r"### 五、国内一流大学.*?\n### 六、", text, re.S)
rows5 = count_school_rows(m5.group(0))
print("国内一流大学 extra50 rows:", len(rows5))

m6 = re.search(r"### 六、国内一流学科.*?\n### 七、", text, re.S)
rows6 = count_school_rows(m6.group(0))
print("国内一流学科 extra135 rows:", len(rows6))

m1 = re.search(r"### 一、中央科学教育.*?\n### 二、", text, re.S)
c9 = re.findall(r"^\|\s*(\d+)\s*\|", m1.group(0), re.M)
print("C9 numbered:", c9)

m7 = re.search(r"### 七、长安集团.*?\n---", text, re.S)
rows7 = re.findall(r"^\| \d+ \|", m7.group(0), re.M) if m7 else []
print("长安集团 rows:", len(rows7))

print("arith:", 12 + 86 + 195, 21 + 53 + 53, 293 + 127)
print("nested:", 9 + 36, 45 + 50, 95 + 135)
print("--- checks done ---")
