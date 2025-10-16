#!/bin/bash

# FlyEsports 强力重置脚本 - 解决顽固的缓存问题
echo "🔥 执行强力重置，清理所有缓存并重新构建..."

# 进入项目根目录
cd "$(dirname "$0")/.."

echo "1. 停止所有相关容器..."
docker-compose stop backend

echo "2. 清理Python缓存文件..."
find backend -name "*.pyc" -delete 2>/dev/null
find backend -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

echo "3. 删除容器（保留数据卷）..."
docker-compose rm -f backend

echo "4. 清理Docker构建缓存..."
docker builder prune -f

echo "5. 重新构建后端镜像（无缓存）..."
docker-compose build --no-cache backend

echo "6. 启动后端服务..."
docker-compose up -d backend

echo "7. 等待服务完全启动..."
sleep 10

echo "8. 检查服务状态..."
docker ps | grep backend
echo ""
docker-compose logs backend --tail 10

echo ""
echo "🎉 强力重置完成！"
echo "💡 这应该解决了所有代码同步问题"
echo "🔍 检查日志: docker-compose logs backend"