#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cleanse_spells.py — 清洗施法次数 HTML → data/clean/spells.json

用法:
    python3 src/cleanse_spells.py                 # 默认输入 data/raw/casts.html
    python3 src/cleanse_spells.py --casts X.html --out Y.json
"""

import argparse
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402


def parse(html):
    """从 casts 页面 HTML 提取技能列表."""
    soup = BeautifulSoup(html, "lxml")
    tbody = soup.find("tbody")
    if tbody is None:
        raise SystemExit("❌ HTML 里没有找到表格, 可能不是 casts 页面")

    spells = []
    for tr in tbody.find_all("tr", recursive=False):
        if tr.get("id", "").startswith("main-table-row-totals"):
            continue

        # spell id: 藏在 onclick 的 toggleGraphEntry('123') 里
        m = re.search(r"toggleGraphEntry\('(\d+)'\)", tr.get("onclick", ""))
        if not m:
            continue
        sid = int(m.group(1))

        name_el = tr.find("span", id=re.compile(r"^ability-\d+-\d+$"))
        name = name_el.get_text(strip=True) if name_el else ""

        count_el = tr.find("span", class_="report-amount-total")
        count = int(count_el.get_text(strip=True)) if count_el else 0

        pct_el = tr.find("div", class_="report-amount-percent")
        pct = float(pct_el.get_text(strip=True).replace("%", "")) if pct_el else 0.0

        cpm_el = tr.find("td", class_="main-table-number primary main-per-second-amount")
        cpm = float(cpm_el.get_text(strip=True)) if cpm_el else 0.0

        uptime = None
        uptime_el = tr.find("td", class_="uptime-percent")
        if uptime_el:
            ut = uptime_el.get_text(strip=True).replace("%", "")
            if ut and ut != "-":
                try:
                    uptime = float(ut)
                except ValueError:
                    pass

        spells.append({
            "id": sid,
            "name": name,
            "count": count,
            "pct": pct,
            "cpm": cpm,
            "uptime_pct": uptime,
        })

    spells.sort(key=lambda x: x["count"], reverse=True)
    return spells


def main():
    ap = argparse.ArgumentParser(description="清洗施法次数 HTML")
    ap.add_argument("--casts", help="casts 页面 HTML 路径 (默认 data/raw/casts.html)")
    ap.add_argument("--out", help="输出 JSON 路径 (默认 data/clean/spells.json)")
    args = ap.parse_args()

    config.ensure_dirs()
    src = config.require(
        Path(args.casts) if args.casts else config.find_input("casts"),
        "从 WCL 保存 casts 页面 (?type=casts&source=<src>) 后放到这里",
    )

    spells = parse(src.read_text("utf-8"))

    out = Path(args.out) if args.out else config.CLEAN_DIR / "spells.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(spells, ensure_ascii=False, indent=2), "utf-8")

    print("✅ {} → {} 共 {} 条".format(config.rel(src), config.rel(out), len(spells)))
    for s in spells[:5]:
        print("   {:15s} → {:4d}次 ({}%)".format(s["name"], s["count"], s["pct"]))


if __name__ == "__main__":
    main()
