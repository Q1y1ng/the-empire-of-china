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
py -3 tools/audit/asserts.py                    # 8 条窄断言，只读 hall_data + manifest
py -3 tools/audit/run_shots.py                  # 16 站位接触表
py -3 tools/audit/run_shots.py --only 座椅落地,二层净空
py -3 tools/audit/run_shots.py --manifest "$TEMP/gm/m.json"
py -3 tools/audit/manifest.py --old prev.json --new m.json   # 差分 + 受影响机位
```

实测（2026-11-28，RTX 3060 Laptop，精模 63 物体 / 1,176,188 面）：

| 手段 | 耗时 |
| --- | --- |
| 16 站位 Workbench 1280×720 + manifest + 拼图 | **11–13 s**（单张 0.22–1.52 s） |
| 断言 8 条（纯 py） | **0.2 s** |
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
| `asserts.py` | 8 条窄断言，只 import `hall_data` + 读 manifest；口径写死在代码里，见下节 |
| `check.py` | 编排：断言 → （可选）只出受影响机位。**日常只用这一条** |

## 三之二、断言清单（口径钉死，不靠人推）

| 断言 | 口径 | 门槛 |
| --- | --- | --- |
| `seat.floor_gap` | 座席组最低点 − 该层最前一排的 `tier_row_z` | ±0.02 m |
| `bal2.headroom` | 三层挑台最低点 − 二层楼板（**clamp 后**）最高点 | ≥ 2.30 m |
| `cross_aisle` | `TIERS[i]["aisles"]` 里宽度 ≥1.5 m 的处数 | 每层 ≥2 处 |
| `pit.rear_void` | `hall_radius(0)` − 池座末排 r | 只报数（规格待裁） |
| `seat.density` | 席数 ÷ `hall_plan()` 鞋带面积 | 参考 0.9–2.4 |
| `seat.forward` | 椅面法向 · 指向扇心 | **SKIP**：manifest 无朝向字段 |
| `origin_stack` | 物体中心离原点 <5 m | 应为 0 |
| `out_of_shell` | 越出中厅体块（±1 m 容差） | 应为 0 |

两条要说明白的：

- **`bal2.headroom` 用 clamp 口径**，所以是 3.566 m，不是构建端报的 2.46 m。
  2.46 是把二层楼板按 **未 clamp** 的公式外推到 r=86.5 算的；实际楼板过了末排就是平台（`tier_z(clamp=True)`）。
  两个数都 ≥2.30，门槛过，但口径必须只留一个——**真实几何是 3.566**。
- **`seat.forward` 明着 SKIP**。manifest 里没有朝向，从 bbox 猜“椅背朝哪”只能靠瞎猜；
  猜出来的 PASS 比不查更危险。要查就在构建端断言，或让 manifest 带上 `forward`。

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
