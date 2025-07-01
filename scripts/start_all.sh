#!/bin/bash
# VRT系统一键启动脚本 (Linux/Mac)
# 使用tmux在后台启动所有服务

set -e

echo "🚀 VRT系统一键启动脚本"
echo "=============================="

# 检查tmux是否安装
if ! command -v tmux &> /dev/null; then
    echo "❌ tmux未安装，请先安装: sudo apt install tmux (Ubuntu) 或 brew install tmux (Mac)"
    exit 1
fi

# 检查uvicorn是否安装
if ! command -v uvicorn &> /dev/null; then
    echo "❌ uvicorn未安装，请先安装: pip install uvicorn"
    exit 1
fi

# 检查celery是否安装
if ! command -v celery &> /dev/null; then
    echo "❌ celery未安装，请先安装: pip install celery"
    exit 1
fi

echo "✅ 所有依赖检查通过"

# 创建tmux会话
SESSION_NAME="vrt_system"

# 删除已存在的会话
tmux kill-session -t $SESSION_NAME 2>/dev/null || true

# 创建新会话
tmux new-session -d -s $SESSION_NAME

# 窗口1: FastAPI (uvicorn)
tmux rename-window -t $SESSION_NAME:0 'FastAPI'
tmux send-keys -t $SESSION_NAME:0 'uvicorn main:app --reload --host 0.0.0.0 --port 8000' C-m

# 窗口2: Celery Worker
tmux new-window -t $SESSION_NAME -n 'Celery-Worker'
tmux send-keys -t $SESSION_NAME:1 'celery -A app.tasks.celery_app worker --loglevel=info' C-m

# 窗口3: Celery Beat
tmux new-window -t $SESSION_NAME -n 'Celery-Beat'
tmux send-keys -t $SESSION_NAME:2 'celery -A app.tasks.celery_app beat --loglevel=info' C-m

# 窗口4: Celery Flower (监控)
tmux new-window -t $SESSION_NAME -n 'Flower'
tmux send-keys -t $SESSION_NAME:3 'celery -A app.tasks.celery_app flower --port=5555' C-m

echo "🎉 所有服务已在tmux后台启动!"
echo ""
echo "📋 管理命令:"
echo "  查看所有服务: tmux attach-session -t $SESSION_NAME"
echo "  停止所有服务: tmux kill-session -t $SESSION_NAME"
echo "  查看特定窗口: tmux attach-session -t $SESSION_NAME:窗口号"
echo ""
echo "🌐 访问地址:"
echo "  - API文档: http://localhost:8000/docs"
echo "  - 健康检查: http://localhost:8000/api/admin/health"
echo "  - 任务监控: http://localhost:5555"
echo ""
echo "💡 提示: 使用 'tmux ls' 查看所有会话" 