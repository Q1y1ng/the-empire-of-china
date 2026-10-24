#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""帝国百科（静态站）生成器。

用法：
    py -3 tools/build_baike.py            # 生成 docs/baike/*.html
    py -3 tools/build_baike.py --check    # 只校验交叉链接，不写文件

源文件：docs/baike/src/<slug>.md
    文件头前置信息（--- 包起来）：
        slug: li-xiannian
        title: 李先念
        subtitle: 中华帝国国务院总理
        category: 人物          # 机构 / 人物 / 概念
        summary: 一句话摘要（检索用）
        updated: 2026-10-25
        infobox:
          中文名: 李先念
          ...
    正文：Markdown 子集（## / ### / 段落 / - 列表 / 1. 列表 / > 引文 / 表格 / **粗体**）
          交叉链接写作 [[词条名]] 或 [[词条名|显示文字]]，词条名必须存在，否则报错。

输出：docs/baike/index.html（首页）＋ <slug>.html（词条页）；样式内联，无外部依赖。
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAIKE = os.path.join(ROOT, "docs", "baike")
SRC = os.path.join(BAIKE, "src")
CATEGORIES = ["机构", "人物", "概念"]


# --------------------------------------------------------------------------
# 前置信息
# --------------------------------------------------------------------------
def parse_front(text: str, name: str):
    if not text.startswith("---"):
        raise SystemExit(f"{name}: 缺少前置信息块（--- 开头）")
    end = text.find("\n---", 3)
    if end < 0:
        raise SystemExit(f"{name}: 前置信息块未闭合")
    front, body = text[3:end], text[end + 4 :].lstrip("\n")
    meta = {"infobox": []}
    in_box = False
    for raw in front.split("\n"):
        if not raw.strip():
            continue
        if raw.strip() == "infobox:":
            in_box = True
            continue
        if in_box and raw.startswith("  "):
            k, _, v = raw.strip().partition(":")
            meta["infobox"].append((k.strip(), v.strip()))
            continue
        in_box = False
        k, _, v = raw.partition(":")
        meta[k.strip()] = v.strip()
    for need in ("slug", "title", "category"):
        if not meta.get(need):
            raise SystemExit(f"{name}: 前置信息缺少 {need}")
    if meta["category"] not in CATEGORIES:
        raise SystemExit(f"{name}: category 必须是 {CATEGORIES}")
    return meta, body


# --------------------------------------------------------------------------
# 极简 Markdown
# --------------------------------------------------------------------------
def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(s: str, links: dict[str, str], here: str) -> tuple[str, list[str]]:
    """行内处理：粗体、交叉链接。返回 (html, 引用到的 slug 列表)。"""
    used: list[str] = []
    out = esc(s)

    def link_sub(m: re.Match) -> str:
        target = m.group(1).strip()
        label = (m.group(2) or target).strip()
        slug = links.get(target)
        if not slug:
            raise SystemExit(f"交叉链接指向不存在的词条：[[{target}]]")
        used.append(slug)
        cls = ' class="mw self"' if slug == here else ' class="mw"'
        return f'<a{cls} href="{slug}.html">{label}</a>'

    out = re.sub(r"\[\[([^\[\]|]+)(?:\|([^\[\]]+))?\]\]", link_sub, out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", out)
    return out, used


def md_to_html(body: str, links: dict[str, str], here: str):
    lines = body.split("\n")
    html: list[str] = []
    toc: list[tuple[int, str, str]] = []
    used: list[str] = []
    h2 = h3 = 0
    i = 0
    while i < len(lines):
        raw = lines[i]
        s = raw.strip()
        if not s:
            i += 1
            continue

        # 表格
        if s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            html.append(render_table(rows, links, here, used))
            continue

        # 标题
        m = re.match(r"^(#{2,3})\s+(.*)$", s)
        if m:
            level = len(m.group(1))
            text = m.group(2).strip()
            inner, u = inline(text, links, here)
            used.extend(u)
            if level == 2:
                h2, h3 = h2 + 1, 0
                anchor = f"s{h2}"
            else:
                h3 += 1
                anchor = f"s{h2}-{h3}"
            toc.append((level, anchor, text))
            html.append(f'<h{level} id="{anchor}">{inner}</h{level}>')
            i += 1
            continue

        # 引文
        if s.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip()[1:].strip())
                i += 1
            inner, u = inline(" ".join(x for x in buf if x), links, here)
            used.extend(u)
            html.append(f"<blockquote>{inner}</blockquote>")
            continue

        # 无序列表
        if re.match(r"^[-*]\s+", s):
            items = []
            while i < len(lines) and re.match(r"^[-*]\s+", lines[i].strip()):
                inner, u = inline(re.sub(r"^[-*]\s+", "", lines[i].strip()), links, here)
                used.extend(u)
                items.append(f"<li>{inner}</li>")
                i += 1
            html.append("<ul>" + "".join(items) + "</ul>")
            continue

        # 有序列表
        if re.match(r"^\d+\.\s+", s):
            items = []
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i].strip()):
                inner, u = inline(re.sub(r"^\d+\.\s+", "", lines[i].strip()), links, here)
                used.extend(u)
                items.append(f"<li>{inner}</li>")
                i += 1
            html.append("<ol>" + "".join(items) + "</ol>")
            continue

        # 段落
        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(
            r"^(#{2,3}\s|\||>|[-*]\s|\d+\.\s)", lines[i].strip()
        ):
            buf.append(lines[i].strip())
            i += 1
        inner, u = inline("".join(buf), links, here)
        used.extend(u)
        html.append(f"<p>{inner}</p>")
    return "\n".join(html), toc, used


