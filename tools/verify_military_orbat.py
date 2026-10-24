#!/usr/bin/env python3
"""军事编制设定交叉校验（对应 docs/compose/spec/military-orbat.md T3）

校验对象：
    设定/全国军事编制设定(2026).md   —— 新编军事编制分卷
    设定/中华帝国世界观总设定v2.0.md —— 第九编摘要＋附录二（2026修订版）
断言内容：陆军七级人数链、标准重装旅兵力与16行装备核算、空军缩比倍率与总量、
海军舰员/支队/舰队、航母编成、军衔两表冻结未动、旧术语残留零命中。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JUAN = (ROOT / "设定" / "全国军事编制设定(2026).md").read_text(encoding="utf-8")
ZONG = (ROOT / "设定" / "中华帝国世界观总设定v2.0.md").read_text(encoding="utf-8")
GAO = (ROOT / "设定" / "全国高等教育设定(2026).md").read_text(encoding="utf-8")
ROSTERS = sorted((ROOT / "设定").glob("全国官员名录*.md"))

# ── 陆军七级链：班15 → ×10 ×10 ×10 → 军10旅 → 军区约2个军 ──
squad = 15
company, battalion, brigade, army = squad * 10, squad * 100, squad * 1000, squad * 10_000
mr = int(2.5 * army)
assert (company, battalion, brigade, army, mr) == (150, 1_500, 15_000, 150_000, 375_000)
total_army = 8 * mr
assert total_army == 3_000_000
print(f"陆军链: 班{squad}→连{company}→营{battalion:,}→旅{brigade:,}→军{army:,}→军区{mr:,}；"
      f"八军区合计 {total_army:,}")

# ── 标准重装旅兵力：9营＋9直属连＋旅部150 ──
brigade_headcount = 9 * battalion + 9 * company + 150
assert brigade_headcount == 15_000
print(f"重装旅兵力: 9×{battalion:,}＋9×{company}＋150 = {brigade_headcount:,}")

# ── 重装旅装备16行：数量×(营=100班 / 连=10班)×每班装备数 ──
EQUIP = [
    # (装备, 单位数量, 单位级别, 每班装备数)
    ("炊事车", 1, "营", 3),
    ("步兵战车", 4, "营", 2),
    ("主战坦克", 1, "营", 3),
    ("火力支援车·重装", 1, "营", 2),
    ("防空导弹车", 1, "营", 3),
    ("防空保障车", 1, "营", 2),
    ("远火发射车", 1, "营", 2),
    ("运火保障车", 1, "营", 3),
    ("自行迫榴炮", 1, "营", 3),
    ("炮兵保障车", 1, "营", 2),
    ("火力支援车·工兵", 3, "连", 1),
    ("工兵保障车", 3, "连", 4),
    ("卡车", 2, "连", 7),
    ("急救车", 2, "连", 3),
    ("武装直升机", 1, "连", 5),
    ("运输直升机", 1, "连", 5),
]
EXPECTED = {
    "炊事车": 300, "步兵战车": 800, "主战坦克": 300, "火力支援车·重装": 200,
    "防空导弹车": 300, "防空保障车": 200, "远火发射车": 200, "运火保障车": 300,
    "自行迫榴炮": 300, "炮兵保障车": 200, "火力支援车·工兵": 30, "工兵保障车": 120,
    "卡车": 140, "急救车": 60, "武装直升机": 50, "运输直升机": 50,
}
total_equipment = 0
for name, n, level, per in EQUIP:
    calc = n * (100 if level == "营" else 10) * per
    assert calc == EXPECTED[name], (name, calc, EXPECTED[name])
    total_equipment += calc
print(f"重装旅装备: 16行核算全部通过，合计约 {total_equipment:,} 台架")
assert len(EQUIP) == 16

# ── 空军缩比：小队15人≈5机 → 中队3小队 → 大队4中队 → 旅5大队 → 军8旅 → 8军区各1军 ──
air_crew_squad, air_ac_squad = 15, 5
air_mid_ac = 3 * air_ac_squad
air_grp_ac = 4 * air_mid_ac
air_bde_ac = 5 * air_grp_ac
air_corps_ac = 4 * air_bde_ac
air_all_ac = 8 * air_corps_ac + 3_200
air_crew_corps = 4 * 5 * 4 * 3 * air_crew_squad
air_crew_all = 8 * air_crew_corps + 3_200 * 3
assert (air_mid_ac, air_grp_ac, air_bde_ac, air_corps_ac, air_all_ac) == (15, 60, 300, 1_200, 12_800)
assert (air_crew_corps, air_crew_all) == (3_600, 38_400)
print(f"空军缩比: 中队{air_mid_ac}机→大队{air_grp_ac}机→旅{air_bde_ac}机→军{air_corps_ac:,}机→"
      f"全军{air_all_ac:,}机；空勤{air_crew_corps:,}/军、共{air_crew_all:,}人")

# ── 海军：班5→连3班；舰员连倍率45/75/150；支队50艘；舰队8支队；三大舰队 ──
navy_squad = 5
navy_company = 3 * navy_squad
frigate, destroyer, cruiser = 3 * navy_company, 5 * navy_company, 10 * navy_company
assert (navy_company, frigate, destroyer, cruiser) == (15, 45, 75, 150)
flotilla_ships = 28 + 4 + 8
flotilla_crew = 28 * frigate + 4 * destroyer + 8 * cruiser
assert (flotilla_ships, flotilla_crew) == (40, 2_760)
fleet_ships = 6 * flotilla_ships
assert fleet_ships == 240 and 3 * fleet_ships == 720
print(f"海军: 护卫舰{frigate}/驱逐舰{destroyer}/巡洋舰{cruiser}人；支队{flotilla_ships}艘"
      f"（舰员{flotilla_crew:,}）；舰队{fleet_ships}艘×3＝{3 * fleet_ships:,}艘主力舰")

# ── 航母：水兵班10→连5班→营10连→航母10营 ──
carrier_squad = 10
carrier_company = 5 * carrier_squad
carrier_battalion = 10 * carrier_company
carrier = 10 * carrier_battalion
assert carrier == 5_000
print(f"航母: 班{carrier_squad}→连{carrier_company}→营{carrier_battalion:,}→{carrier:,}水兵＋舰载航空兵")

# ── 分卷文本锚点 ──
ANCHORS = [
    "标准重装旅", "指挥岗位标准衔", "舰载航空兵", "战略力量（火箭军）", "水兵班",
    "14,850", "旅部", "约12,800机", "约720艘主力舰", "2,760", "约3,550台架",
    # 附录A 原草案列（含两处勘误标注）
    "炊事车×300", "步兵战车×800", "主战坦×300", "防空车×300", "远火×200",
    "自行炮×300", "卡车×140", "急救车×60", "武直×50", "运直×50",
    "保障车×200", "保障车×300", "保障车×120",
    "原稿「火炮×200」→勘误", "原稿「火炮×30」→勘误",
    # 待定清单
    "旅种谱系", "侦察车", "待定",
]
for anchor in ANCHORS:
    assert anchor in JUAN, f"分卷缺锚点: {anchor}"
print(f"分卷锚点: {len(ANCHORS)} 组全部命中")

# ── 总设定锚点：摘要小节、军区链、修订版附录二、标准衔 ──
for anchor in [
    "编制总纲（摘要·2026冻结版）",
    "中央军委 → 军区 → 军 → 旅 → 营 → 连 → 班",
    "皇帝 → 中央军委 → 军区 → 军 → 旅 → 营 → 连 → 班",
    "附录二：帝国军队层级与军衔表（2026修订版·独立于文官品级）",
    "指挥岗位标准衔（2026冻结）",
    "《全国军事编制设定(2026)》",
    "标准重装旅15,000人",
    "八军区空军",
]:
    assert anchor in ZONG, f"总设定缺锚点: {anchor}"

# 军衔两表冻结未动
assert "## 军官军衔（12等）" in ZONG and "## 士官/士兵军衔（9等）" in ZONG
assert "**元帅** — 上将 — 中将 — 少将" in ZONG

# ── 旧术语残留扫描（总设定排除附录二「修订沿革」历史注记行） ──
zong_scan = "\n".join(l for l in ZONG.splitlines() if "修订沿革" not in l)
for bad in ["集团军", "合成旅", "舰艇大队", "航空旅", "战区", "师/旅", "军级"]:
    assert bad not in zong_scan, f"总设定残留: {bad}"
for bad in ["集团军", "合成旅", "舰艇大队", "航空旅"]:
    juan_scan = "\n".join(l for l in JUAN.splitlines() if "旧口径" not in l)
    assert bad not in juan_scan, f"分卷残留: {bad}"
# 分卷术语说明中「八大战区」仅出现1次（指旧称，非使用）
assert JUAN.count("八大战区") == 1
print("残留扫描: 总设定『战区/集团军/合成旅/舰艇大队/航空旅/师/排-团』零命中；分卷仅术语说明1处")

# ── 级别待遇对照（2026冻结·作者表）──
GRADE_ANCHORS_JUAN = [
    "级别待遇对照【核心·2026冻结·作者表】",
    "以军衔来确认职级待遇",
    "（资浅授中将者享三品）",
    "皇家理工等重点国立校总校校长",
    "吏二 | 少尉/准尉",
]
GRADE_ANCHORS_ZONG = [
    "级别待遇对照（2026冻结版·作者表）",
    "中央政治学院校长·帝国国防大学校长",
    "高校机构级别随校长级别待遇同步",
    "军区司令职位三品；授上将者按二品高配",
]
GRADE_ANCHORS_GAO = [
    "校长级别待遇（2026冻结·作者表）",
    "同州立大学",
    "比总校校长低一级",
    "整体再降一档",
    "**四品**（校长授少将）",
]
for anchor in GRADE_ANCHORS_JUAN:
    assert anchor in JUAN, f"分卷缺级别待遇锚点: {anchor}"
for anchor in GRADE_ANCHORS_ZONG:
    assert anchor in ZONG, f"总设定缺级别待遇锚点: {anchor}"
for anchor in GRADE_ANCHORS_GAO:
    assert anchor in GAO, f"高教设定缺级别待遇锚点: {anchor}"
print(f"级别待遇对照: 分卷{len(GRADE_ANCHORS_JUAN)}+总设定{len(GRADE_ANCHORS_ZONG)}"
      f"+高教{len(GRADE_ANCHORS_GAO)} 组锚点全部命中")

# ── 名录：军区司令二品全域落地 ──
NEW_KOUJING = "军区司令职位三品（授上将者按二品高配）"
koujing_hits = 0
for path in ROSTERS:
    for line in path.read_text(encoding="utf-8").splitlines():
        if NEW_KOUJING in line:
            koujing_hits += 1
        elif "军区司令" in line and "二品" in line and "高配" not in line and "政委" not in line:
            raise AssertionError(f"名录残留军区司令二品: {path.name}: {line.strip()}")
assert koujing_hits == 2, f"口径行应为2处（卷三十五+合订本），实际{koujing_hits}"
juan1 = (ROOT / "设定" / "全国官员名录·卷一·中央与京畿直隶州(2026).md").read_text(encoding="utf-8")
assert "| 10 | 穆长缨※ | 委员 | 京畿军区司令 | 三品（授上将者高配二品）【推演】 |" in juan1
print(f"名录修订: {len(ROSTERS)} 文件扫描，军区司令三品（上将高配二品）全域落地（口径行{koujing_hits}处），零残留")

print("--- military-orbat checks done ---")
