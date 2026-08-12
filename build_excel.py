#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_excel.py — 读取 spells_clean.json + talents_clean.json + wowhead_cache.json
生成 分析报告.xlsx:
  Tab1 "施法次数": 中文名/图标/次数/占比/CPM/法力/射程/冷却/施法时间/描述
  Tab2 "天赋":    职业/专精/英雄天赋 + 选中天赋(中文名/图标/类型/描述/属性)
图标列直接嵌入 Wowhead 图标图片.
"""

import json, urllib.request
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image as XLImage
from openpyxl.cell.cell import Cell

SPELLS = json.loads(Path("spells_clean.json").read_text("utf-8"))
TALENTS = json.loads(Path("talents_clean.json").read_text("utf-8"))
WH = json.loads(Path("wowhead_cache.json").read_text("utf-8"))

ICON_BASE = "https://assets.rpglogs.cn/img/warcraft/abilities/"  # WCL 用的图标 CDN
WH_ICON_BASE = "https://nether.wowhead.com/images/wow/icons/medium/"  # wowhead 中图标

wb = Workbook()

# ── 样式 ──
HDR_FONT = Font(bold=True, color="FFFFFF", size=11)
HDR_FILL = PatternFill("solid", fgColor="4472C4")
THIN = Side(style="thin", color="DDDDDD")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP_TOP = Alignment(horizontal="left", vertical="top", wrap_text=True)
CENTER = Alignment(horizontal="center", vertical="center")

GROUP_CN = {"class": "职业", "spec": "专精", "hero": "英雄"}
GROUP_FILL = {"class": "D9E1F2", "spec": "E2EFDA", "hero": "FCE4D6"}


def wh(sid):
    """取 wowhead 缓存里的数据, sid 可能是 int/str."""
    return WH.get(str(sid), WH.get(sid, {}))


def style_header(ws, ncols, row=1):
    for col in range(1, ncols + 1):
        c = ws.cell(row=row, column=col)
        c.font = HDR_FONT
        c.fill = HDR_FILL
        c.alignment = CENTER
        c.border = BORDER


def fetch_icon(url, cache_dir="_icons"):
    """下载图标到本地缓存, 返回本地路径; 失败返回 None."""
    if not url:
        return None
    d = Path(cache_dir)
    d.mkdir(exist_ok=True)
    name = url.rsplit("/", 1)[-1]
    if not name:
        return None
    local = d / name
    if local.exists():
        return str(local)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            local.write_bytes(r.read())
        return str(local)
    except Exception:
        return None


def icon_url_for(spell_id):
    """用 WCL 图标 CDN (assets.rpglogs.cn), 文件名来自 wowhead icon 字段."""
    info = wh(spell_id)
    icon = (info.get("icon") or "").strip()
    if not icon:
        return ""
    if icon.startswith("http"):
        return icon
    return f"https://assets.rpglogs.cn/img/warcraft/abilities/{icon}.jpg"


# ════════════════════════════════════════════════════════════════════════
# Tab 1: 施法次数
# ════════════════════════════════════════════════════════════════════════
ws1 = wb.active
ws1.title = "施法次数"

headers1 = ["排名", "图标", "技能名", "Spell ID", "施法次数", "占比%", "CPM",
            "Uptime%", "法力/消耗", "射程", "施法时间", "技能描述"]
ws1.append(headers1)
style_header(ws1, len(headers1))

for i, s in enumerate(SPELLS, 1):
    info = wh(s["id"])
    row = [
        i, "", info.get("name") or s["name"], s["id"],
        s["count"], s["pct"], s["cpm"],
        s["uptime_pct"] if s["uptime_pct"] is not None else "-",
        info.get("cost", ""), info.get("range", ""),
        info.get("cast_time", ""), info.get("desc", ""),
    ]
    ws1.append(row)
    r = ws1.max_row
    for col in range(1, len(headers1) + 1):
        ws1.cell(row=r, column=col).border = BORDER
    ws1.cell(row=r, column=12).alignment = WRAP_TOP
    # 行高随描述长度
    desc_len = len(info.get("desc", "") or "")
    ws1.row_dimensions[r].height = max(28, min(120, 14 + desc_len // 40 * 14))

# 合计行
total = sum(s["count"] for s in SPELLS)
ws1.append(["", "", "合计", "", total, 100.0, "", "", "", "", "", ""])
r = ws1.max_row
for col in range(1, len(headers1) + 1):
    ws1.cell(row=r, column=col).font = Font(bold=True)
    ws1.cell(row=r, column=col).border = BORDER

# 列宽
widths1 = [6, 8, 16, 10, 10, 8, 8, 10, 14, 12, 12, 60]
for i, w in enumerate(widths1, 1):
    ws1.column_dimensions[get_column_letter(i)].width = w
ws1.freeze_panes = "C2"

# 嵌入图标
for i, s in enumerate(SPELLS, 1):
    url = icon_url_for(s["id"])
    local = fetch_icon(url)
    if local:
        try:
            img = XLImage(local)
            img.width = 24
            img.height = 24
            ws1.add_image(img, f"B{i+1}")
        except Exception:
            pass


# ════════════════════════════════════════════════════════════════════════
# Tab 2: 天赋
# ════════════════════════════════════════════════════════════════════════
ws2 = wb.create_sheet("天赋")

p = TALENTS["player"]
hero_name = next((h["name"] for h in TALENTS["heroTrees"] if h["id"] == p["heroSpecId"]), p["heroSpecId"])
ws2.append(["职业", p["className"], "专精", p["specName"], "英雄天赋", hero_name])
ws2.append(["天赋码", TALENTS["talentCode"], "", "", "", ""])
ws2.append([])  # 空行

headers2 = ["分组", "图标", "天赋名", "Spell ID", "类型", "选择/等级",
            "法力/消耗", "射程", "施法时间", "天赋描述"]
ws2.append(headers2)
style_header(ws2, len(headers2), row=ws2.max_row)

header_row = ws2.max_row
for t in TALENTS["selectedTalents"]:
    info = wh(t["spellId"])
    cn_name = info.get("name") or t["name"]
    row = [
        GROUP_CN.get(t["treeType"], t["treeType"]),
        "",
        cn_name,
        t["spellId"],
        t["type"],
        t["ranksChosen"] if t["ranksChosen"] is not None else "-",
        info.get("cost", ""),
        info.get("range", ""),
        info.get("cast_time", ""),
        info.get("desc", ""),
    ]
    ws2.append(row)
    r = ws2.max_row
    fill = PatternFill("solid", fgColor=GROUP_FILL.get(t["treeType"], "FFFFFF"))
    for col in range(1, len(headers2) + 1):
        ws2.cell(row=r, column=col).fill = fill
        ws2.cell(row=r, column=col).border = BORDER
    ws2.cell(row=r, column=10).alignment = WRAP_TOP
    desc_len = len(info.get("desc", "") or "")
    ws2.row_dimensions[r].height = max(28, min(140, 14 + desc_len // 45 * 14))

widths2 = [8, 8, 24, 10, 10, 10, 14, 12, 12, 65]
for i, w in enumerate(widths2, 1):
    ws2.column_dimensions[get_column_letter(i)].width = w
ws2.freeze_panes = ws2.cell(row=header_row + 1, column=3).coordinate

# 嵌入图标
for idx, t in enumerate(TALENTS["selectedTalents"]):
    r = header_row + 1 + idx
    url = icon_url_for(t["spellId"])
    local = fetch_icon(url)
    if local:
        try:
            img = XLImage(local)
            img.width = 24
            img.height = 24
            ws2.add_image(img, f"B{r}")
        except Exception:
            pass

# ── 保存 ──
out = "分析报告.xlsx"
wb.save(out)
print(f"✅ 已生成 {out}")
print(f"   施法次数 tab: {len(SPELLS)} 条技能 (含图标/描述)")
print(f"   天赋 tab: {len(TALENTS['selectedTalents'])} 个天赋 (含图标/描述)")
print(f"   图标缓存: _icons/")
