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
rsync -avz --delete \
    --exclude '.git/' \
    --exclude '__pycache__/' \
    --exclude '.DS_Store' \
    --exclude 'sync.sh' \
    ./ "$SERVER_USER@$SERVER_HOST:$SERVER_DIR/"

echo "==> 双同步完成"
