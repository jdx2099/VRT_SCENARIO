#!/bin/bash

# 简化的数据库初始化脚本 - 适用于独立Docker容器和root用户
# 使用方法: chmod +x init_database_root_simple.sh && ./init_database_root_simple.sh

set -e

echo "🗄️ 快速初始化数据库（使用root用户）..."

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker未运行，请先启动Docker"
    exit 1
fi

# 获取MySQL容器名称
MYSQL_CONTAINER="mysql-container"

if [ -z "$MYSQL_CONTAINER" ]; then
    echo "❌ 未找到MySQL容器，请先启动MySQL容器"
    exit 1
fi

echo "✅ 找到MySQL容器: $MYSQL_CONTAINER"

# 设置MySQL root密码（请根据你的实际情况修改）
MYSQL_ROOT_PASSWORD="Pass1234"

echo "📊 创建数据库..."
docker exec -i $MYSQL_CONTAINER mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "
CREATE DATABASE IF NOT EXISTS vrt_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
"

echo "🔧 创建数据库表..."
docker exec -i $MYSQL_CONTAINER mysql -u root -p"$MYSQL_ROOT_PASSWORD" vrt_db < db/create_tables_current.sql

echo "✅ 数据库初始化完成！"

# 验证结果
echo "🔍 验证表结构..."
docker exec -i $MYSQL_CONTAINER mysql -u root -p"$MYSQL_ROOT_PASSWORD" vrt_db -e "SHOW TABLES;"

echo "🎉 数据库准备就绪！"
echo "📋 连接信息："
echo "   容器: $MYSQL_CONTAINER"
echo "   数据库: vrt_db"
echo "   用户: root" 