@echo off
chcp 65001 >nul
echo 🪟 Windows环境VRT系统启动脚本
echo ================================================

echo 🚀 启动Celery Worker (Windows兼容模式)...
start "Celery Worker" cmd /k "celery -A app.tasks.celery_app worker --loglevel=info --pool=solo --concurrency=1"

echo ⏰ 等待Worker启动...
timeout /t 3 /nobreak >nul

echo ⏰ 启动Celery Beat调度器...
start "Celery Beat" cmd /k "celery -A app.tasks.celery_app beat --loglevel=info --scheduler=celery.beat.PersistentScheduler"

echo 🌐 启动FastAPI服务...
start "FastAPI" cmd /k "uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

echo.
echo 🎉 所有服务已启动!
echo 💡 提示:
echo    - 访问 http://localhost:8000/docs 查看API文档
echo    - 运行 python test_scheduled_tasks.py 测试功能
echo    - 关闭对应窗口即可停止服务
echo.
pause 