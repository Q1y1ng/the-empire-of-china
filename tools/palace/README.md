# 皇宫建模（宫城 / 宫城·0.72 km²）

把《长安城市志》卷三与《总设定》第十六编里的宫城数字，做成**可复现的 2D 总平面图与 3D 体量白模**。

- 数据唯一来源：[`palace_data.py`](palace_data.py)（每条尺寸标注【设定】或【推定】）
- 2D 出图：[`build_plan.py`](build_plan.py)（matplotlib → PNG + SVG）
- 3D 白模：[`build_massing.py`](build_massing.py)（Blender 5.x 无头 → .blend / .glb / 渲染图）

## 一、口径（先看这个）

| 档 | 内容 | 来源 |
| --- | --- | --- |
| 【设定】 | 宫城 **753 × 961 m**、0.72 km²、墙高 10 m、护城河宽 52 m、四门名、中轴里程、七个分区占地（8/6/7/7/16/4/24 ha）、殿宇名与用途、启门动线 | 《长安城市志》卷三；《总设定》第十六编；《法律要目·三》第五条 |
| 【推定】 | 四至（分区怎么切）、单体面阔进深与殿身高度、台基与月台尺寸、门楼形制、值房排布、石桥、现代附楼 | 本仓库按明官式比例反推（**架空混合：明式为骨，不作考据级复原**） |

全书检索「面阔／进深／庑殿／歇山／斗拱／琉璃瓦／须弥座」= **0 次**，所以任何细部都属新增口径，不属既定设定。若后续精模要做考据级，先补设定再改 `palace_data.py`。

面积自检（`python palace_data.py`）：

```
前朝正殿  8.40 ha / 8    +5.0%      东厢紫光阁  7.02 / 7   +0.3%
中、后殿  6.00 ha / 6    +0.0%      西厢政枢殿  7.02 / 7   +0.3%
后寝     15.84 ha / 16   -1.0%      琼苑        3.96 / 4   -1.0%
分区合计 48.24 ha / 48   （余量 24 ha 为门庭、巷道、值房）
宫城总   72.36 ha / 72
```

## 二、跑起来

### 2D 总平面

```bash
uv venv "$TEMP/palace-build" --python 3.12
uv pip install --python "$TEMP/palace-build/Scripts/python.exe" \
  --index-url https://pypi.tuna.tsinghua.edu.cn/simple matplotlib
"$TEMP/palace-build/Scripts/python.exe" build_plan.py            # 300 dpi → docs/assets
"$TEMP/palace-build/Scripts/python.exe" build_plan.py --dpi 150 --out "$TEMP/out"
```

> 本机 `python` 是 Anaconda **2.7.3 32 位**，直接 `python build_plan.py` 会报语法错；用 `py -3` 或上面的 venv。

### 3D 体量白模

```bash
"/e/SteamLibrary/steamapps/common/Blender/blender.exe" -b --factory-startup \
  -P build_massing.py -- --out "$TEMP/out" --samples 160 --res 1920
```

实测（RTX 3060 Laptop 6 GB / OptiX）：建 192 个物体、1,932 三角面约 2 s；1600×900 / 128 spp 每张 15~25 s；正射总平面 28 s；glTF 0.23 MB。

## 三、产物

| 文件 | 说明 |
| --- | --- |
| `docs/assets/皇宫宫城(2026)·总平面图.png` | 4200×4800 / 300 dpi 总平面，含图例、动线、面积表 |
| `docs/assets/皇宫宫城(2026)·总平面图.svg` | 矢量版（可缩放进 typst / 排版） |
| `docs/assets/皇宫宫城(2026)·体量白模·鸟瞰东南.png` | 1920×1080，全局体量关系 |
| `docs/assets/皇宫宫城(2026)·体量白模·中轴.png` | 沿中轴低空视角，看承天门→玄武门六进序列 |
| `docs/assets/皇宫宫城(2026)·体量白模·人视金瓯殿.png` | 人视高度，殿身、台基、月台比例 |
| `docs/assets/皇宫宫城(2026)·体量白模.glb` | glTF，后续网页漫游（three.js）直接用 |
| `%TEMP%/palace_massing/palace_massing.blend` | 可在 Blender GUI 里转着看；TEMP 会被清，要留就另存 |

## 四、构图与形制

- **中轴**：承天门（城台+门楼）→ 前庭 → 宣政门 → 金瓯殿月台 → 金瓯殿（120×60，台基 144×84）→ 秉衡殿 → 凝命殿 → 后寝（乾宁宫、泰宁宫、六宫）→ 琼苑 → 玄武门；御道贯通，承天桥 / 玄武桥跨护城河。
- **东西两厢**：紫光阁（90×90，中央政治局驻地）与政枢殿（110×70，国务院核心部门）各带两座配殿。
- **现代附楼**：紫光阁东侧一栋 56×80 平顶玻璃体（**架空混合·推定**），对应「紫光阁办公化」。
- **屋顶**：正殿庑殿顶（四坡起脊），配殿、六宫、值房悬山顶，角楼庑殿顶；台基一律白石，城墙压顶深色。

## 五、已知限制

1. 殿身**只有体块**：没有开间、斗拱、彩画、门窗、廊庑；门洞未开（城门为实体城台）。
2. 高度为明官式比例推估值（金瓯殿 15 m 殿身 + 7.9 m 屋顶 ≈ 23 m，与太和殿 26.9 m 同量级），不是设定值。
3. 值房为示意排布，不占分区面积账（分区表里的 24 ha 是余量）。
4. 琼苑只做绿地，无树木、水体、假山。
5. `palace_data.py` 改数字后，2D 与 3D 同时变；改结构（新增殿宇）两边都会自动跟着画。

## 六、踩过的坑

- **相机 `clip_end` 默认 100 m**：753×961 m 的米制场景会被整片裁掉，首版渲染全空。固定为 `40000`。
- **Blender 5.3 的 EEVEE 标识符是 `BLENDER_EEVEE`**，4.x 的 `BLENDER_EEVEE_NEXT` 已不存在；写错直接抛 `enum not found`。
- **中文字渲染**：`bpy.data.fonts.load(r"C:\Windows\Fonts\msyh.ttc")` 可用；默认 Bfont 没有 CJK 字形。
- **AgX 会把宫墙红洗成粉色**：白模改用 `view_transform='Standard'` + 曝光 −0.25，颜色才与材质一致。
- **同一套顶点坐标不要用「旋转物体」改屋顶朝向**：屋顶顶点是世界坐标，旋转会绕原点飞走；改为按长边直接生成脊线。
- 材质 `Principled BSDF` 的 `Base Color` 是线性值，直接填 sRGB 直觉值会偏亮。
