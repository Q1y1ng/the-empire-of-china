# -*- coding: utf-8 -*-
"""一次性迁移：删去「谋官」概念，改为直书处分与刑罚（2026-11-15 作者指令·方案甲）

用法：py -3 tools/archive/remove_mouguan_once.py [--apply]
不带 --apply 时只做命中数断言与清单打印；带 --apply 才落盘。
每条替换都写死 old/new 与预期命中数，命中数不符即中止。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SET = '设定'
BAIKE = os.path.join('docs', 'baike', 'src')

# (相对路径, old, new, 预期命中数)
EDITS = [
    # ── 法条本体 ──
    (os.path.join(SET, '法律要目·二·组织法与人事(2026).md'),
     '**以组织形态干预任免、分配官位者，按「谋官」论处**；国家监委设关系图谱审查，可要求当事人就荐举关系、同乡同学关系作出书面说明，拒不如实说明者依情节处分。',
     '**以组织形态干预任免、分配官位者，予以免职；情节严重的，开除公职；收受财物的，按《刑法》受贿罪从重处罚。**国家监委设关系图谱审查，可要求当事人就荐举关系、同乡同学关系作出书面说明，拒不如实说明者给予降级处分。', 1),
    (os.path.join(SET, '法律要目·三·部门法(2026).md'),
     '受贿、贪污、挪用公款、私分国有资产、**以圈谋官**（以非正式关系谋取职务）五罪并列；按数额与情节分三档；',
     '受贿、贪污、挪用公款、私分国有资产**四罪并列**；以组织形态干预任免、分配官位并收受财物的，按受贿罪从重处罚；未收财物而私授官位的，处三年以下有期徒刑或者拘役。按数额与情节分三档；', 1),
    # ── 设定主干 ──
    (os.path.join(SET, '总设定·第一编·世界观总览.md'),
     '**帝国无政党；只有非正式圈子（不入册、不承认、以圈谋官即犯罪）**',
     '**帝国无政党；政治活动以个人身份与制度程序为限，非正式交往归私人领域**', 1),
    (os.path.join(SET, '总设定·第五编·现代政治制度.md'),
     '- **以圈谋官即犯罪**：《监察制度改革法》明定，以组织形态干预任免、分配官位者，按**「谋官」**论处',
     '- **人事权归制度程序**：《监察制度改革法》第六条明定，以组织形态干预任免、分配官位者，予以免职；情节严重的，开除公职；收受财物的，按《刑法》受贿罪从重处罚', 1),
    (os.path.join(SET, '帝国主数据表(2026).md'),
     '无法定政党、无党团；非正式圈子不入册、官方不承认，以圈谋官按「谋官」论处（《监察制度改革法》）',
     '无法定政党、无党团；非正式交往归私人领域；以组织形态干预任免、分配官位者予以免职，情节严重的开除公职（《监察制度改革法》第六条）', 1),
    (os.path.join(SET, '国家议会(2026).md'),
     '5. **红线**：以组织形态干预任免、分配官位者，按「谋官」论处（《监察制度改革法》）——因此圈子只谈议案，不敢碰人事',
     '5. **人事红线**：以组织形态干预任免、分配官位者，予以免职；情节严重的，开除公职（《监察制度改革法》第六条）', 1),
    (os.path.join(SET, '帝国百科·沈叙衡(2026).md'),
     '｜ 谋官论处（《监察制度改革法》第六条）',
     '｜ 人事处分（《监察制度改革法》第六条）', 1),
    (os.path.join(SET, '帝国百科·沈叙衡(2026).md'),
     '| 谋官论处 | 《监察制度改革法》第六条：以组织形态干预任免、分配官位者论罪；圈子治理的红线。 | 法律要目·监察制度改革法 |',
     '| 人事处分 | 《监察制度改革法》第六条：以组织形态干预任免、分配官位者予以免职，情节严重的开除公职。 | 法律要目·监察制度改革法 |', 1),
    # ── 百科词条 ──
    (os.path.join(BAIKE, 'quanzi.md'),
     '  主管: 国家监察委员会（按谋官论处查办）',
     '  主管: 国家监察委员会（按第六条查办）', 1),
    (os.path.join(BAIKE, 'quanzi.md'),
     '  红线: 以圈谋官按「谋官」论处',
     '  红线: 干预任免、分配官位者予以免职，情节严重的开除公职', 1),
    (os.path.join(BAIKE, 'quanzi.md'),
     '1984 年《监察制度改革法》第六条明定：以组织形态干预任免、分配官位者，按「谋官」论处。这是[[谋官论处]]的法源，也是圈子治理的唯一红线；',
     '1984 年《监察制度改革法》第六条明定：以组织形态干预任免、分配官位者，予以免职，情节严重的开除公职。这是圈子治理唯一落到人头上的规定；', 1),
    (os.path.join(BAIKE, 'quanzi.md'),
     '| 谋官论处 | 以组织形态干预任免、分配官位者论罪 | 《监察制度改革法》第六条（1984） |',
     '| 人事处分 | 干预任免、分配官位者予以免职，情节严重的开除公职 | 《监察制度改革法》第六条（1984） |', 1),
    (os.path.join(BAIKE, 'audit.md'),
     '为[[谋官论处]]的认定提供技术基础',
     '为干预任免类案件的认定提供技术基础', 1),
    (os.path.join(BAIKE, 'cheng-musong.md'),
     '以圈谋官、以抽调为名行提拔之实的，按[[谋官论处]]办理',
     '以抽调为名行提拔之实的，依《监察制度改革法》第六条办理', 1),
    (os.path.join(BAIKE, 'cheng-musong.md'),
     '监察制度改革法「谋官」条',
     '监察制度改革法第六条', 1),
    (os.path.join(BAIKE, 'discipline.md'),
     '- **查处以圈谋官**：依《监察制度改革法》第六条，对以组织形态干预任免、分配官位者按「谋官」论处；',
     '- **查处干预任免**：依《监察制度改革法》第六条，对以组织形态干预任免、分配官位者予以免职，情节严重的开除公职；', 1),
    (os.path.join(BAIKE, 'discipline.md'),
     '（无法定政党、以圈谋官按谋官论处）',
     '（无法定政党；干预任免予以免职）', 1),
    (os.path.join(BAIKE, 'du-jianchuan.md'),
     '[[谋官论处]]查[[圈子（系／圈／会）]]里的请托与举荐关系',
     '[[国家监察委员会]]查[[圈子（系／圈／会）]]里的请托与举荐关系', 1),
    (os.path.join(BAIKE, 'duoyuan-xinxi.md'),
     '这一顺序在《监察制度改革法》第六条「谋官论处」与[[谋官论处]]的关系图谱审查中体现得最清楚',
     '这一顺序在《监察制度改革法》第六条与关系图谱审查中体现得最清楚', 1),
    (os.path.join(BAIKE, 'jiancha-sifa-wei.md'),
     '以组织形态干预任免、分配官位者按[[谋官论处]]。',
     '以组织形态干预任免、分配官位者予以免职，情节严重的开除公职。', 1),
    (os.path.join(BAIKE, 'jiancha-sifa-wei.md'),
     '第六条把「以组织形态干预任免、分配官位」定为谋官',
     '第六条把「以组织形态干预任免、分配官位」定为处分事由', 1),
    (os.path.join(BAIKE, 'jiancha-sifa-wei.md'),
     '- **受理谋官线索**',
     '- **受理干预任免线索**', 1),
    (os.path.join(BAIKE, 'org.md'),
     '干部人事一旦与钱挂上钩，[[谋官论处]]就无从落地',
     '干部人事一旦与钱挂上钩，处分就无从落地', 1),
    (os.path.join(BAIKE, 'parliament.md'),
     '依《监察制度改革法》第六条按[[谋官论处]]',
     '依《监察制度改革法》第六条予以免职', 1),
    (os.path.join(BAIKE, 'qiu-jingde.md'),
     '为[[谋官论处]]的认定提供技术基础',
     '为干预任免类案件的认定提供技术基础', 2),
    (os.path.join(BAIKE, 'qu-jingyi.md'),
     '**审「谋官」类案件。** [[谋官论处]]管的是以组织形态干预任免、分配官位，依《监察制度改革法》第六条论处',
     '**审干预任免类案件。**《监察制度改革法》第六条管的是以组织形态干预任免、分配官位，依该条予以免职', 1),
    (os.path.join(BAIKE, 'supervision.md'),
     '同一条还写明红线：以组织形态干预任免、分配官位者，按[[谋官论处]]。',
     '同一条还写明：以组织形态干预任免、分配官位者，予以免职，情节严重的开除公职。', 1),
    (os.path.join(BAIKE, 'tan-jingyan.md'),
     '第二件是关系图谱审查：查[[谋官论处]]他不看饭局',
     '第二件是关系图谱审查：查干预任免，他不看饭局', 1),
    (os.path.join(BAIKE, 'tan-jingyan.md'),
     '对[[谋官论处]]类案件，他不看饭局与请托记录',
     '对干预任免类案件，他不看饭局与请托记录', 1),
    (os.path.join(BAIKE, 'tan-jingyan.md'),
     '即认定为「以圈谋官」，不必再证主观故意',
     '即认定为干预任免，不必再证主观故意', 1),
    (os.path.join(BAIKE, 'xuanju-weiyuan.md'),
     '按[[谋官论处]]论处',
     '予以免职', 1),
    (os.path.join(BAIKE, 'xunshi-weiyuanhui.md'),
     '在[[谋官论处]]的关系图谱审查中合流',
     '在关系图谱审查中合流', 1),
    (os.path.join(BAIKE, 'xunshi-weiyuanhui.md'),
     '| 关联制度 | 谋官论处（关系图谱审查）；财产与利益申报 |',
     '| 关联制度 | 干预任免的处分（关系图谱审查）；财产与利益申报 |', 1),
    (os.path.join(BAIKE, 'zhan-shensi.md'),
     '另转一份给[[谋官论处]]承办机构',
     '另转一份给干预任免案的承办机构', 1),
    (os.path.join(BAIKE, 'zhan-shensi.md'),
     '以组织形态干预任免、分配官位者，按谋官论处，定级权在彼不在此',
     '以组织形态干预任免、分配官位者予以免职，定级权在彼不在此', 1),
    # ── 研究底本（政审一项）──
    (os.path.join('研究', '方案·干部培育与晋升新制（草案）.md'),
     '无政治犯罪、无「谋官」记录、无非法团体关系',
     '无政治犯罪、无干预任免的处分记录、无非法团体关系', 1),
]


def main():
    apply = '--apply' in sys.argv
    problems = []

    for rel, old, new, expect in EDITS:
        path = os.path.join(ROOT, rel)
        with open(path, encoding='utf-8') as f:
            text = f.read()
        got = text.count(old)
        if got != expect:
            problems.append(f'{rel}: 期望 {expect} 处，实际 {got} 处 —— {old[:30]}…')
            continue
        if apply:
            with open(path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(text.replace(old, new))

    # related 行：摘掉「谋官论处」这个词条名，并整理逗号
    src = os.path.join(ROOT, BAIKE)
    related_fixed = []
    for name in sorted(os.listdir(src)):
        if not name.endswith('.md'):
            continue
        path = os.path.join(src, name)
        with open(path, encoding='utf-8') as f:
            lines = f.read().split('\n')
        hit = False
        for i, line in enumerate(lines):
            if line.startswith('related:') and '谋官论处' in line:
                tokens = [t.strip() for t in line.split(':', 1)[1].split(',')]
                tokens = [t for t in tokens if t and t != '谋官论处']
                lines[i] = 'related: ' + ', '.join(tokens)
                hit = True
        if hit:
            related_fixed.append(name)
            if apply:
                with open(path, 'w', encoding='utf-8', newline='\n') as f:
                    f.write('\n'.join(lines))

    print(f'正文替换 {len(EDITS)} 条，related 清理 {len(related_fixed)} 个文件')
    for n in related_fixed:
        print('  related:', n)
    if problems:
        print('\n[中止] 命中数不符：')
        for p in problems:
            print('  ', p)
        return 1

    if apply:
        # 断言：源文与百科里不再出现「谋官」
        leftovers = []
        for base in (os.path.join(ROOT, SET), os.path.join(ROOT, BAIKE)):
            for name in os.listdir(base):
                if not name.endswith('.md'):
                    continue
                p = os.path.join(base, name)
                with open(p, encoding='utf-8') as f:
                    if '谋官' in f.read():
                        leftovers.append(os.path.join(os.path.basename(base), name))
        if leftovers:
            print('\n[警告] 仍有残留：', ', '.join(leftovers))
            return 2
        print('\n[完成] 设定源与百科源已无「谋官」字样')
    else:
        print('\n（干跑，未落盘；加 --apply 执行）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