def render_table(rows: list[str], links, here, used) -> str:
    def cells(row: str) -> list[str]:
        return [c.strip() for c in row.strip().strip("|").split("|")]

    head = cells(rows[0])
    body_rows = rows[1:]
    if body_rows and re.match(r"^[\s|:\-]+$", body_rows[0].replace("|", "")):
        align = body_rows[0]
        body_rows = body_rows[1:]
        cls = "tb"
    else:
        cls = "tb"
        align = ""
    out = [f'<div class="tablewrap"><table class="{cls}">']
    head_cells = []
    for h in head:
        inner, u = inline(h, links, here)
        used.extend(u)
        head_cells.append(f"<th>{inner}</th>")
    out.append("<thead><tr>" + "".join(head_cells) + "</tr></thead>")
    out.append("<tbody>")
    for r in body_rows:
        tds = []
        for c in cells(r):
            inner, u = inline(c, links, here)
            used.extend(u)
            tds.append(f"<td>{inner}</td>")
        out.append("<tr>" + "".join(tds) + "</tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


# --------------------------------------------------------------------------
# 模板
# --------------------------------------------------------------------------
CSS = r"""
:root{--blue:#315efb;--blue-l:#4e6ef2;--ink:#1f2329;--ink-2:#40454d;--ink-3:#6b7280;
--line:#e5e7eb;--bg:#f5f6f8;--card:#fff;--tag:#eef2ff;--warn:#fff7e6}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-size:15px;line-height:1.8;
font-family:"PingFang SC","Microsoft YaHei","Hiragino Sans GB","Source Han Sans SC",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
a{color:var(--blue-l);text-decoration:none}
a:hover{text-decoration:underline}
a.mw{color:var(--blue-l)}
a.mw.self{color:var(--ink-3);cursor:default}
header.topbar{position:sticky;top:0;z-index:50;background:#fff;border-bottom:1px solid var(--line);box-shadow:0 1px 2px rgba(0,0,0,.03)}
.topbar-in{max-width:1240px;margin:0 auto;padding:0 20px;height:56px;display:flex;align-items:center;gap:18px}
.logo{display:flex;align-items:baseline;gap:6px;font-weight:700;font-size:20px;letter-spacing:.5px;color:var(--blue)}
.logo small{font-size:11px;font-weight:400;color:var(--ink-3);letter-spacing:0}
.search{position:relative;flex:1;max-width:520px}
.search input{width:100%;border:2px solid var(--blue-l);border-radius:2px;padding:6px 12px;font-size:14px;outline:0;color:var(--ink-2)}
.search .results{position:absolute;top:38px;left:0;right:0;background:#fff;border:1px solid var(--line);
border-radius:2px;box-shadow:0 6px 18px rgba(0,0,0,.08);display:none;max-height:340px;overflow:auto;z-index:60}
.search .results div{padding:7px 12px;font-size:13px;cursor:pointer;border-bottom:1px solid #f2f3f5}
.search .results div:hover{background:#f7f9ff}
.search .results small{color:var(--ink-3);margin-left:6px}
.topbar nav{display:flex;gap:16px;font-size:13px;color:var(--ink-3)}
.topbar nav a{color:var(--ink-3)}
.crumb{max-width:1240px;margin:0 auto;padding:12px 20px 0;font-size:12px;color:var(--ink-3)}
.crumb a{color:var(--ink-3)}
.wrap{max-width:1240px;margin:0 auto;padding:0 20px 60px;display:grid;grid-template-columns:minmax(0,1fr) 336px;gap:24px;align-items:start}
.main{background:var(--card);border:1px solid var(--line);border-radius:3px;padding:26px 32px 40px}
.entry-tag{display:inline-block;font-size:12px;color:#fff;background:var(--blue-l);border-radius:2px;padding:1px 6px;margin-bottom:10px}
h1.entry-title{font-size:32px;line-height:1.3;margin:0 0 6px;font-weight:700;letter-spacing:1px}
.entry-sub{font-size:15px;color:var(--ink-3);margin:0 0 12px}
.entry-meta{font-size:12px;color:var(--ink-3);display:flex;flex-wrap:wrap;gap:14px;border-bottom:1px solid var(--line);padding-bottom:16px;margin-bottom:20px}
h2{font-size:20px;margin:34px 0 14px;padding-left:12px;border-left:4px solid var(--blue-l);line-height:1.4}
h3{font-size:16px;margin:22px 0 10px}
p{margin:0 0 12px;text-align:justify}
blockquote{margin:14px 0;padding:10px 16px;background:#fafbfc;border-left:3px solid var(--blue-l);color:var(--ink-2);font-size:14px}
ul,ol{margin:0 0 12px;padding-left:22px}
li{margin:4px 0}
.tablewrap{overflow-x:auto;margin:12px 0 18px}
table.tb{border-collapse:collapse;width:100%;font-size:14px}
table.tb th,table.tb td{border:1px solid var(--line);padding:7px 10px;vertical-align:top;text-align:left}
table.tb thead th{background:#f7f8fa;font-weight:600;white-space:nowrap}
table.tb tbody tr:nth-child(even){background:#fcfcfd}
.note{background:var(--warn);border:1px solid #ffe1a8;border-radius:2px;padding:10px 14px;font-size:13px;color:#7a5b13;margin:14px 0}
aside{display:flex;flex-direction:column;gap:16px;position:sticky;top:72px}
.infobox{border:1px solid #c9d2e3;border-radius:2px;overflow:hidden;background:#fff}
.infobox h3{margin:0;padding:9px 12px;font-size:14px;font-weight:600;color:#fff;
background:linear-gradient(90deg,#3f63d8,#5c7ce0);letter-spacing:.5px}
table.ib{width:100%;border-collapse:collapse;font-size:13px}
table.ib th,table.ib td{padding:7px 10px;border-bottom:1px solid #eef0f4;vertical-align:top;text-align:left}
table.ib th{width:84px;background:#fafbfd;color:var(--ink-2);font-weight:600;white-space:nowrap}
table.ib tr:last-child th,table.ib tr:last-child td{border-bottom:0}
.toc{border:1px solid var(--line);border-radius:2px;background:#fff;padding:12px 14px}
.toc h4{margin:0 0 8px;font-size:13px;color:var(--ink-2)}
.toc ol{margin:0;padding-left:0;list-style:none;font-size:13px;color:var(--ink-2)}
.toc ol li{margin:3px 0}
.toc ol ol{padding-left:14px;font-size:12.5px;color:var(--ink-3)}
.toc a{color:var(--ink-2)}
.sidecard{border:1px solid var(--line);border-radius:2px;background:#fff;padding:12px 14px;font-size:13px;color:var(--ink-2)}
.sidecard h4{margin:0 0 8px;font-size:13px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 0}
.chips a{background:var(--tag);border:1px solid #dbe3ff;color:#2f4ecb;border-radius:12px;padding:2px 10px;font-size:12px}
footer.foot{max-width:1240px;margin:0 auto;padding:0 20px 40px;font-size:12px;color:var(--ink-3)}
footer.foot .line{border-top:1px solid var(--line);padding-top:14px;display:flex;flex-wrap:wrap;gap:10px 18px;justify-content:space-between}
/* 首页 */
.hero{background:linear-gradient(135deg,#2f55d4,#5c7ce0);color:#fff;padding:52px 20px 46px}
.hero-in{max-width:1240px;margin:0 auto}
.hero h1{margin:0 0 8px;font-size:34px;letter-spacing:2px;border:0;padding:0;color:#fff}
.hero p{margin:0 0 22px;color:#dbe4ff;font-size:14px}
.hero .search{max-width:560px}
.hero .search input{border-color:#fff;height:42px}
.hero .search .results{top:46px;color:var(--ink)}
.cats{max-width:1240px;margin:26px auto 0;padding:0 20px;display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:18px;align-items:start}
.cat{background:#fff;border:1px solid var(--line);border-radius:3px;padding:18px 20px}
.cat h2{margin:0 0 10px;font-size:17px;border-left:4px solid var(--blue-l);padding-left:10px}
.cat ul{list-style:none;margin:0;padding:0}
.cat li{padding:7px 0;border-bottom:1px dashed #eef0f4;font-size:14px;display:block}
.cat li span{display:block;margin-top:2px}
.cat li:last-child{border-bottom:0}
.cat li span{color:var(--ink-3);font-size:12px}
.stats{max-width:1240px;margin:18px auto 60px;padding:0 20px;font-size:13px;color:var(--ink-3)}
@media (max-width:1020px){.wrap{grid-template-columns:1fr}aside{position:static;order:-1}.main{padding:20px}}
@media print{header.topbar,.crumb,.toc,.sidecard,footer.foot,.search{display:none}
body{background:#fff}.wrap{display:block;padding:0}.main{border:0;padding:0}aside{position:static;margin-top:18px}}
"""

SEARCH_JS = r"""
<script>
(function(){
  var INDEX = window.WIKI_INDEX || [];
  document.querySelectorAll('.search').forEach(function(box){
    var input = box.querySelector('input');
    var out = box.querySelector('.results');
    function render(q){
      var key = (q||'').trim().toLowerCase();
      if(!key){ out.style.display='none'; out.innerHTML=''; return; }
      var hits = INDEX.filter(function(e){
        return (e.t + ' ' + e.s + ' ' + (e.k||'')).toLowerCase().indexOf(key) >= 0;
      }).slice(0, 10);
      if(!hits.length){ out.innerHTML = '<div style="color:#9aa3b2;cursor:default">无匹配词条</div>'; out.style.display='block'; return; }
      out.innerHTML = hits.map(function(e){
        return '<div data-h="' + e.u + '">' + e.t + '<small>' + (e.c||'') + ' · ' + (e.s||'') + '</small></div>';
      }).join('');
      out.style.display = 'block';
    }
    input.addEventListener('input', function(){ render(input.value); });
    input.addEventListener('keydown', function(ev){
      if(ev.key === 'Enter'){
        var first = out.querySelector('div[data-h]');
        if(first){ location.href = first.getAttribute('data-h'); }
      }
    });
    out.addEventListener('click', function(ev){
      var d = ev.target.closest('div[data-h]');
      if(d){ location.href = d.getAttribute('data-h'); }
    });
    document.addEventListener('click', function(ev){
      if(!box.contains(ev.target)){ out.style.display='none'; }
    });
  });
})();
</script>
"""


def page(title: str, body: str, index_json: str, css_href: str = "assets/wiki.css") -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}_帝国百科</title>
<link rel="stylesheet" href="{css_href}">
</head>
<body>
{body}
<script>window.WIKI_INDEX = {index_json};</script>
{SEARCH_JS}
</body>
</html>
"""


def topbar(home: str = "index.html") -> str:
    return f"""<header class="topbar">
  <div class="topbar-in">
    <a class="logo" href="{home}">帝国百科<small>帝国官方在线百科</small></a>
    <form class="search" onsubmit="return false;">
      <input type="text" placeholder="搜索词条（机构 / 人物 / 概念）" aria-label="搜索词条">
      <div class="results"></div>
    </form>
    <nav><a href="{home}">首页</a><a href="{home}#cats">分类</a><a href="{home}#about">凡例</a></nav>
  </div>
