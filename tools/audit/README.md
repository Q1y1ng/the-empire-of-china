# tools/audit/ —— 自查工具（不建模，只负责“看得见改动”）

给 `tools/grandhall/`、`tools/plaza/` 的作者会话当**外部自查层**用：
不动它们的代码，只读它们产出的 `.blend` 与 manifest。

来由（2026-11-28）：作者每天走进 Unity 看 5 次，一次闭环 10 分钟
（40 s 建模 + 3 min20 Cycles 13 张 + 6 min Unity 打包 235 MB + autoshot）。
缺陷却多是**关系型**的（净空 1.99 m、座椅悬空 0.40 m、横向过道缺失、椅背朝向），
Cycles 图看不出来，体检脚本（面级共面/缝）也查不出。

本目录只解决两件事：**看快**（秒级接触表）与**只看改动的**（manifest 差分）。

## 一、口径先说清：它判什么、不判什么

| 判 | 不判 |
| --- | --- |
| 净空、悬空、穿插、过道在不在、椅背朝向、体量关系 | **好不好看**（Workbench 无 PBR / URP / ACES） |
| 改动是否影响某张图 | 材质配色是否达标（要判请用 `--color material` + Cycles） |
| 物体是否跑到原点、bbox 是否异常 | 面级精度（2 cm 缝要 Cycles 或专门体检脚本） |

Workbench 用**分组色**（不是材质色）：同组一色，目的是分得清墙/板/座椅/穹顶。
分辨率默认 1280×720——640×360 看不出 2 cm 缝与 40 cm 悬空。

## 二、跑起来

```bash
# 一条命令：断言 + 接触表（~13 s）
py -3 tools/audit/check.py

# 只算数，不出图（0.2 s，改一次就跑一次）
py -3 tools/audit/check.py --no-shots

# 只出“相对上一份 manifest 有变化”的机位（改一处 → 6 s）
py -3 tools/audit/check.py --diff "$TEMP/gm/prev.json"
```

分开调用也可以：

```bash
py -3 tools/audit/asserts.py                    # 10 条窄断言，只读 hall_data + manifest
py -3 tools/audit/selftest.py                   # 断言自检：篡改 manifest，确认断言真会红
py -3 tools/audit/run_shots.py                  # 16 站位接触表
py -3 tools/audit/run_shots.py --only 座椅落地,二层净空
py -3 tools/audit/run_shots.py --manifest "$TEMP/gm/m.json"
py -3 tools/audit/manifest.py --old prev.json --new m.json   # 差分 + 受影响机位
```

实测（2026-11-28，RTX 3060 Laptop，精模 63 物体 / 1,176,188 面）：

| 手段 | 耗时 |
| --- | --- |
| 16 站位 Workbench 1280×720 + manifest + 拼图 | **11–13 s**（单张 0.22–1.52 s） |
| 断言 10 条（纯 py） | **0.2 s** |
| 断言自检 7 例（`selftest.py`，6 次子进程） | **4 s** |
| 断言 + 只出受影响 7 站位（`--diff`） | **6.6 s** |
| 对照：13 张 Cycles 1920×1080 / 96 spp | 3 min 20 s |
| 对照：Unity 换 glb + 打包 235 MB + autoshot | 6 min |

## 三、文件

| 文件 | 说明 |
| --- | --- |
| `shots_table.py` | **站位不复制**：AST 读 `tools/grandhall/build_hall.py` 的 `SHOTS`，`AX` 取自 `hall_data.AXIS_Y`；只认常量/元组/字典/`dict()`/四则/`AX`，出现别的语法直接报错（不静默算错） |
| `shots.py` | Blender 侧：在已存 `.blend` 上出 Workbench 图；`--manifest` 落 `{name, group, bbox, tris}` |
| `sheet.py` | Pillow 拼 3 列接触表，标签自动跟 `SHOTS`（焦距/正交/hide 列表） |
| `run_shots.py` | 一条命令：复制 `.blend` → 调 Blender → 拼图。**Blender 脚本报错也返回 0**，这里靠 `RESULT` 行判定成功，并先清旧 PNG 防“拿旧图当新图” |
| `manifest.py` | 两份 manifest 差分；受影响机位 = 分组可见 ∩ **视锥命中**（座椅是整厅合并网格，只按分组会 16/16 全中，加视锥后 7/16） |
| `manifest_io.py` | manifest 读写与 schema 归一：`build_hall.py` 与 `shots.py` 两个生产者必须是同一种格式，否则 diff 对不上 |
| `asserts.py` | 10 条窄断言，只 import `hall_data` + 读 manifest；口径写死在代码里，见下节 |
| `selftest.py` | **断言自检**：把缺陷注入 manifest 副本，要求目标断言 FAIL、原样 PASS。跑不通说明判据写虚了 |
| `check.py` | 编排：断言 → （可选）只出受影响机位。**日常只用这一条** |

