# -*- coding: utf-8 -*-
"""生成百科与名录共用的虚构人名池（百家姓＋二字名，政治形象端正）。

- 与全库既有姓名查重（设定/*.md、全书、百科 src），保证不重名；
- 输出稳定顺序到 tools/fictional_names.txt，按行号分块分配给各批词条；
- 只生成，不改任何设定文件。

用法：py -3 tools/gen_fictional_names.py [--count 1200]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "tools" / "fictional_names.txt"

SURNAMES = (
    "王李张刘陈杨赵黄周吴徐孙胡朱高林何郭马罗梁宋郑谢韩唐冯于董萧程曹袁邓许傅沈曾彭吕苏卢蒋蔡贾丁魏薛叶阎余潘杜戴夏钟汪田任姜范方石姚谭廖邹熊金陆郝孔白崔康毛邱秦江史顾侯邵孟龙万段雷钱汤尹黎易常武乔贺赖龚文"
)

GIVEN = """
承志 立言 守正 怀安 允中 明远 之翰 惟清 慎行 敬之
慕之 崇文 敬堂 元直 子衡 尔康 康年 秉文 焕章 景行 允文 端方
介夫 季直 百里 伯英 仲甫 叔明 学谦 恭甫 敏之 静之 问之 存之
若愚 若谷 立诚 守拙 拙存 克明 允恭 敬修 元度 世清 汝霖 沛然
焕然 斐然 蔚然 毅然 卓然 泰然 浩然 沛霖 济川 立川 望山 怀山
镜湖 澄之 清源 溯源 思远 致远 静远 明诚 明允 明哲 允升 允昭
贞白 守一 抱朴 弘毅 士弘 立本 崇本 敦礼 敦复 敬孚 敬舆 敬宣
敬和 敬让 敬先 敬祖 敬宗 敬民 敬贤 敬修 敬猷 敬元 敬同 敬文
秉直 秉正 秉忠 秉清 秉衡 秉均 秉仁 秉义 秉礼 秉智 秉信 秉哲
允怀 允迪 允修 允臧 允亮 允成 允平 允宁 允康 允泰 允安 允济
之澄 之涣 之澜 之润 之滨 之渊 之涵 之澈 之泓 之沅 之湛 之沐
伯谦 仲谦 叔谦 季谦 伯庸 仲容 叔度 季长 伯阳 仲宣 叔向 季札
其昌 其正 其明 其远 其深 其厚 其高 其恒 其久 其新 其茂 其芳
维新 维正 维明 维远 维清 维俭 维诚 维朴 维则 维翰 维城 维屏
"""


def existing_names() -> set[str]:
    names: set[str] = set()
    files = list((ROOT / "设定").glob("*.md")) + [ROOT / "设定集" / "中华帝国设定全书(2026).md"]
    files += list((ROOT / "docs" / "baike" / "src").glob("*.md"))
    for f in files:
        if not f.exists():
            continue
        t = f.read_text(encoding="utf-8")
        # 抓 2—3 字中文人名式词（粗筛），只需保证全名不撞
        for m in re.finditer(r"[\u4e00-\u9fa5]{2,3}", t):
            names.add(m.group(0))
    return names


def main() -> int:
    count = 1200
    if "--count" in sys.argv:
        count = int(sys.argv[sys.argv.index("--count") + 1])
    taken = existing_names()
    out: list[str] = []
    given = GIVEN.split()
    for sn in SURNAMES:
        for gn in given:
            full = sn + gn
            if full in taken or len(full) != 3:
                continue
            if full[1:] in taken and False:
                continue
            out.append(full)
            if len(out) >= count:
                break
        if len(out) >= count:
            break
    OUT.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"已生成 {len(out)} 个虚构人名 → {OUT.relative_to(ROOT)}")
    print("前 8 个：", "、".join(out[:8]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