</header>"""


# --------------------------------------------------------------------------
# 生成
# --------------------------------------------------------------------------
def load_entries():
    entries = {}
    for fn in sorted(os.listdir(SRC)):
        if not fn.endswith(".md"):
            continue
        path = os.path.join(SRC, fn)
        with open(path, encoding="utf-8") as fh:
            meta, body = parse_front(fh.read(), fn)
        entries[meta["slug"]] = {"meta": meta, "body": body}
    if not entries:
        raise SystemExit(f"未找到词条源文件：{SRC}")
    return entries


def build(check_only: bool = False):
    entries = load_entries()
    links = {e["meta"]["title"]: slug for slug, e in entries.items()}
    dups = len(entries) - len(links)
    if dups:
        raise SystemExit("存在重名词条（title 必须唯一）")

    parsed = {}
    backlinks = {slug: [] for slug in entries}
    for slug, e in entries.items():
        html, toc, used = md_to_html(e["body"], links, slug)
        parsed[slug] = {"html": html, "toc": toc}
        for u in dict.fromkeys(used):
            if u != slug and slug not in backlinks[u]:
                backlinks[u].append(slug)

    index = [
        {
            "t": e["meta"]["title"],
            "u": e["meta"]["slug"] + ".html",
            "c": e["meta"]["category"],
            "s": e["meta"].get("subtitle", ""),
            "k": e["meta"].get("summary", ""),
        }
        for e in (entries[s] for s in sorted(entries, key=lambda x: (CATEGORIES.index(entries[x]["meta"]["category"]), entries[x]["meta"]["title"])))
    ]
    index_json = json.dumps(index, ensure_ascii=False, separators=(",", ":"))

    if check_only:
        print(f"[校验] {len(entries)} 条 / 交叉链接全部可解析")
        return

    os.makedirs(os.path.join(BAIKE, "assets"), exist_ok=True)
    with open(os.path.join(BAIKE, "assets", "wiki.css"), "w", encoding="utf-8") as fh:
        fh.write(CSS.strip() + "\n")

    today = date.today().isoformat()

    # ---- 词条页 ----
    written = 0
    for slug, e in entries.items():
        meta = e["meta"]
        cat = meta["category"]
        toc_items = []
        for level, anchor, text in parsed[slug]["toc"]:
            toc_items.append((level, anchor, text))
        # 目录：两级
        toc_html = ["<div class=\"toc\"><h4>目录</h4><ol>"]
        h2n = 0
        for level, anchor, text in toc_items:
            text_html = esc(text)
            if level == 2:
                h2n += 1
                toc_html.append(f'<li><a href="#{anchor}">{h2n} {text_html}</a>')
            else:
                toc_html.append(f'<li style="margin-left:14px"><a href="#{anchor}">{text_html}</a></li>')
        toc_html.append("</ol></div>")
        # 修正：h3 应嵌在上一个 h2 的 li 内，简单起见改为平铺（已在样式上缩进）
        toc_block = "\n".join(toc_html).replace("</li>\n<li style=\"margin-left:14px\">", "<ol><li style=\"margin-left:0\">").replace(
            "<li style=\"margin-left:14px\">", "<li>"
        )

        box_rows = "".join(
            f'<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>' for k, v in meta["infobox"]
        )
        infobox = f"""<div class="infobox"><h3>{esc(meta['title'])}</h3>