## 三之二、断言清单（口径钉死，不靠人推）

| 断言 | 口径 | 门槛 |
| --- | --- | --- |
| `seat.floor_gap` | 座席组最低点 − 该层最前一排的 `tier_row_z` | ±0.02 m |
| `bal2.headroom` | 三层挑台最低点 − **同半径处**二层楼板（clamp 后） | ≥ 2.30 m |
| `tier.overhang` | 二层各排视线被三层挑台切掉的顶棚高度 | 只报数（切的是装饰带还是人） |
| `cross_aisle` | `TIERS[i]["aisles"]` 里宽度 ≥1.5 m 的处数 | 每层 ≥2 处 |
| `pit.rear_void` | `hall_radius(0)` − 池座末排 r | 0.5–2.0 m（作者：末排贴墙） |
| `seat.density` | 席数 ÷ `hall_plan()` 鞋带面积 | 1.6–2.6（实物 2.13） |
| `seat.forward` | 「座心 − 靠背心」→ 朝向；观众席对扇心、主席团对观众厅 | 对齐 ≥ 0.99 |
| `seat.module` | 座椅族 5 条模数不变式（尺寸只在 `SEAT_DETAIL` 一处） | 全部成立 |
| `origin_stack` | 物体中心离原点 <5 m | 应为 0 |
| `out_of_shell` | 越出中厅体块（±1 m 容差） | 应为 0 |

两条要说明白的：

- **`bal2.headroom` 用 clamp 口径**，所以是 3.566 m，不是构建端报的 2.46 m。
  2.46 是把二层楼板按 **未 clamp** 的公式外推到 r=86.5 算的；实际楼板过了末排就是平台（`tier_z(clamp=True)`）。
  两个数都 ≥2.30，门槛过，但口径必须只留一个——**真实几何是 3.566**。
- **`seat.forward` 从 SKIP 转正**（2026-11-29）。以前 manifest 里没有朝向，从 bbox 猜“椅背朝哪”只能靠瞎猜，
  所以宁可明着 SKIP。现在构建端在**落进网格的顶点**上取「座心 − 靠背心」→ 单位朝向，
  记对齐度的全量 min/max/mean，并按步长抽样（含首末座）存原始 `(座心, 朝向)`；
  这里不采信它报的数，逐样本自己重算，且基准方向各自从 `hall_data` 现推。
  能抓住的真缺陷（作者 2026-11-28 抓到的“九把主席团椅背对观众”就是这一类）：
  模板翻半圈、靠背与座垫两串盒子写反、零向量、两端口径不同源。
  `selftest.py` 把这 6 种注入跑一遍，全部必须 FAIL，原样必须 PASS。

## 四、接线约定（与作品会话商定 2026-11-28）

- 只读：`docs/assets/*万人大礼堂*`、`%LOCALAPPDATA%\Temp\grandhall\*.blend`、manifest.json
- **不改** `tools/grandhall/`、`tools/plaza/`、`tools/palace/`
- `.blend` 每次构建覆盖 → `run_shots.py` 先复制到 `$TEMP/grandhall_shots/_blend/` 再开
- 对方若加 `build_hall.py --manifest`，schema 与本目录一致：
  `{blender, blend, generated, objects:[{name, group, bbox:{min,max}, tris}], totals}`

## 五、已知局限

- **视锥是粗判**（bbox 八角点，忽略近远裁剪与遮挡）：只用来“少重出几张”，不当可见性真相。
- **分组太粗**：`seat0/1/2` 各是一个 40 万面的合并网格，任何座椅改动都会命中整片。
  真要更细，得让构建端按排/区拆 group——那是作品会话的决定，不是本目录能替的。
- **Workbench 不显示烘好的贴图**：`--color material` 只对纯色节点材质有效（当前仅 3 个）。
- 站位表依赖 `build_hall.py` 里 `SHOTS` 是**顶层字面量**；改成函数构造或条件拼装会直接报错，
  这是有意的（宁可炸，不要悄悄用错站位）。

