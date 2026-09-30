#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch_wowhead.py — 用 nether.wowhead.com tooltip 接口抓中文名+描述

读取: data/clean/spells.json + data/clean/talents.json 里的所有 spellId
输出: cache/wowhead_cache.json
      { spellId: {name, icon, desc, cost, range, cooldown, cast_time} }

注意: 每次运行都全量重抓并覆盖, 不复用旧缓存 —— Wowhead 描述会随版本变化。

用法:
    python3 src/fetch_wowhead.py [--spells X.json] [--talents Y.json] [--cache Z.json] [--sleep 0.3]
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
API = "https://nether.wowhead.com/tooltip/spell/{sid}?locale=zhCN"


def parse_tooltip(tip_html):
    """从 tooltip HTML 片段提取: 描述/法力消耗/射程/冷却/施法时间."""
    soup = BeautifulSoup(tip_html, "lxml")
    # 描述: 在 <div class="q"> 里 (绿色描述文本)
    desc_parts = [d.get_text(" ", strip=True) for d in soup.select("div.q")]
    desc = "\n".join(p for p in desc_parts if p)
    desc = re.sub(r"<!--.*?-->", "", desc).strip()

    text = re.sub(r"<!--.*?-->", "", soup.get_text(" ", strip=True))

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


def collect_ids(spells_path, talents_path):
    spells = json.loads(Path(spells_path).read_text("utf-8"))
    talents = json.loads(Path(talents_path).read_text("utf-8"))
    ids = {s["id"] for s in spells}
    ids |= {t["spellId"] for t in talents["selectedTalents"] if t.get("spellId")}
    ids.discard(0)   # hero tree 顶层节点 spellId=0, 跳过
    ids.discard(None)
    return sorted(i for i in ids if i)


def main():
    ap = argparse.ArgumentParser(description="抓取 Wowhead 中文名与描述")
    ap.add_argument("--spells", help="默认 data/clean/spells.json")
    ap.add_argument("--talents", help="默认 data/clean/talents.json")
    ap.add_argument("--cache", help="默认 cache/wowhead_cache.json")
    ap.add_argument("--sleep", type=float, default=0.3, help="每次请求间隔秒 (礼貌限速)")
    args = ap.parse_args()

    config.ensure_dirs()
    spells_path = config.require(
        Path(args.spells) if args.spells else config.CLEAN_DIR / "spells.json",
        "先跑 python3 src/cleanse_spells.py")
    talents_path = config.require(
        Path(args.talents) if args.talents else config.CLEAN_DIR / "talents.json",
        "先跑 python3 src/cleanse_talents.py")
    out = Path(args.cache) if args.cache else config.CACHE_DIR / "wowhead_cache.json"

    ids = collect_ids(spells_path, talents_path)
    print("共 {} 个唯一 spellId 需要抓取".format(len(ids)))

    cache = {}
    failed = []
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA, "Accept": "application/json"})

    for i, sid in enumerate(ids, 1):
        try:
            r = sess.get(API.format(sid=sid), timeout=15)
            if r.status_code != 200:
                cache[sid] = {"name": "", "icon": "", "desc": "",
                              "error": "http {}".format(r.status_code)}
                failed.append(sid)
                print("  [{}/{}] {} → HTTP {}".format(i, len(ids), sid, r.status_code))
                continue
            d = r.json()
            cache[sid] = {"name": d.get("name", ""), "icon": d.get("icon", ""),
                          **parse_tooltip(d.get("tooltip", ""))}
            print("  [{}/{}] {} → {}".format(i, len(ids), sid, cache[sid]["name"]))
        except Exception as e:
            cache[sid] = {"name": "", "icon": "", "desc": "", "error": str(e)}
            failed.append(sid)
            print("  [{}/{}] {} → ERR {}".format(i, len(ids), sid, e))
        time.sleep(args.sleep)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(cache, ensure_ascii=False, indent=2), "utf-8")
    print("\n✅ 抓取完成, 缓存 {} 条 → {}".format(len(cache), config.rel(out)))
    if failed:
        print("⚠️  其中 {} 条失败, Excel 里会回退用 WCL 的英文名: {}".format(
            len(failed), failed[:10]))


if __name__ == "__main__":
    main()
