# 中国古代皇宫 3D 项目 · 外部资产来源与许可（CREDITS）

生成日期：2026-11-22　目标管线：Blender 5.3.0 无头（Cycles，Windows）
本目录中的资产全部为 **CC0 1.0**，可商用、可修改、**无需署名**；此文件是自愿留存的溯源记录。

## 一、交付清单

### 1.1 HDR 环境光（2K，Radiance `.hdr`）

| 文件名 | 原始名称 | 来源 URL | 作者 | 许可证 | 需署名 | 大小 | 用途 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `hdri_sky_sunny_2k.hdr` | Kloofendal 43d Clear (Pure Sky) | <https://polyhaven.com/a/kloofendal_43d_clear_puresky> | Greg Zaal | CC0 1.0 | 否 | 4.4 MB | 晴天侧光：有真实太阳盘，硬阴影 + 强烈方向感，做宫殿外景主光 |
| `hdri_sky_overcast_2k.hdr` | Kloofendal Overcast (Pure Sky) | <https://polyhaven.com/a/kloofendal_overcast_puresky> | Greg Zaal | CC0 1.0 | 否 | 4.1 MB | 阴天柔光：无硬阴影、低对比，做建筑细部/评审灯光 |

两张均为纯天空（Pure Sky），无地面景物，用作 World 光照不会把草地/建筑"反射"进画面；需天空背景时可直接用同一张图。
- 走向参考：晴天图 `max=114176`（太阳盘），`mean=0.75`；阴天图 `max=6.69`，`mean=0.89`——阴天整体更亮但无高光峰值，这正是柔光的数值特征。

### 1.2 PBR 贴图（2048×2048，全部无缝平铺）

| 文件名 | 原始名称 | 来源 URL | 作者 | 许可证 | 需署名 | 大小 | 用途 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `tex_whitemarble_2k_diff.jpg`<br>`tex_whitemarble_2k_nor_gl.jpg`<br>`tex_whitemarble_2k_rough.jpg` | Marble 021 | <https://ambientcg.com/a/Marble021> | Lennart Demes (ambientCG) | CC0 1.0 | 否 | 3.5 / 1.3 / 1.2 MB | 汉白玉：台基、栏板、望柱、御路石。近纯白微灰纹，最贴近汉白玉 |
| `tex_greybrick_2k_diff.jpg`<br>`tex_greybrick_2k_nor_gl.png`<br>`tex_greybrick_2k_rough.jpg` | Brick Wall 08 | <https://polyhaven.com/a/brick_wall_08> | Amal Kumar | CC0 1.0 | 否 | 2.8 / 21.4 / 1.9 MB | 青砖：宫墙、值房、墁地。冷灰蓝调，青砖的"灰中带蓝"正确 |
| `tex_wood_2k_diff.jpg`<br>`tex_wood_2k_nor_gl.png`<br>`tex_wood_2k_rough.jpg` | Wood Table 001 | <https://polyhaven.com/a/wood_table_001> | Rico Cilliers（处理）/ Dimitrios Savva（摄影） | CC0 1.0 | 否 | 0.9 / 19.7 / 0.9 MB | 木纹：柱、梁枋、隔扇、匾额。红棕抛光木纹，作朱红漆柱的底色层 |
| `tex_glazedtile_2k_diff.jpg`<br>`tex_glazedtile_2k_nor_gl.png`<br>`tex_glazedtile_2k_rough.jpg` | Grey Roof 01 | <https://polyhaven.com/a/grey_roof_01> | Rob Tuytel | CC0 1.0 | 否 | 1.3 / 19.4 / 1.3 MB | 琉璃瓦面：已带透明釉层的高光与起伏，着色器里染成黄/绿即得琉璃效果 |

合计 14 个文件、约 **85 MB**（其中 3 张 PNG 法线图占 63 MB，见 §三.4）。
命名规则：`hdri_sky_<天气>_2k` / `tex_<材质>_2k_<diff|nor_gl|rough>`，全 ASCII，规避中文路径问题。

### 1.3 许可依据（原文）

- Poly Haven：<https://polyhaven.com/license> — "Our assets are all licensed as CC0 … You do not need to give credit or attribution."
- ambientCG：<https://docs.ambientcg.com/license/> — "All ambientCG assets are provided under the Creative Commons CC0 1.0 Universal License … You don't need to give credit."

### 1.4 复现命令

```bash
curl -L --retry 3 --max-time 300 -o hdri_sky_sunny_2k.hdr \
  https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/2k/kloofendal_43d_clear_puresky_2k.hdr
curl -L --retry 3 --max-time 300 -o hdri_sky_overcast_2k.hdr \
  https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/2k/kloofendal_overcast_puresky_2k.hdr
# 贴图：先取 https://api.polyhaven.com/files/<asset_id>，再取 JSON 里 <副层>.2k.jpg|png 的 url
# ambientCG：https://ambientcg.com/api/v2/full_json?type=Material&id=Marble021&include=downloadData
#            → 下 2K-JPG.zip 后解出 Color / NormalGL / Roughness
```

