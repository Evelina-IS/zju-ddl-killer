#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"

if [ ! -d "$DIR/venv" ]; then
    echo "🔧 首次运行，创建虚拟环境..."
    python3 -m venv "$DIR/venv"
fi
source "$DIR/venv/bin/activate"
pip install -q requests rich python-dateutil 2>/dev/null

# ── 请修改为你的 Cookie 和账号 ──
# PTA_COOKIES 获取方式：浏览器登录 pintia.cn → F12 → Application → Cookies → 复制
export PTA_COOKIES="PTASession=xxx; JSESSIONID=xxx; _bl_uid=xxx"

# 学在浙大账号（可选，不需要可留空）
export ZJU_USER="xxxxxxxxxxxx"      # 学号
export ZJU_PASS="xxxxxxxxxxxx"      # 密码

PYTHONPATH="$DIR:$PYTHONPATH" \
python3 -m zju_ddl_scraper.cli "$@"
