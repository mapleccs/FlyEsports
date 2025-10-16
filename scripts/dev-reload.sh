#!/bin/bash

# FlyEsports 开发环境重载脚本
echo "🔄 正在清理Python缓存并重启后端服务..."

# 进入项目根目录
cd "$(dirname "$0")/.."

# 清理Python缓存
echo "1. 清理Python缓存文件..."
find backend -name "*.pyc" -delete 2>/dev/null
find backend -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# 重启后端容器以确保代码生效
echo "2. 重启后端容器..."
docker-compose restart backend

# 等待容器启动
echo "3. 等待容器启动..."
sleep 5

# 检查健康状态
echo "4. 检查服务状态..."
docker ps | grep backend

echo ""
echo "✅ 重载完成！可以测试最新代码了。"
echo "💡 如果仍有问题，运行: docker-compose logs backend"