## 二、评估过但**不用**的组件库及原因

| 名称 | 链接 | 许可证 | 最近更新 | 能不能用 | 为什么 |
| --- | --- | --- | --- | --- | --- |
| ACA 筑韵古建插件 v0.5.2 | [DTool 文章](https://www.dtool.design/archives/5651) / [文档](https://docs.qq.com/doc/DYXpwbUp1UWR0RXpu) | **不明** | 2026-01-05 | ❌ | 标题自称"国产开源"，但页面按钮是**登录后下载**，未登录拿不到包；文档为腾讯文档只读。GitHub/Gitee 检索 `ACA 筑韵`、`筑韵 古建`、`zhuyun` 均无对应仓库 → 许可无法确认，不能进商用管线 |
| Zenodo 7837875 中世纪中式木构生成脚本 | <https://zenodo.org/records/7837875> | 未授予（Restricted） | 2023-04-17（元数据 2025-04-24） | ❌ | 记录本身公开，但**文件状态是 Restricted**："Access is restricted until all authors and contributors consented"，下载数 0，需登录并申请权限 → 拿不到。思路（Blender 侧栏参数化生成宋元木构，适配 Blender 3.0）可借鉴 |
| miniLibs 中国古建参数化构件库 | <https://github.com/in-a-mist/miniLibs> | MIT | 2023-09-06 | ❌ | 许可最干净，但整套是 **Rhino/Grasshopper** 平台（`.3dm` + ghpython），本机无 Rhino，Blender 也读不了 `.3dm` → 资产不可直接用，仅可参考其《营造法式》构件拆分 |
| chbim-prototype | <https://github.com/Chartreuse310/chbim-prototype> | MIT | 2026-09-23（**已归档** 2026-10-16） | ❌ | 几何核心是 **OpenSCAD**，产物要再转 STL/glTF 才能进 Blender；且仓库自述为 MVP 原型、0 star、已归档 → 工程化风险高 |
| KerneLab/DouGong | <https://github.com/KerneLab/DouGong> | **无 LICENSE**（GitHub API `license=null`） | 2026-06-23 | ❌ | 27 MB 里有斗拱相关内容，但**没有任何许可证**：默认保留所有权利，商用/改模型均有法律风险 → 一票否决 |
| 33_DougongMechanics | <https://github.com/1195214305/33_DougongMechanics> | **无 LICENSE** | 2026-01-20 | ❌ | 仅 21 KB，属课程/论文代码片段，无模型资产；同样无许可证 |
| 筑韵千年 zhuyun-heritage | <https://github.com/3502687683-web/zhuyun-heritage> | MIT | 2026-05-31 | ❌ | 是 ECharts + Three.js 的**数据可视化大屏**参赛作品，不是模型库；Three.js 场景里的构件非独立可复用资产 |
| Sketchfab 太和殿（David_Pang） | <https://sketchfab.com/3d-models/f39212f1ba0145bf882e742b28d4eaef> | CC BY 4.0 | 2020-11-12 | ⚠️ 备选 | 95.9 万三角面，质量可用；但 **Sketchfab 下载必须登录账号**，本机无账号无法无人值守拉取，且 CC BY 要求逐模型署名、二次分发需保留声明 → 本轮不纳入，留作人工确认后的备选。同类还有 Larc7、TRNKL 等的同名模型，许可与几何各异，需逐个核 |
| Open Heritage 3D · 鹿港龙山寺（台湾） | <https://openheritage3d.org/project.php?id=tnav-3t41> | **CC BY-NC-SA 4.0** | 2019-04-18（采集 2016-04） | ❌ | 与中式宫庙最贴的一个（有藻井、斗拱、龙柱石雕），但：①**NC 禁商用**且 SA 传染；②14.73 GB LiDAR + 5.78 GB 航测，产物是 LAS 点云/照片而非网格精模；③下载要填表 + 验证码，**邮件发链接**。三条任一条都足以否掉 |
| Open Heritage 3D · 顺化皇城（越南） | <https://openheritage3d.org/project.php?id=4z5b-vz23> | **CC BY-NC-SA 4.0** | 2019-04-18 | ❌ | 阮朝中式皇城，形制极接近；同样 NC + 点云（20.69 GB LiDAR + 83 GB 摄影测量）+ 邮件申请 → 不可用 |
| CTA ConstructionTools（营造法式） | <https://archcookie.com/3249.html> | 商业授权 | 2021-08-30 | ❌ | 是 **SketchUp** 插件、商业收费；平台与格式都不符，Blender 无法直接调用 |
| 境外其他 | — | — | — | — | 关于 Open Heritage 3D 的"中国数据"结论：逐条核对数据表 107 条记录，**中国大陆 0 条**；东亚仅有日本、台湾（鹿港龙山寺）。台湾条目归在 Country=Taiwan |

## 三、本机 Blender 读取注意事项（实测，非推测）

1. **中文路径可用**：资产放在 `E:/AI/帝国/tools/palace/assets/`，Blender 5.3.0 无头成功地用 `bpy.data.images.load()` 读了全部 14 个文件，文件名与路径均未出错。但**文件名仍全部用 ASCII**，以免 `//` 相对路径、打包、跨机迁移时踩坑。
2. **色彩空间是最大的坑**：12 张贴图加载后 `colorspace_settings.name` **全部默认 `sRGB`**，包括法线图和粗糙度图。必须手动把 `nor_gl` / `rough` 改成 **Non-Color**，否则法线会被 sRGB 曲线扭曲、粗糙度整体偏亮（高光散、金属感丢失）。这是一个静默错误——不报错，只是"看起来不对"。
3. **法线图方向**：已选 `nor_gl`（OpenGL 约定，+Y 向上），直接插 Normal Map 节点即可；**不要**用 `nor_dx`（DirectX 约定，绿通道相反，凹凸会反过来）。
4. **仓库体积**：85 MB 里 63 MB 是 3 张 2048² PNG 法线（灰砖 21.4 MB、木纹 19.7 MB、琉璃瓦 19.4 MB）。若要压体积，可把法线转成质量 95 的 JPG（约 2–4 MB/张，视觉损失极小），但近景石雕/瓦当的细微起伏会略钝；粗糙度与漫反射已用 JPG，无需再动。
5. **平铺质量（量化实测）**：以"左右/上下接缝差 ÷ 相邻像素差"为指标（≈1.0 即无缝）——
   - 汉白玉 0.92–1.09、青砖 0.91–1.21、琉璃瓦法线 0.87–1.24：接缝与普通像素梯度同级，**任意平铺无痕**。
   - **木纹上下接缝 2.70**（漫反射）最差，琉璃瓦上下 2.25（漫反射）/1.94（粗糙度）次之：绝对值仍小（木纹 0.022、琉璃瓦 0.018），但成大面竖向重复时能看出"带状"。建议木纹 UV 沿构件长向拉伸（柱子本来就该顺纹），琉璃瓦按屋面坡向阵列而非随机平铺。
6. **贴图比例**：Poly Haven 给出物理尺寸——`grey_roof_01` 8 m、`brick_wall_08` 1.9 m、`wood_table_001` 1.5 m，可按构件实际尺寸设 Mapping 缩放（如青砖墙 4 m 高 → 重复 ≈2.1 次）。**ambientCG 的 API 不返回物理尺寸**（`dimensionX/Y` 均为 0），汉白玉需目测校准：按台基通高与栏板高度反推，建议 1 UV ≈ 1.2–1.5 m 起调。
7. **风格缺口**：本目录只解决了"材质与环境光"，**没有任何一件中式构件几何**（斗拱、举折屋面、须弥座、栏板）。上面的组件库全部因许可/平台/格式问题落空，几何需项目内自建，或由 lead 决定是否接受 Sketchfab 的 CC BY 模型（需人工登录 + 署名）。

### 附：验证脚本

`verify_hdri.py`（同时存在本目录与 `$TEMP/palace_polish/assets/`；Blender 无头，480×270 球体+地面，Cycles 64 spp CPU）

```bash
timeout 300 "E:/SteamLibrary/steamapps/common/Blender/blender.exe" -b --factory-startup \
  -P tools/palace/assets/verify_hdri.py -- \
  "E:/AI/帝国/tools/palace/assets" "$TEMP/palace_polish/assets"
```

实测：`RESULT: PASS`；晴天图渲染 `mean_sRGB=161.25`、阴天图 `mean_sRGB=151.02`（0–255），`clipped=0.000`，晴天图可见硬阴影与镜面高光、阴天图完全无硬影。
产物 `verify.png` / `verify_overcast.png`（480×270）同时留在 `$TEMP/palace_polish/assets/` 与本目录，便于复核。

## 关于法线贴图

`tex_*_nor_gl.jpg` 是由同目录的 `_nor_gl.png` 原件（各约 20 MB）以 quality 92 / 无子采样转出的，
体积从 63 MB 降到约 5 MB。PNG 原件仍留在本机，但按 `.gitignore` **不入库**——
需要更高精度时按本表 URL 重新下载即可。法线/粗糙度贴图挂进 Blender 时必须把色彩空间改成
**Non-Color**（默认 sRGB 会静默出错、不报错）。本目录资产当前尚未接进 `lg_look.py`
（材质全是程序化），留作下一轮 triplanar 贴图用。
