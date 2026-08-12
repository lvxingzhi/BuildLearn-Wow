# BuildLearn-Wow

从 [Warcraft Logs](https://cn.warcraftlogs.com/) 拉取某次 run 的**施法次数**与**天赋**，再从 [Wowhead](https://www.wowhead.com/) 抓取对应技能/天赋的中文名与描述，最终汇总成一份带图标和描述的 Excel 报告。

原本需要几个小时手动翻页对照的操作，现在跑三个脚本即可完成。

## 背景

学习某个职业构建时，需要：
1. 从 WCL 顶部玩家某次 run 的记录里拿到**施法次数列表**和**天赋**
2. 去 Wowhead 抓取每个技能/天赋的**中文描述**
3. 自己再做分析

## 数据流

```
施法次数HTML ──┐                        ┌──→ spells_clean.json ──┐
(casts 页面)   │  cleanse_spells.py     │                        │
              └─→ (清洗HTML为JSON) ──────┘                        │
                                                                 │
天赋树HTML ───┐                        ┌──→ talents_clean.json ─┤
(summary 页面)│  cleanse_talents.py    │                        │  build_excel.py
              └─→ (清洗HTML为JSON) ──────┘                        │  → 分析报告.xlsx
                                                                 │   (两个tab: 施法次数 / 天赋)
                        nether.wowhead.com                        │
              ┌──→ (抓取中文tooltip) ───→ wowhead_cache.json ───┘
```

## 三步流程

### 第 1 步：准备数据

从 WCL 手动保存两个页面的 HTML（命名固定）：

- `施法次数HTML` —— casts 页面，如：
  `https://cn.warcraftlogs.com/reports/<code>?fight=<id>&type=casts&source=<src>`
- `天赋树HTML` —— summary 页面，如：
  `https://cn.warcraftlogs.com/reports/<code>?fight=<id>&type=summary&source=<src>`

### 第 2 步：清洗 HTML → JSON

```bash
python3 cleanse_spells.py    # → spells_clean.json   (施法次数列表)
python3 cleanse_talents.py   # → talents_clean.json  (玩家选中的天赋)
```

### 第 3 步：抓取 Wowhead 描述

```bash
python3 fetch_wowhead.py     # → wowhead_cache.json  (中文名 + 描述 + 图标)
```

使用 Wowhead 现行的 tooltip JSON 接口：

```
https://nether.wowhead.com/tooltip/spell/{spell_id}?locale=zhCN
```

带本地缓存 `wowhead_cache.json`，重复运行只补抓缺失的 spellId。

### 第 4 步：生成 Excel

```bash
python3 build_excel.py       # → 分析报告.xlsx
```

## 产出：`分析报告.xlsx`

**Tab 1「施法次数」**（按次数降序）
- 排名 / 图标 / 技能名 / Spell ID / 施法次数 / 占比% / CPM / Uptime%
- 法力消耗 / 射程 / 施法时间 / 技能描述
- 底部合计行

**Tab 2「天赋」**（按 class → spec → hero 分组，三色区分）
- 顶部：职业 / 专精 / 英雄天赋 / 天赋码
- 分组 / 图标 / 天赋名 / Spell ID / 类型 / 选择等级
- 法力消耗 / 射程 / 施法时间 / 天赋描述

图标直接嵌入单元格（来自 WCL 的图标 CDN `assets.rpglogs.cn`）。

## 依赖

```bash
pip3 install openpyxl beautifulsoup4 requests lxml
```

Python ≥ 3.9（类型注解兼容 3.9）。

## 文件清单

| 文件 | 作用 | 输入 → 输出 |
|---|---|---|
| `cleanse_spells.py` | 清洗施法次数 HTML | `施法次数HTML` → `spells_clean.json` |
| `cleanse_talents.py` | 清洗天赋 HTML | `天赋树HTML` → `talents_clean.json` |
| `fetch_wowhead.py` | 抓 Wowhead 中文名+描述 | 两个 JSON 收集 spellId → `wowhead_cache.json` |
| `build_excel.py` | 生成 Excel 报告 | 三个 JSON → `分析报告.xlsx` |

## 换新的 run 怎么做

1. 替换 `施法次数HTML` 和 `天赋树HTML` 两个文件的内容
2. 依次跑：

```bash
python3 cleanse_spells.py
python3 cleanse_talents.py
python3 fetch_wowhead.py    # 已缓存的 spellId 会自动跳过
python3 build_excel.py
```

## 说明

- **不依赖 WCL 官方 API**：WCL 页面对匿名访问有人机验证墙（`/human-challenge`），但页面 HTML 本身结构完整、可直接解析，因此采用「手动保存 HTML → 脚本解析」的方式，规避反爬与 OAuth 注册成本。
- **天赋 JSON**：`天赋树HTML` 里包含两段关键 JSON —— `dehydratedBuild`（玩家选了哪些节点）和 `changeSet.allNodes`（所有节点的完整定义）。脚本用平衡花括号提取整段 JSON，再用 `selectedNodes` 去 `allNodes` 查详情，拼出「玩家实际点的天赋列表」。
- **天赋名翻译**：WCL 的 blueprint 只存英文 `name`，因此用 `spellId` 去 Wowhead 抓中文名替换。
