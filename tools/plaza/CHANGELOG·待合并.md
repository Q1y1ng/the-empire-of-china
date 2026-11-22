# 广场 · 待合并 CHANGELOG

> 合并时机：广场这轮改动全部推完，再统一并入根 `CHANGELOG.md` 的 `## [未发布]`。
> 合并前不要动根 CHANGELOG，避免与皇宫会话冲突。

### 新增

- 广场精模：砖缝与琉璃釉面烘成**可平铺 PNG 贴图**（`tools/plaza/tex/`，4 组 albedo + normal，共 2.7 MB）。此前精模的砖缝/瓦纹是程序化 Brick/Wave 节点，glTF 不支持，导出的 glb 里 `images=0 / textures=0`、38 个材质全是纯色 —— 材质细节在交付件里全丢；现在 glb 内嵌 8 张贴图，4 个材质带 baseColor + normal。
- 新增 `tools/plaza/tex_lib.py`：平铺砖纹/琉璃釉色与法线图案生成、材质改写、**世界坐标盒式投影 UV**（按面法线选轴，1 贴图单位 = 4.8 m，不用展 UV）。
- `build_massing.py` 新增 `--cpu`，可强制 CPU 渲染做对比。

### 变更

- 广场精模 glb：53.46 → 58.91 MB（贴图 2.7 MB + UV 约 3 MB）。
- 广场精模 11 张图按 OptiX 重渲染，单张 8~13 s，全轮 2 分 20 秒（此前 CPU 约 21.6 s/张）。
- `tools/plaza/README.md` 补「贴图与渲染设备」小节、更新实测数据与 glb 体积。

### 修复

- **Cycles 从没跑过 GPU**：`--factory-startup` 绕过用户首选项，`cycles.preferences.compute_device_type` 默认 `NONE`，只写 `scene.cycles.device = "GPU"` 会静默回落 CPU。现在显式按 OPTIX → CUDA → CPU 依次尝试并设 OptiX 降噪；同机 1920×1080 / 48 spp 实测 CPU 21.6 s → OptiX 9.1 s（2.4 倍）。
- 仓库里的精模 glb 与脚本不同步（旧导出少 23,916 三角面），已按当前脚本重导出。
