#!/usr/bin/env bash
# 一条命令双同步：git commit + push 到 GitHub，同时 rsync 镜像到本地服务器
# 用法: ./sync.sh ["提交说明"]
set -euo pipefail
cd "$(dirname "$0")"

SERVER_USER="${SSH_USER_NAME:-huajyang}"
SERVER_HOST="192.168.2.223"
SERVER_DIR="/opt/1panel/apps/openresty/openresty/www/sites/192.168.2.223/index/study/english-grammar"

MSG="${1:-sync: $(date '+%Y-%m-%d %H:%M:%S')}"

echo "==> [1/2] 同步到 GitHub"
git add -A
if git diff --cached --quiet; then
    echo "    无改动，跳过 commit/push"
else
    git commit -m "$MSG"
    git push origin main
fi

echo "==> [2/2] 同步到服务器 $SERVER_HOST:$SERVER_DIR"
rsync -avz --delete --8-bit-output \
    --exclude '.git/' \
    --exclude '__pycache__/' \
    --exclude '.DS_Store' \
    --exclude 'sync.sh' \
    --exclude '.venv/' \
    --exclude 'data/' \
    --exclude 'llm_config.json' \
    ./ "$SERVER_USER@$SERVER_HOST:$SERVER_DIR/"

echo "==> [3/2] 重启服务器上的 Streamlit 服务"
if ssh "$SERVER_USER@$SERVER_HOST" 'sudo -n systemctl restart english-grammar' 2>/dev/null; then
    echo "    服务已重启"
else
    echo "    警告：自动重启失败，请手动执行: sudo systemctl restart english-grammar"
fi

echo "==> 双同步完成"
