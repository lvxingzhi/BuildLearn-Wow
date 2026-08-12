#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cleanse_talents.py — 清洗天赋树HTML为结构化JSON
"""

import json
import re
from pathlib import Path

raw = Path("天赋树HTML").read_text("utf-8")

# ── 提取 dehydratedBuild ──
m = re.search(r"const tree = JSON\.parse\s*\(\s*'([^']+)'\s*\)", raw, re.DOTALL)
if not m:
    raise ValueError("未找到 dehydratedBuild")
build_str = m.group(1).replace("\\u0022", '"').replace("\\/", "/")
build_data = json.loads(build_str)

dehy = build_data.get("dehydratedBuild", {})
change_set = dehy.get("changeSet", {})
selected_groups = dehy.get("selectedNodes", [])
selected_ids = []
for group in selected_groups:
    for item in group:
        val = item[0] if isinstance(item, list) else item
        selected_ids.append(val)

hero_spec_id = dehy.get("heroSpecId")
talent_code = dehy.get("exportCodeParams", {}).get("exportCode", "")

# ── 提取蓝图节点 ──
# 直接从 HTML 中提取 nodeId -> abilities 的映射
# 匹配格式: "nodeId": NNN, ... "abilities": [{ ... }, ...]
# 简单取每个 node 的第一条 ability
nodes_map = {}

# 把 raw 清理一下以便于正则匹配
clean = raw.replace("\\u0022", '"').replace("\\/", "/")

# 提取 allNodes 数组的 JSON
m_all = re.search(r'"allNodes"\s*:\s*\[(.+?)\]', clean, re.DOTALL)
if m_all:
    nodes_json_str = m_all.group(0).replace('\\"', '"')
    # 去掉一些少见的 unicode 转义
    nodes_json_str = nodes_json_str.replace('"', '"')
    try:
        all_nodes = json.loads(nodes_json_str)
        for node in all_nodes:
            nid = node.get("nodeId")
            if not nid:
                continue
            abilities = node.get("abilities", [])
            if abilities:
                ab = abilities[0]
                nodes_map[nid] = {
                    "name": ab.get("name", ""),
                    "spellId": ab.get("spellId", 0),
                    "type": ab.get("type", ""),
                    "maxRanks": ab.get("maxRanks", 1),
                    "icon": ab.get("icon", ""),
                    "treeType": node.get("treeType", ""),
                    "row": node.get("row", 0),
                    "heroTreeId": node.get("heroTreeId"),
                }
            else:
                nodes_map[nid] = {
                    "name": "空节点", "spellId": 0,
                    "type": "node", "treeType": node.get("treeType", ""),
                    "row": node.get("row", 0),
                }
    except json.JSONDecodeError as e:
        print(f"⚠️ allNodes JSON 解析失败: {e}")
else:
    print("⚠️ 未找到 allNodes 数组")

# 如果 JSON 解析失败，用正则逐个提取 node
if not nodes_map:
    for match in re.finditer(
        r'"nodeId"\s*:\s*(\d+)\s*.*?"abilities"\s*:\s*\[(.+?)\]',
        clean, re.DOTALL
    ):
        nid = int(match.group(1))
        ab_str = '{' + match.group(2).strip() + '}'
        # 取第一个
        m_ab = re.search(r'"id"\s*:\s*(\d+)\s*,\s*"name"\s*:\s*"([^"]*)"', ab_str)
        if m_ab:
            nodes_map[nid] = {
                "name": m_ab.group(2),
                "spellId": int(m_ab.group(1)),
                "type": "active" if "active" in ab_str else "passive",
                "treeType": "class" if "treeType" in ab_str else "spec",
            }

print(f"找到 {len(nodes_map)} 个节点")

# ── 已选节点详情 ──
selected_detailed = []
for nid in selected_ids:
    node = nodes_map.get(nid, {"name": "未知", "type": "unknown", "spellId": 0})
    selected_detailed.append({
        "node_id": nid,
        "name": node["name"],
        "type": node.get("type", ""),
        "spellId": node.get("spellId", 0),
        "treeType": node.get("treeType", ""),
        "row": node.get("row", 0),
    })

result = {
    "class_name": change_set.get("className"),
    "spec_name": change_set.get("specName"),
    "hero_spec_id": hero_spec_id,
    "class_icon": build_data.get("classIcon", ""),
    "spec_icon": build_data.get("specIcon", ""),
    "talent_code": talent_code,
    "all_nodes_count": len(nodes_map),
    "selected_count": len(selected_ids),
    "selected_nodes": selected_detailed,
    "all_nodes": {str(k): v for k, v in nodes_map.items()},
}

with open("talents_clean.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\n✅ 天赋清洗完成")
print(f"  职业: {result['class_name']} / 专精: {result['spec_name']}")
print(f"  英雄天赋 ID: {result['hero_spec_id']}")
print(f"  蓝图节点数: {result['all_nodes_count']}")
print(f"  已选节点数: {result['selected_count']}")

for i, n in enumerate(selected_detailed[:20]):
    print(f"  {i+1:2d}. id={n['node_id']} → {n['name']:35s} ({n['type']:>8s}, {n['treeType']})")
if len(selected_detailed) > 20:
    print(f"  ...还有 {len(selected_detailed) - 20} 个")