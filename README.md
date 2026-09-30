## 从wcl网络请求中获取两个返回的HTML

casts.html(选择人物, 选择施法) -> 找网络请求中返回的符合格式的网页
https://cn.warcraftlogs.com/reports/ZCgDRk2BmKQVf3Pq?fight=2&type=casts&source=1

talents.html(选择人物, 选择摘要) -> 找网络请求中返回的符合格式的网页
https://cn.warcraftlogs.com/reports/ZCgDRk2BmKQVf3Pq?fight=2&type=summary&source=1

分别存为 `data/raw/casts.html` 和 `data/raw/talents.html`。

## 快速开始
```bash
pip install -r requirements.txt
make all
```

## 目录结构

| 目录 | 内容 | 进 git |
|---|---|---|
| `src/` | 四个脚本 + `config.py`（所有路径集中在这里） | ✅ |
| `data/raw/` | 手动放入的 WCL HTML | ❌ |
| `data/clean/` | 清洗产物 `spells.json` / `talents.json` | ❌ |
| `cache/` | Wowhead 数据 + 图标缓存 | ❌ |
| `runs/` | 按 run 归档的 Excel + 清洗副本 + `meta.json` | ❌ |

## 四步流程

| 步骤 | 命令 | 输入 → 输出 |
|---|---|---|
| 1 | `make spells` | `data/raw/casts.html` → `data/clean/spells.json` |
| 2 | `make talents` | `data/raw/talents.html` → `data/clean/talents.json` |
| 3 | `make wowhead` | 两个 JSON 的 spellId → `cache/wowhead_cache.json` |
| 4 | `make excel` | 三个 JSON → `runs/<slug>/分析报告.xlsx` |

`make all` 依次跑完四步。每步都能单独重跑，也支持自定义路径：
`--casts` / `--talents` / `--spells` / `--cache` / `--out` / `--name`（详见 `--help`）。
另有 `make install`、`make clean`、`make help`。

换新的 run：替换 `data/raw/` 里两个 HTML，再 `make all` 即可。旧报告不会被覆盖，各自留在 `runs/` 下。

## 报告内容

- **Tab「施法次数」**（按次数降序）：排名 / 图标 / 技能名 / Spell ID / 次数 / 占比% / CPM / Uptime% / 法力消耗 / 射程 / 施法时间 / 描述，底部合计行
- **Tab「天赋」**：顶部职业 + 专精 + 英雄天赋 + 天赋码，下面按 职业 / 专精 / 英雄 三色分组

图标从 WCL CDN（`assets.rpglogs.cn`）下载缓存后**直接嵌入单元格**。

## 注意事项

- **不走 WCL API**：匿名访问有人机验证墙（`/human-challenge`），但页面 HTML 结构完整可解析，因此采用「手动保存 HTML → 脚本解析」，规避反爬与 OAuth 注册成本。
- **天赋怎么解析的**：`talents.html` 里嵌了两段 JSON —— `dehydratedBuild`（玩家选了哪些节点）和 `changeSet.allNodes`（全部节点定义）。脚本用平衡花括号扫描器提取整段 JSON，再用 `selectedNodes` 去 `allNodes` 反查，拼出玩家实际点的天赋列表。
- **天赋名翻译**：WCL 的 blueprint 只存英文 `name`，所以用 spellId 去 Wowhead 抓中文名替换。
- **Wowhead 缓存每次全量覆盖**：技能描述会随游戏版本变动，旧数据不可信。
- **旧文件名兼容**：以前放在仓库根目录的 `施法次数HTML` / `天赋树HTML` 仍可识别（会打印提示），但建议改用 `data/raw/` 下的新文件名。
- Python ≥ 3.9。
