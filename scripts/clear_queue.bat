@echo off
echo 正在清除Redis队列中的待执行任务...
echo.

REM 方法1: 使用Redis CLI直接清除队列
echo 方法1: 使用Redis CLI清除队列
redis-cli -n 1 DEL celery
if %errorlevel% equ 0 (
    echo ✅ 已清除Redis数据库1中的celery队列
) else (
    echo ❌ 清除celery队列失败
)

REM 清除其他可能的队列
redis-cli -n 1 DEL celery:1
redis-cli -n 1 DEL celery:2
redis-cli -n 1 DEL celery:3

REM 清除结果后端
redis-cli -n 2 FLUSHDB
echo ✅ 已清除Redis数据库2中的任务结果

echo.
echo �� Redis队列清理完成！
pause 