<table class="ib">{box_rows}</table></div>"""

        bl = [entries[s]["meta"]["title"] for s in backlinks[slug]]
        back_html = ""
        if bl:
            back_html = (
                '<div class="sidecard"><h4>引用本条目的词条</h4><div class="chips">'
                + "".join(f'<a href="{links[t]}.html">{esc(t)}</a>' for t in bl)
                + "</div></div>"
            )

        related = [t for t in (meta.get("related", "") or "").split(",") if t.strip()]
        rel_html = ""
        if related:
            items = []
            for t in related:
                t = t.strip()
                if t in links:
                    items.append(f'<a href="{links[t]}.html">{esc(t)}</a>')
            if items:
                rel_html = f'<h2 id="related">相关条目</h2><div class="chips">{"".join(items)}</div>'

        meta_line = " · ".join(
            x
            for x in [
                f"分类：{cat}",
                f"最近更新：{meta.get('updated') or today}",
                "本词条依据《帝国主数据表(2026)》《全国官员名录(2026)》等设定文档整理",
            ]
            if x
        )

        body = f"""{topbar()}
<div class="crumb">帝国百科 &gt; <a href="index.html#cats">{cat}</a> &gt; <span>{esc(meta['title'])}</span></div>
<div class="wrap">
  <main class="main">
    <span class="entry-tag">{cat}词条</span>
    <h1 class="entry-title">{esc(meta['title'])}</h1>
    <p class="entry-sub">{esc(meta.get('subtitle',''))}</p>
    <div class="entry-meta"><span>{esc(meta_line)}</span></div>
    {parsed[slug]['html']}
    {rel_html}
  </main>
  <aside>
    {infobox}
    {toc_block}
    {back_html}
  </aside>
