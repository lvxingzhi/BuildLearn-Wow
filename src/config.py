#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""config.py — 集中管理所有路径, 避免每个脚本各自硬编码相对文件名.

四个脚本都通过 `sys.path.insert(0, src目录)` 后 import config,
因此从任何工作目录执行 `python3 src/xxx.py` 都能正确定位仓库文件.
"""

import re
from datetime import datetime
from pathlib import Path

# ── 目录 ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent

RAW_DIR = ROOT / "data" / "raw"        # 手动放入的 WCL 页面 HTML
CLEAN_DIR = ROOT / "data" / "clean"    # 清洗产物 (每次覆盖)
CACHE_DIR = ROOT / "cache"             # Wowhead 数据 + 图标缓存
ICON_DIR = CACHE_DIR / "icons"
RUNS_DIR = ROOT / "runs"               # 按 run 归档的 Excel 报告

REPORT_XLSX = "分析报告.xlsx"

# ── 旧文件名兼容 ─────────────────────────────────────────────────────────
# 之前 HTML 直接放在仓库根目录、无扩展名。这里保留识别, 方便过渡。
LEGACY_NAMES = {
    "casts": ["施法次数HTML", "施法次数.html", "casts.html"],
    "talents": ["天赋树HTML", "天赋树.html", "talents.html"],
}


def ensure_dirs():
    """确保各目录存在 (图标目录按需创建)."""
    for d in (RAW_DIR, CLEAN_DIR, CACHE_DIR, RUNS_DIR):
        d.mkdir(parents=True, exist_ok=True)


def find_input(kind):
    """定位输入 HTML: 优先 data/raw/<kind>.html, 找不到再退回旧文件名."""
    new = RAW_DIR / "{}.html".format(kind)
    if new.exists():
        return new
    for name in LEGACY_NAMES[kind]:
        legacy = ROOT / name
        if legacy.exists():
            print("⚠️  仍在使用旧位置 {} , 建议改放到 {}".format(
                legacy.name, new.relative_to(ROOT)))
            return legacy
    return new


def rel(path):
    """相对仓库根目录显示; 路径不在仓库内时退回绝对路径."""
    try:
        return Path(path).resolve().relative_to(ROOT)
    except ValueError:
        return Path(path).resolve()


def require(path, hint=""):
    """校验输入文件存在, 不存在则打印提示并退出."""
    path = Path(path)
    if not path.exists():
        print("❌ 找不到输入文件: {}".format(path))
        if hint:
            print("   {}".format(hint))
        raise SystemExit(1)
    return path


# ── run 归档目录 ────────────────────────────────────────────────────────
def _slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")


def make_run_dir(player, override=None):
    """生成 run 归档目录: runs/<日期>-<职业>-<专精>, 重名自动加 -2/-3."""
    if override:
        slug = _slugify(override)
    else:
        parts = [datetime.now().strftime("%Y-%m-%d"),
                 _slugify(player.get("className")),
                 _slugify(player.get("specName"))]
        slug = "-".join(p for p in parts if p) or "run"

    target = RUNS_DIR / slug
    if target.exists():
        i = 2
        while (RUNS_DIR / "{}-{}".format(slug, i)).exists():
            i += 1
        target = RUNS_DIR / "{}-{}".format(slug, i)
    target.mkdir(parents=True, exist_ok=True)
    return target
