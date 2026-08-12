#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cleanse_talents.py — 清洗天赋树HTML为结构化JSON

天赋树HTML里有两段关键JSON:
  1. dehydratedBuild  → 玩家选了哪些节点 (selectedNodes) + 英雄天赋 (heroSpecId)
  2. changeSet.allNodes → 所有节点的完整定义 (name/spellId/icon/row/treeType...)

流程: 提取两段JSON → 用selectedNodes去allNodes查详情 → 输出"玩家实际点的天赋列表"
"""

import json
from pathlib import Path

HTML = Path("天赋树HTML").read_text("utf-8")


def extract_json_after_marker(html: str, marker: str) -> dict:
    """从 marker 位置开始,提取一个完整的 JSON 对象(平衡花括号,处理字符串转义)."""
    start = html.find(marker)
    if start < 0:
        return None
    brace_start = html.find("{", start)
    depth = 0
    in_str = False
    esc = False
    for i in range(brace_start, len(html)):
        c = html[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    raw = html[brace_start : i + 1]
                    raw = raw.replace("\\u0022", '"')  # JSON.parse 参数里的引号转义
                    return json.loads(raw)
    return None


# --- 1. dehydratedBuild: 玩家选择 ---
dehydrated = extract_json_after_marker(HTML, "const tree = JSON.parse")
dbh = dehydrated["dehydratedBuild"]
cs = dbh["changeSet"]
selected = dbh["selectedNodes"]           # [[102465],[102567,1],...]
hero_spec_id = dbh.get("heroSpecId")
class_name = cs.get("className")
spec_name = cs.get("specName")
talent_code = dehydrated["exportCodeParams"].get("exportCode", "")

# selectedNodes 里每个 entry = [abilityId] 或 [abilityId, rankOrChoice]
selected_map = {item[0]: (item[1] if len(item) > 1 else None) for item in selected}
print(f"玩家: {class_name} {spec_name}  英雄天赋ID: {hero_spec_id}")
print(f"选中节点数: {len(selected_map)}")

# --- 2. changeSet.allNodes: 所有节点完整定义 ---
blueprint = extract_json_after_marker(HTML, "Object.assign(talentTreeBlueprintCache")
# 结构: { "<Class>_<Spec>_<id>": { changeSet, heroTrees, ... } }
inner = next(v for v in blueprint.values() if isinstance(v, dict))
all_nodes = inner["changeSet"]["allNodes"]
hero_trees = inner.get("heroTrees", [])
print(f"全节点数: {len(all_nodes)}  英雄天赋树候选: {[h['name'] for h in hero_trees]}")

# --- 3. 拼接: 玩家实际选中的天赋详情 ---
# allNodes 里: type=choice 的节点有多个 abilities, 玩家 selectedNodes 里的 id 对应其中一个 ability.id
chosen = []
for node in all_nodes:
    for ab in node.get("abilities", []):
        if ab["id"] in selected_map:
            chosen.append({
                "nodeId": node["nodeId"],
                "abilityId": ab["id"],
                "name": ab["name"],
                "spellId": ab.get("spellId"),
                "icon": ab.get("icon"),
                "type": ab.get("type"),            # passive/active/capstone
                "treeType": node.get("treeType"),   # class/spec/hero
                "row": node.get("row"),
                "posX": node.get("posX"),
                "maxRanks": node.get("maxRanks"),
                "ranksChosen": selected_map[ab["id"]],  # 选了几级 / choice 索引
                "heroTreeId": ab.get("heroTreeId"),
            })

order = {"class": 0, "spec": 1, "hero": 2}
chosen.sort(key=lambda x: (order.get(x["treeType"], 9), x["row"] or 0, x["posX"] or 0))

result = {
    "player": {"className": class_name, "specName": spec_name, "heroSpecId": hero_spec_id},
    "heroTrees": hero_trees,
    "talentCode": talent_code,
    "selectedTalents": chosen,
}

with open("talents_clean.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\n✅ 清洗完成,玩家实际选中 {len(chosen)} 个天赋:")
for t in chosen[:8]:
    print(f"  [{t['treeType']:5s}] {t['name']:28s} spell={t['spellId']} ranks={t['ranksChosen']}")
print(f"  ... (共 {len(chosen)} 个)")