</div>
<footer class="foot"><div class="line">
  <span>帝国百科 · 词条内容按设定文档整理，数据截至 {today}。</span>
  <span>本页为架空历史设定演示 · 非真实出版物</span>
</div></footer>"""
        with open(os.path.join(BAIKE, f"{slug}.html"), "w", encoding="utf-8") as fh:
            fh.write(page(f"{meta['title']}（{cat}）", body, index_json))
        written += 1

    # ---- 首页 ----
    cats_html = []
    for cat in CATEGORIES:
        rows = []
        for slug in sorted(entries, key=lambda s: entries[s]["meta"]["title"]):
            m = entries[slug]["meta"]
            if m["category"] != cat:
                continue
            rows.append(
                f'<li><a href="{slug}.html">{esc(m["title"])}</a><span>{esc(m.get("subtitle",""))}</span></li>'
            )
        cats_html.append(
            f'<div class="cat"><h2>{cat}（{len(rows)}）</h2><ul>{"".join(rows)}</ul></div>'
        )

    home = f"""{topbar()}
<div class="hero"><div class="hero-in">
  <h1>帝国百科</h1>
  <p>继文十一年（2026）· 中华帝国国家与人物条目总集 · {len(entries)} 条</p>
  <form class="search" onsubmit="return false;">
    <input type="text" placeholder="输入词条名，如「国务院」「李先念」「三衡国策」" aria-label="搜索词条">
    <div class="results"></div>
  </form>
</div></div>
<div id="cats" class="cats">{"".join(cats_html)}</div>
<div id="about" class="stats">
凡例：本百科全部词条依据《中华帝国世界观总设定 v2.0》《帝国主数据表(2026)》《全国官员名录(2026)》《国民议会(2026)》《法律要目(2026)》《帝国高层人物小传(2026)》等设定文档整理；正文中的<b>蓝色词条</b>可直接点击跳转；标【推演】者为可调整的推演项。
</div>
<footer class="foot"><div class="line">
  <span>帝国百科 · 生成于 {today}</span>
  <span>本页为架空历史设定演示 · 非真实出版物</span>
</div></footer>"""
    with open(os.path.join(BAIKE, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(page("首页", home, index_json))

    total_links = sum(len(v) for v in backlinks.values())
    print(f"[百科] 词条 {written} 页 + 首页 1 页 / 交叉链接 {total_links} 条 / 索引 {len(index)} 项")


if __name__ == "__main__":
    build(check_only="--check" in sys.argv)
