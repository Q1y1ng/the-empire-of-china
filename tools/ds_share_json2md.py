#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 DeepSeek 分享页的 JSON（/api/v0/share/content 返回体）转成 markdown 对话。

为什么要走 API：分享页的正文在前端虚拟列表里，headless dump-dom 只能拿到
「当前渲染窗口」的消息（实测 41 轮只渲染出 19 轮）。官方接口一次返回全部：

    GET https://chat.deepseek.com/api/v0/share/content?share_id=<share_id>

用法：
    py -3 tools/ds_share_json2md.py <share.json> --qa OUT_QA.md --think OUT_THINK.md

输出：
    --qa     问题 + 回答正文（THINK 只留「思考用时」一行）
    --think  每轮思考过程全文（备用，通常不必通读）
"""
import argparse
import json
import re
import sys


def frag_text(frag):
    if frag.get("type") == "FILE":
        names = [f.get("file_name", "?") for f in frag.get("files") or []]
        return "[附件：" + "、".join(names) + "]\n\n" if names else ""
    c = frag.get("content")
    return (c or "") + "\n\n" if c else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_path")
    ap.add_argument("--qa", default="qa.md")
    ap.add_argument("--think", default="think.md")
    a = ap.parse_args()

    with open(a.json_path, encoding="utf-8") as f:
        data = json.load(f)
    biz = data["data"]["biz_data"]
    msgs = biz["messages"]

    qa, th = [], []
    qa.append(f"# 对话原文（问与答）· {biz.get('title', '')}\n")
    th.append(f"# 对话原文（思考过程）· {biz.get('title', '')}\n")

    round_no = 0
    for m in msgs:
        role = m["role"]
        frags = m.get("fragments") or []
        if role == "USER":
            round_no += 1
            qa.append(f"\n---\n\n## R{round_no} · 用户\n")
            for fr in frags:
                qa.append(frag_text(fr))
        else:
            think_secs = sum((fr.get("elapsed_secs") or 0) for fr in frags if fr["type"] == "THINK")
            head = f"\n---\n\n## R{round_no} · DeepSeek（思考 {think_secs}s）\n"
            qa.append(head)
            for fr in frags:
                t = fr["type"]
                if t == "RESPONSE":
                    qa.append(frag_text(fr))
                elif t == "TOOL_SEARCH":
                    c = (fr.get("content") or "").strip()
                    if c:
                        qa.append(f"> 〔联网检索〕{c}\n\n")
                elif t == "TIP":
                    pass
            th.append(f"\n---\n\n## R{round_no} · 思考（{think_secs}s）\n")
            for fr in frags:
                if fr["type"] == "THINK":
                    th.append(frag_text(fr))

    def tidy(lines):
        s = "".join(lines)
        s = re.sub(r"[ \t]+\n", "\n", s)
        s = re.sub(r"\n{3,}", "\n\n", s)
        return s.strip() + "\n"

    with open(a.qa, "w", encoding="utf-8", newline="\n") as f:
        f.write(tidy(qa))
    with open(a.think, "w", encoding="utf-8", newline="\n") as f:
        f.write(tidy(th))
    print(f"rounds={round_no} qa={len(tidy(qa))} chars think={len(tidy(th))} chars", file=sys.stderr)


if __name__ == "__main__":
    main()
