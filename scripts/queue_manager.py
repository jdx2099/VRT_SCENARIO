#!/usr/bin/env python3
"""
Redis队列管理工具
支持查看、清除、统计队列中的任务
"""
import redis
import json
import argparse
import sys
import os
from datetime import datetime
from app.core.config import settings

class QueueManager:
    def __init__(self):
        self.broker = redis.from_url(settings.CELERY_BROKER_URL)
        self.backend = redis.from_url(settings.CELERY_RESULT_BACKEND)
        self.queue_name = 'celery'
    
    def show_status(self):
        """显示队列状态"""
        print("=" * 60)
        print("📊 Redis队列状态报告")
        print("=" * 60)
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Broker URL: {settings.CELERY_BROKER_URL}")
        print(f"Backend URL: {settings.CELERY_RESULT_BACKEND}")
        print()
        
        # 检查broker连接
        try:
            self.broker.ping()
            print("✅ Broker连接正常")
        except:
            print("❌ Broker连接失败")
            return
        
        # 检查backend连接
        try:
            self.backend.ping()
            print("✅ Backend连接正常")
        except:
            print("❌ Backend连接失败")
            return
        
        print()
        
        # 队列信息
        queue_length = self.broker.llen(self.queue_name)
        print(f"📋 主队列 '{self.queue_name}': {queue_length} 个待执行任务")
        
        # 检查其他队列
        other_queues = ['celery:1', 'celery:2', 'celery:3']
        for queue in other_queues:
            if self.broker.exists(queue):
                count = self.broker.llen(queue)
                print(f"📋 队列 '{queue}': {count} 个任务")
        
        # 任务结果统计
        result_keys = self.backend.keys('celery-task-meta-*')
        print(f"📊 任务结果: {len(result_keys)} 个")
        
        # 显示前几个任务详情
        if queue_length > 0:
            print(f"\n🔍 前5个任务详情:")
            tasks = self.broker.lrange(self.queue_name, 0, 4)
            for i, task in enumerate(tasks, 1):
                try:
                    task_data = json.loads(task)
                    headers = task_data.get('headers', {})
                    task_name = headers.get('task', 'Unknown')
                    task_id = headers.get('id', 'Unknown')
                    args = task_data.get('args', [])
                    kwargs = task_data.get('kwargs', {})
                    
                    print(f"  {i}. 任务ID: {task_id}")
                    print(f"     任务名: {task_name}")
                    print(f"     参数: {args}")
                    print(f"     关键字参数: {kwargs}")
                    print()
                except Exception as e:
                    print(f"  {i}. 无法解析的任务数据: {e}")
                    print()
    
    def clear_queue(self, confirm=False):
        """清除队列"""
        if not confirm:
            queue_length = self.broker.llen(self.queue_name)
            print(f"⚠️  警告: 即将清除队列 '{self.queue_name}' 中的 {queue_length} 个任务")
            response = input("确认清除? (y/N): ")
            if response.lower() != 'y':
                print("❌ 操作已取消")
                return
        
        try:
            # 清除主队列
            queue_length = self.broker.llen(self.queue_name)
            self.broker.delete(self.queue_name)
            print(f"✅ 已清除主队列 '{self.queue_name}' 中的 {queue_length} 个任务")
            
            # 清除其他队列
            other_queues = ['celery:1', 'celery:2', 'celery:3']
            for queue in other_queues:
                if self.broker.exists(queue):
                    count = self.broker.llen(queue)
                    self.broker.delete(queue)
                    print(f"✅ 已清除队列 '{queue}' 中的 {count} 个任务")
            
            # 清除任务结果
            result_keys = self.backend.keys('celery-task-meta-*')
            if result_keys:
                self.backend.delete(*result_keys)
                print(f"✅ 已清除 {len(result_keys)} 个任务结果")
            
            print("🎉 队列清理完成！")
            
        except Exception as e:
            print(f"❌ 清除队列时发生错误: {e}")
    
    def clear_results(self, confirm=False):
        """只清除任务结果"""
        if not confirm:
            result_keys = self.backend.keys('celery-task-meta-*')
            print(f"⚠️  警告: 即将清除 {len(result_keys)} 个任务结果")
            response = input("确认清除? (y/N): ")
            if response.lower() != 'y':
                print("❌ 操作已取消")
                return
        
        try:
            result_keys = self.backend.keys('celery-task-meta-*')
            if result_keys:
                self.backend.delete(*result_keys)
                print(f"✅ 已清除 {len(result_keys)} 个任务结果")
            else:
                print("ℹ️  没有任务结果需要清除")
        except Exception as e:
            print(f"❌ 清除任务结果时发生错误: {e}")
    
    def show_task_details(self, task_id):
        """显示特定任务的详细信息"""
        try:
            task_key = f'celery-task-meta-{task_id}'
            task_data = self.backend.get(task_key)
            
            if task_data:
                task_info = json.loads(task_data)
                print(f"📋 任务ID: {task_id}")
                print(f"状态: {task_info.get('status', 'Unknown')}")
                print(f"结果: {task_info.get('result', 'No result')}")
                print(f"完成时间: {task_info.get('date_done', 'Unknown')}")
            else:
                print(f"❌ 未找到任务ID为 {task_id} 的结果")
        except Exception as e:
            print(f"❌ 获取任务详情时发生错误: {e}")

def main():
    parser = argparse.ArgumentParser(description='Redis队列管理工具')
    parser.add_argument('action', choices=['status', 'clear', 'clear-results', 'task'], 
                       help='执行的操作')
    parser.add_argument('--task-id', help='任务ID（用于task操作）')
    parser.add_argument('--force', action='store_true', help='强制执行，不询问确认')
    
    args = parser.parse_args()
    
    manager = QueueManager()
    
    if args.action == 'status':
        manager.show_status()
    elif args.action == 'clear':
        manager.clear_queue(confirm=args.force)
    elif args.action == 'clear-results':
        manager.clear_results(confirm=args.force)
    elif args.action == 'task':
        if args.task_id:
            manager.show_task_details(args.task_id)
        else:
            print("❌ 请提供任务ID: --task-id <task_id>")

if __name__ == "__main__":
    main() 