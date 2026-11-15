# 八州政区图生成脚本

从《疆域与省界表（2026）》与真实地理数据生成 4500×3000 的八州政区图，并可插入《中华帝国设定全书》PDF。

## 文件

| 文件 | 作用 |
| --- | --- |
| `prep_empire_map.py` | 读 DataV 中国地级界 + Natural Earth 10m，按八州归并，投影到 Albers，输出 `%TEMP%\empire-map\prepared.pkl` |
| `render_empire_map.py` | 读 pickle，用 matplotlib 出图：八州色块、州府、首都星标、图例、比例尺、指北针、右侧信息栏 |
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
& "$env:TEMP\empire-map\.venv\Scripts\python.exe" tools\map\prep_empire_map.py
& "$env:TEMP\empire-map\.venv\Scripts\python.exe" tools\map\render_empire_map.py
```

产物：`docs/assets/中华帝国全图(2026)·八州政区图.png`。

插 PDF：

```powershell
py -3 tools\map\build_book_with_map.py
```

## 备注

- 脚本里 `BASE` / `OUT` 是 `%TEMP%` 绝对路径，换机需改。
- typst 不接受 `C:/...` 绝对路径；`build_book_with_map.py` 会把图复制到 typ 同目录并用相对文件名。
- 详见 `E:\AI\tools.md` §12。
