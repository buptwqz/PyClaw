#!/bin/bash
# 在阿里云 ECS 上执行：bash update.sh
set -e

echo "[1/3] 拉取最新代码..."
git pull

echo "[2/3] 重新构建镜像..."
docker compose build --no-cache

echo "[3/3] 重启服务..."
docker compose up -d

echo "完成！查看日志：docker compose logs -f"
