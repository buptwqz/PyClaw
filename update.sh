#!/bin/bash
# 在阿里云 ECS 上执行：bash update.sh
set -e

echo "[1/2] 拉取最新代码..."
git pull

echo "[2/2] 重启服务..."
docker compose restart

echo "完成！查看日志：docker compose logs -f"