## 六、验收账本（`acceptance.py` + `acceptance.json`）

作者每次走进模型说的话，逐条落账：**原话 → 类型 → 绑定哪条断言**。

```bash
py -3 tools/audit/acceptance.py            # 全部条目，按状态分组
py -3 tools/audit/acceptance.py --open     # 还没守住的
py -3 tools/audit/acceptance.py --add "座椅还是没贴地" --kind 几何 --assert seat.floor_gap
py -3 tools/audit/acceptance.py --close A-001 --status fixed
```

状态四档：`open`（未解决）/ `asserted`（已有断言守住）/ `fixed`（修好且断言通过）/ `spec`（等作者裁决）。

为什么它是复利：作者提过 N 条，构建时机器挡 N 条，作者下次只看新的。`check.py` 每次会打印未守住的条数。

## 七、几何自检（`geom.py`）

```bash
py -3 tools/audit/check.py --geom          # 断言 + 几何，共约 4-5 s
```

查四类：真实三角面互穿、悬空、法线内翻、包围盒重合。

**踩过的坑（写在代码注释里了）**：`BVHTree.overlap()` 报的是**包围盒相交的面**，不是真相交。
第一版拿它当互穿，`座席0 × 桌板0` 报了 39,958 对——其实是椅背嵌在座箱里的正常榫接。
现在对候选面再跑一遍**线段-三角形求交**，`real` 才是真相交。

结果 113 对是**真相交**，但多数是构造性的（椅背穿桌板、满天星灯嵌进穹顶、座席埋进挑台前缘）。
所以带白名单：判过的写进 `geom_allow.json`，之后只报新增未登记的。
首次要人判一遍（约 10 分钟），这是唯一没法自动化的部分——**工具不该替作者决定"这算不算错"**。

## 八、浏览器看图（`view.py`）

```bash
py -3 tools/audit/view.py                 # 自动找最新精模 glb，起本地服务
py -3 tools/audit/view.py --shot 二层坐姿  # 换站位（站位名取自 SHOTS）
py -3 tools/audit/view.py --outside       # 自动框全景
```

默认机位是**池座坐姿**——就是作者验收时的视角。`F` 飞行（WASD + 鼠标）、`O` 轨道。
材质是原始 glTF（无 URP / ACES），**只判关系，不判观感**；但比「换 glb → 建场景 → 打包 235 MB → autoshot」快两个数量级。

验证方式：CDP 驱动 Edge 截图，HUD 读到 `63 物体 / 1,176,188 三角面`，池座视角能看到主席台与台口。

## 九、厅/席变体（`variants.py`）

```bash
py -3 tools/audit/variants.py
```

三档方案一次出数（不改几何，只改 `hall_data` 的临时副本调它自己的 `tier_rows`）：

| 方案 | 进深 | 后墙宽 | 面积 | 席数 | 密度 | 最远视距 | 后区空场 | 达 1 万席 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 现状 | 95 | 160 | 9,500 | 10,340 | 1.09 | 66.4 | 40.0 | ✓ |
| 缩厅 | 70 | 120 | 5,600 | 9,461 | 1.69 | 61.9 | 15.0 | ✗ |
| 铺满 | 95 | 160 | 9,500 | 14,227 | 1.50 | 73.9 | 18.1 | ✓ |

给作者用数选，不是改代码的依据。净空**故意不在这张表里**——它要靠网格底面（`asserts.py` 的 3.566 m），
在这里用 z0 相减会得出 5.47（层间高差），两个数并排就是新的口径病。

## 十、跨模型契约（`../contract.py`）

```bash
py -3 tools/contract.py        # 9 条自检：内部一致 + hall_data 一致
py -3 tools/contract.py --json
```

收中厅体块、壁厚/空腔、内胆实际范围、门斗、台基下沉。**含一条已裁决例外**：
内胆东面 −311.5 比理想空腔线 −312.5 外移 1.0 m（门斗出挑进壁厚）——这是裁决，不算漂移，
所以断言写成"等于门斗面"而不是"等于空腔线"。

口径提醒：契约按 **2026-11-25 下沉方案**写（体块不抬高、内胆下沉 2.3、穹顶 50.0 ≤ 琉璃顶底 50.15）。
早先算的"抬到台基面 52.3、顶穿檐口"是**已否决**的，别再写回来。
