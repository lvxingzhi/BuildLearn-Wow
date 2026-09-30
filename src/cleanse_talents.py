#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cleanse_talents.py — 清洗天赋树 HTML → data/clean/talents.json

天赋树HTML 里嵌了两段关键 JSON:
  1. dehydratedBuild         → 玩家选了哪些节点 (selectedNodes) + 英雄天赋 (heroSpecId)
  2. changeSet.allNodes      → 所有节点的完整定义 (name/spellId/icon/row/treeType...)

流程: 提取两段 JSON → 用 selectedNodes 去 allNodes 查详情 → 玩家实际点的天赋列表

用法:
    python3 src/cleanse_talents.py                   # 默认输入 data/raw/talents.html
    python3 src/cleanse_talents.py --talents X.html --out Y.json
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402


def extract_json_after_marker(html, marker):
    """从 marker 位置开始, 提取一个完整 JSON 对象 (平衡花括号 + 处理字符串转义)."""
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
                    raw = html[brace_start:i + 1]
                    raw = raw.replace("\\u0022", '"')  # JSON.parse 参数里的引号转义
                    return json.loads(raw)
    return None


def parse(html):
    """解析天赋树 HTML, 返回 {player, heroTrees, talentCode, selectedTalents}."""
    dehydrated = extract_json_after_marker(html, "const tree = JSON.parse")
    if not dehydrated:
        raise SystemExit("❌ 没找到 dehydratedBuild, 可能不是天赋树页面")
    dbh = dehydrated["dehydratedBuild"]
    cs = dbh["changeSet"]
    selected = dbh["selectedNodes"]          # [[102465], [102567, 1], ...]
    hero_spec_id = dbh.get("heroSpecId")
    class_name = cs.get("className")
    spec_name = cs.get("specName")
    talent_code = dehydrated["exportCodeParams"].get("exportCode", "")

    # selectedNodes 里每个 entry = [abilityId] 或 [abilityId, rankOrChoice]
    selected_map = {item[0]: (item[1] if len(item) > 1 else None) for item in selected}

    blueprint = extract_json_after_marker(html, "Object.assign(talentTreeBlueprintCache")
    if not blueprint:
        raise SystemExit("❌ 没找到 talentTreeBlueprintCache, 可能不是天赋树页面")
    # 结构: { "<Class>_<Spec>_<id>": { changeSet, heroTrees, ... } }
    inner = next(v for v in blueprint.values() if isinstance(v, dict))
    all_nodes = inner["changeSet"]["allNodes"]
    hero_trees = inner.get("heroTrees", [])

    print("玩家: {} {}   英雄天赋ID: {}".format(class_name, spec_name, hero_spec_id))
    print("全节点 {} 个, 选中 {} 个, 英雄天赋树候选: {}".format(
        len(all_nodes), len(selected_map), [h["name"] for h in hero_trees]))

    # allNodes 里 type=choice 的节点有多个 abilities,
    # 玩家 selectedNodes 里的 id 对应其中一个 ability.id
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
                    "type": ab.get("type"),             # passive/active/capstone
                    "treeType": node.get("treeType"),   # class/spec/hero
                    "row": node.get("row"),
                    "posX": node.get("posX"),
                    "maxRanks": node.get("maxRanks"),
                    "ranksChosen": selected_map[ab["id"]],   # 选了几级 / choice 索引
                    "heroTreeId": ab.get("heroTreeId"),
                })

    order = {"class": 0, "spec": 1, "hero": 2}
    chosen.sort(key=lambda x: (order.get(x["treeType"], 9), x["row"] or 0, x["posX"] or 0))

    return {
        "player": {"className": class_name, "specName": spec_name,
                   "heroSpecId": hero_spec_id},
        "heroTrees": hero_trees,
        "talentCode": talent_code,
        "selectedTalents": chosen,
    }


def main():
    ap = argparse.ArgumentParser(description="清洗天赋树 HTML")
    ap.add_argument("--talents", help="summary 页面 HTML 路径 (默认 data/raw/talents.html)")
    ap.add_argument("--out", help="输出 JSON 路径 (默认 data/clean/talents.json)")
    args = ap.parse_args()

    config.ensure_dirs()
    src = config.require(
        Path(args.talents) if args.talents else config.find_input("talents"),
        "从 WCL 保存 summary 页面 (?type=summary&source=<src>) 后放到这里",
    )

    result = parse(src.read_text("utf-8"))

    out = Path(args.out) if args.out else config.CLEAN_DIR / "talents.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), "utf-8")

    print("✅ {} → {} 选中 {} 个天赋".format(
        config.rel(src), config.rel(out), len(result["selectedTalents"])))
    for t in result["selectedTalents"][:8]:
        print("   [{:5s}] {:28s} spell={} ranks={}".format(
            t["treeType"], t["name"], t["spellId"], t["ranksChosen"]))


if __name__ == "__main__":
    main()
