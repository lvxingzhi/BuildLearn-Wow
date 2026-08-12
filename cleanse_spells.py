#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cleanse_spells.py — 清洗施法次数HTML为结构化JSON
"""

import json, re
from pathlib import Path

HTML = Path("施法次数HTML").read_text("utf-8")

# 提取所有技能行
rows = re.findall(
    r'main-table-row-(\d+)-42-0-\d+.*?'
    r'<span[^>]*id="ability-\1"[^>]*>([^<]+)</span>.*?'
    r'<span[^>]*class="report-amount-total"[^>]*>([^<]+)</span>',
    HTML, re.DOTALL
)

print(f"匹配到 {len(rows)} 行")
for r in rows[:3]:
    print(r)

# 如果正则不好用，换 BeautifulSoup
from bs4 import BeautifulSoup
soup = BeautifulSoup(HTML, "lxml")

spells = []
for tr in soup.find("tbody").find_all("tr", recursive=False):
    if tr.get("id", "").startswith("main-table-row-totals"):
        continue

    # spell id
    m = re.search(r"toggleGraphEntry\('(\d+)'\)", tr.get("onclick", ""))
    if not m:
        continue
    sid = int(m.group(1))

    # 技能名
    name_el = tr.find("span", id=re.compile(r"^ability-\d+-\d+$"))
    name = name_el.get_text(strip=True) if name_el else ""

    # 次数
    count_el = tr.find("span", class_="report-amount-total")
    count = int(count_el.get_text(strip=True)) if count_el else 0

    # 百分比
    pct_el = tr.find("div", class_="report-amount-percent")
    pct = float(pct_el.get_text(strip=True).replace("%", "")) if pct_el else 0.0

    # CPM
    cpm_el = tr.find("td", class_="main-table-number primary main-per-second-amount")
    cpm = float(cpm_el.get_text(strip=True)) if cpm_el else 0.0

    # uptime
    uptime_el = tr.find("td", class_="uptime-percent")
    uptime = None
    if uptime_el:
        ut = uptime_el.get_text(strip=True).replace("%", "")
        if ut and ut != "-":
            try: uptime = float(ut)
            except: pass

    spells.append({
        "id": sid,
        "name": name,
        "count": count,
        "pct": pct,
        "cpm": cpm,
        "uptime_pct": uptime,
    })

# 按次数排序
spells.sort(key=lambda x: x["count"], reverse=True)

with open("spells_clean.json", "w", encoding="utf-8") as f:
    json.dump(spells, f, ensure_ascii=False, indent=2)

print(f"\n✅ 清洗完成,共 {len(spells)} 条")
for s in spells[:5]:
    print(f"  {s['name']:15s} → {s['count']:4d}次 ({s['pct']}%)")