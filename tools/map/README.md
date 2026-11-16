# 帝国政区图生成脚本

从《疆域与省界表（2026）》与真实地理数据生成两张图，可插入《中华帝国设定全书》PDF：

| 图 | 尺寸 | 脚本 |
| --- | --- | --- |
| 八州政区图（州级） | 4500×3000 | `prep_empire_map.py` → `render_empire_map.py` |
| 四十五省级政区图（省级） | 5400×3600 | `prep_empire_provinces.py` → `render_empire_provinces.py` |

## 文件

| 文件 | 作用 |
| --- | --- |
| `prep_empire_map.py` | 读 DataV 中国地级界 + Natural Earth 10m，按八州归并，投影到 Albers，输出 `%TEMP%\empire-map\prepared.pkl` |
| `render_empire_map.py` | 读 pickle，用 matplotlib 出图：八州色块、州府、首都星标、图例、比例尺、指北针、右侧信息栏 |
| `prep_empire_provinces.py` | 复用上一行模块的投影与东北裁切，把地级界／admin-1 按 45 省级归并，输出 `prepared_provinces.pkl`（含覆盖率断言） |
| `render_empire_provinces.py` | 45 省级填色、省界／州界、省名＋省会避让排布、信息栏（八州分组列 45 省） |
| `build_book_with_map.py` | pandoc→typst，在「第四卷 疆域与首都」卷首插入全图，输出新版 PDF |

## 环境

```powershell
$base = Join-Path $env:TEMP 'empire-map'
uv venv "$base\.venv" --python 3.12
uv pip install --python "$base\.venv\Scripts\python.exe" `
  --index-url https://pypi.tuna.tsinghua.edu.cn/simple `
  matplotlib shapely pyproj pyshp pymupdf
```

## 数据（缓存到 `%TEMP%\empire-map-data`）

- DataV：`https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json` 与各省 `{adcode}_full.json`
- Natural Earth 10m（naciscdn 直链）：
  - `https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_0_countries.zip`
  - `https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_1_states_provinces.zip`
  - `https://naciscdn.org/naturalearth/10m/physical/ne_10m_lakes.zip`
  - `https://naciscdn.org/naturalearth/10m/physical/ne_10m_rivers_lake_centerlines.zip`
  - `https://naciscdn.org/naturalearth/10m/physical/ne_10m_geography_regions_polys.zip`

## 运行

```powershell
$py = "$env:TEMP\empire-map\.venv\Scripts\python.exe"
& $py tools\map\prep_empire_map.py
& $py tools\map\render_empire_map.py

# 省级图（依赖 prep_empire_map 的投影/裁切，须在其后可导入）
& $py tools\map\prep_empire_provinces.py
& $py tools\map\render_empire_provinces.py
```

产物：`docs/assets/中华帝国全图(2026)·八州政区图.png`、`docs/assets/中华帝国全图(2026)·四十五省级政区图.png`。

省级图的调试开关：`$env:MAP_DEBUG="1"` 时打印每个省名的锚点与落点（经纬度、是否仍在本省内），用于定位标签跑偏。

插 PDF：

```powershell
py -3 tools\map\build_book_with_map.py
```

## 分省口径

省级图不是行政区划推算，而是**按《疆域与省界表》的犬牙交错规则逐块归并**，45 个单位一个不重不漏（`prep_empire_provinces.py` 会断言中国境内未归并面积，正常只剩南海礁盘）。要点：

- 中原省领豫西豫南＋鄂西北（十堰、襄阳、随州、荆门、神农架）；河南只余豫东豫北
- 江西领湘中湘北；岭南跨南岭并辖桂东南与港澳；贵州领湘西与鄂西南；安徽跨江领鄂东
- 广西三分（桂北桂中／桂西南／沿海＋海南）；辽南只领大连营口；北海拆冀鲁海岸；山东含徐州
- 陕北归陕西、鄂尔多斯归河套；康巴领川西高原与昌都；帕米尔与新疆分南疆并兼领吉尔吉斯、山地巴达赫尚、哈萨克南部三州
- 面积、人口一律以表为准；省界按地级界归并，仅示意（图注已写明）

## 备注

- 脚本里 `BASE` / `OUT` 是 `%TEMP%` 绝对路径，换机需改。
- typst 不接受 `C:/...` 绝对路径；`build_book_with_map.py` 会把图复制到 typ 同目录并用相对文件名。
- 详见 `E:\AI\tools.md` §12。
