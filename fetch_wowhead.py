#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_wowhead.py — 用 nether.wowhead.com tooltip 接口抓取中文名+描述,缓存到JSON
读取: spells_clean.json + talents_clean.json 里的所有 spellId
输出: wowhead_cache.json  { spellId: {name, icon, desc, cost, range, cooldown, cast_time} }
"""

import json, re, time
from pathlib import Path
import requests
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
API = "https://nether.wowhead.com/tooltip/spell/{sid}?locale=zhCN"

# 收集所有 spellId (施法列表 + 天赋列表)
spells = json.loads(Path("spells_clean.json").read_text("utf-8"))
talents = json.loads(Path("talents_clean.json").read_text("utf-8"))

ids = {s["id"] for s in spells}
ids |= {t["spellId"] for t in talents["selectedTalents"] if t.get("spellId")}
ids.discard(0)  # hero tree 顶层节点 spellId=0 跳过
ids = sorted(ids)
print(f"共 {len(ids)} 个唯一 spellId 需要抓取")


def parse_tooltip(tip_html: str) -> dict:
    """从 tooltip HTML 片段里提取: 描述/法力消耗/射程/冷却/施法时间"""
    soup = BeautifulSoup(tip_html, "lxml")
    # 描述: 在 <div class="q"> 里 (绿色描述文本)
    desc_parts = [d.get_text(" ", strip=True) for d in soup.select("div.q")]
    desc = "\n".join(p for p in desc_parts if p)
    # 清理注释 <!--xxx-->
    desc = re.sub(r"<!--.*?-->", "", desc).strip()

    text = soup.get_text(" ", strip=True)
    text = re.sub(r"<!--.*?-->", "", text)

    def find(pat):
        m = re.search(pat, text)
        return m.group(1) if m else ""

    return {
        "desc": desc,
        "cost": find(r"([\d.]+\s*%?\s*(?:法力值|法力|Mana|怒气|能量|Rage|Energy))"),
        "range": find(r"(\d+\s*码范围|\d+\s*yd range)"),
        "cooldown": find(r"(\d+(?:\.\d+)?\s*(?:秒|分|min|sec)\s*cooldown)"),
        "cast_time": find(r"(瞬发|Instant|\d+(?:\.\d+)?\s*秒\s*施法)"),
    }


cache = {}
sess = requests.Session()
sess.headers.update({"User-Agent": UA, "Accept": "application/json"})

for i, sid in enumerate(ids, 1):
    if sid in cache:
        continue
    try:
        r = sess.get(API.format(sid=sid), timeout=15)
        if r.status_code != 200:
            print(f"  [{i}/{len(ids)}] {sid} → HTTP {r.status_code}")
            cache[sid] = {"name": "", "icon": "", "desc": "", "error": f"http {r.status_code}"}
            continue
        d = r.json()
        parsed = parse_tooltip(d.get("tooltip", ""))
        cache[sid] = {
            "name": d.get("name", ""),
            "icon": d.get("icon", ""),
            **parsed,
        }
        print(f"  [{i}/{len(ids)}] {sid} → {cache[sid]['name']}")
    except Exception as e:
        print(f"  [{i}/{len(ids)}] {sid} → ERR {e}")
        cache[sid] = {"name": "", "icon": "", "desc": "", "error": str(e)}
    time.sleep(0.3)  # 礼貌限速

Path("wowhead_cache.json").write_text(
    json.dumps(cache, ensure_ascii=False, indent=2), "utf-8"
)
print(f"\n✅ 抓取完成,缓存 {len(cache)} 条 → wowhead_cache.json")
