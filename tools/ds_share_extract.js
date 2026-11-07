// 从 chat.deepseek.com 分享页的渲染后 DOM 中抽取对话正文，输出拼接 HTML 片段，
// 交给 pandoc 转 markdown。用法: node ds_share_extract.js <dom.html> <out-frag.html>
const fs = require('fs');
const src = fs.readFileSync(process.argv[2], 'utf8');
const out = process.argv[3];

const starts = [];
const re = /class="[^"]*\bds-message\b/g;
let m;
while ((m = re.exec(src)) !== null) starts.push(m.index);
if (starts.length === 0) { console.error('no ds-message found'); process.exit(1); }

const KEEP = 'p|div|h[1-6]|ul|ol|li|table|thead|tbody|tr|td|th|pre|code|blockquote|strong|em|b|i|br|hr|sup|sub';
function cleanTags(html) {
  return html.replace(new RegExp('<(?!/?(?:' + KEEP + ')\\b)[^>]*>', 'gi'), '');
}

function textOf(html) {
  let t = html
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/<style[\s\S]*?<\/style>/gi, '')
    .replace(/<svg[\s\S]*?<\/svg>/gi, '');
  t = t.replace(/<\/(p|div|li|h1|h2|h3|h4|h5|h6|tr|pre|blockquote|table)>/gi, '\n')
       .replace(/<br\s*\/?>/gi, '\n')
       .replace(/<[^>]+>/g, '');
  t = t.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"')
       .replace(/&#39;/g, "'").replace(/&amp;/g, '&').replace(/&nbsp;/g, ' ');
  return t.replace(/[ \t]+/g, ' ').replace(/\n{3,}/g, '\n\n').trim();
}

// 回退到包含该 class 的 <div 起点，避免把标签切成半截
function tagStart(idx) {
  const i = src.lastIndexOf('<div', idx);
  return i >= 0 ? i : idx;
}

const frags = [];
for (let i = 0; i < starts.length; i++) {
  const s = tagStart(starts[i]);
  const e = i + 1 < starts.length ? tagStart(starts[i + 1]) : src.length;
  const seg = src.slice(s, e);
  const isUser = /d29f3d7d\s+ds-message/.test(seg.slice(0, 120));
  const role = isUser ? '用户' : 'DeepSeek';
  let content;
  if (isUser) {
    // 用户消息是纯文本，直接抽文本再包成段落，避免残留 UI 图标/按钮
    const txt = textOf(seg)
      .split('\n')
      .map((l) => l.trim())
      .filter((l) => l && !/^(复制|编辑|分享|下载|重新生成|查看全部|已思考|深度思考|联网搜索|搜索到|浏览)/.test(l));
    content = txt.map((l) => '<p>' + l.replace(/&/g, '&amp;').replace(/</g, '&lt;') + '</p>').join('\n');
  } else {
    const mt = seg.match(/ds-assistant-message-main-content[^>]*>([\s\S]*)/);
    content = mt ? mt[1] : seg;
  }
  frags.push(`<h2>${role} #${i}</h2>\n` + cleanTags(content) + '\n\n<hr/>\n');
  console.error(`#${i} ${role} rawLen=${seg.length}`);
}

fs.writeFileSync(out, `<!doctype html><html><body>\n${frags.join('\n')}\n</body></html>`, 'utf8');
console.error('wrote ' + out);
