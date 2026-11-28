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
# ① 全部 16 站位 + 一张接触表（默认读 %LOCALAPPDATA%\Temp\grandhall\grandhall_precise.blend）
py -3 tools/audit/run_shots.py

# 只出几个站位（调试用）
py -3 tools/audit/run_shots.py --only 座椅落地,二层净空

# 连带落一份 manifest
py -3 tools/audit/run_shots.py --manifest "$TEMP/gm/manifest.json"

# ② 差分：改了这几处，13 张图里哪几张必须重出
py -3 tools/audit/manifest.py --old "$TEMP/gm/manifest_prev.json" --new "$TEMP/gm/manifest.json"
```

实测（2026-11-28，RTX 3060 Laptop，精模 63 物体 / 1,176,188 面）：

| 手段 | 耗时 |
| --- | --- |
| 16 站位 Workbench 1280×720 + manifest + 拼图 | **11–13 s**（单张 0.22–1.52 s） |
| 对照：13 张 Cycles 1920×1080 / 96 spp | 3 min 20 s |
| manifest 差分（纯 py，不开 Blender） | < 0.2 s |

## 三、文件

| 文件 | 说明 |
| --- | --- |
| `shots_table.py` | **站位不复制**：AST 读 `tools/grandhall/build_hall.py` 的 `SHOTS`，`AX` 取自 `hall_data.AXIS_Y`；只认常量/元组/字典/`dict()`/四则/`AX`，出现别的语法直接报错（不静默算错） |
| `shots.py` | Blender 侧：在已存 `.blend` 上出 Workbench 图；`--manifest` 落 `{name, group, bbox, tris}` |
| `sheet.py` | Pillow 拼 3 列接触表，标签自动跟 `SHOTS`（焦距/正交/hide 列表） |
| `run_shots.py` | 一条命令：复制 `.blend` → 调 Blender → 拼图。**Blender 脚本报错也返回 0**，这里靠 `RESULT` 行判定成功，并先清旧 PNG 防“拿旧图当新图” |
| `manifest.py` | 两份 manifest 差分；受影响机位 = 分组可见 ∩ **视锥命中**（座椅是整厅合并网格，只按分组会 16/16 全中，加视锥后 7/16） |

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
