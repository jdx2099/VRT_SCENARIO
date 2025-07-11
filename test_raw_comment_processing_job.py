#!/usr/bin/env python3
"""
测试原始评论更新功能与processing_jobs表的集成
"""
import asyncio
import httpx
import time
from datetime import datetime

# 测试配置
BASE_URL = "http://localhost:8000"
TEST_CHANNEL_ID = 1
TEST_IDENTIFIER = "s7855"  # 使用一个存在的车型标识

async def test_raw_comment_processing_job():
    """测试原始评论更新的processing_job集成"""
    
    async with httpx.AsyncClient() as client:
        print("🚀 开始测试原始评论更新的processing_job集成")
        print(f"测试车型: channel_id={TEST_CHANNEL_ID}, identifier={TEST_IDENTIFIER}")
        print("-" * 60)
        
        # 1. 启动异步爬取任务
        print("1️⃣ 启动原始评论异步爬取任务...")
        crawl_request = {
            "channel_id": TEST_CHANNEL_ID,
            "identifier_on_channel": TEST_IDENTIFIER,
            "max_pages": 2  # 限制页数以加快测试
        }
        
        try:
            response = await client.post(
                f"{BASE_URL}/api/raw-comments/crawl",
                json=crawl_request
            )
            response.raise_for_status()
            task_info = response.json()
            
            print(f"✅ 任务启动成功:")
            print(f"   Task ID: {task_info['task_id']}")
            print(f"   Job ID: {task_info['job_id']}")
            print(f"   Status: {task_info['status']}")
            print(f"   Message: {task_info['message']}")
            
            task_id = task_info['task_id']
            job_id = task_info['job_id']
            
        except httpx.HTTPError as e:
            print(f"❌ 启动任务失败: {e}")
            return
        
        # 2. 立即查询processing_job状态
        print(f"\n2️⃣ 查询processing_job初始状态...")
        try:
            response = await client.get(f"{BASE_URL}/api/raw-comments/jobs/{job_id}")
            response.raise_for_status()
            job_status = response.json()
            
            print(f"✅ ProcessingJob状态:")
            print(f"   Job ID: {job_status['job_id']}")
            print(f"   Task Type: {job_status['task_type']}")
            print(f"   Status: {job_status['status']}")
            print(f"   Pipeline Version: {job_status['pipeline_version']}")
            print(f"   Created At: {job_status['created_at']}")
            print(f"   Task Params: {job_status['task_params']}")
            
        except httpx.HTTPError as e:
            print(f"❌ 查询processing_job失败: {e}")
        
        # 3. 监控任务执行过程
        print(f"\n3️⃣ 监控任务执行过程...")
        max_wait_time = 120  # 最大等待2分钟
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                # 查询Celery任务状态
                response = await client.get(f"{BASE_URL}/api/raw-comments/tasks/{task_id}/status")
                response.raise_for_status()
                celery_status = response.json()
                
                # 查询ProcessingJob状态
                response = await client.get(f"{BASE_URL}/api/raw-comments/jobs/{job_id}")
                response.raise_for_status()
                job_status = response.json()
                
                current_time = datetime.now().strftime("%H:%M:%S")
                print(f"[{current_time}] Celery: {celery_status['status']} | ProcessingJob: {job_status['status']}")
                
                # 显示详细信息
                if celery_status['status'] == 'PROGRESS':
                    progress = celery_status.get('progress', 0)
                    print(f"           进度: {progress}%")
                
                if job_status['status'] == 'running' and job_status.get('started_at'):
                    print(f"           开始时间: {job_status['started_at']}")
                
                # 任务完成
                if celery_status['status'] in ['SUCCESS', 'FAILURE']:
                    print(f"\n🎯 任务执行完成!")
                    
                    if celery_status['status'] == 'SUCCESS':
                        result = celery_status.get('result', {})
                        print(f"✅ 爬取结果:")
                        print(f"   车型名称: {result.get('result', {}).get('vehicle_name', 'N/A')}")
                        print(f"   爬取页数: {result.get('result', {}).get('total_pages_crawled', 0)}")
                        print(f"   发现评论: {result.get('result', {}).get('total_comments_found', 0)}")
                        print(f"   新增评论: {result.get('result', {}).get('new_comments_count', 0)}")
                        print(f"   耗时: {result.get('result', {}).get('crawl_duration', 0)}秒")
                        
                        # 最终ProcessingJob状态
                        print(f"\n📊 最终ProcessingJob状态:")
                        print(f"   Status: {job_status['status']}")
                        print(f"   Started At: {job_status.get('started_at', 'N/A')}")
                        print(f"   Completed At: {job_status.get('completed_at', 'N/A')}")
                        print(f"   Result Summary: {job_status.get('result_summary', 'N/A')}")
                        
                    else:
                        print(f"❌ 任务失败: {celery_status.get('error', 'Unknown error')}")
                        print(f"   ProcessingJob状态: {job_status['status']}")
                        print(f"   Result Summary: {job_status.get('result_summary', 'N/A')}")
                    
                    break
                
                await asyncio.sleep(5)  # 每5秒检查一次
                
            except httpx.HTTPError as e:
                print(f"❌ 状态查询失败: {e}")
                await asyncio.sleep(5)
                continue
        
        else:
            print(f"⏰ 等待超时 ({max_wait_time}秒)")
        
        # 4. 验证数据库状态
        print(f"\n4️⃣ 验证数据库状态...")
        try:
            # 查询车型评论数量
            response = await client.get(f"{BASE_URL}/api/raw-comments/vehicle/{TEST_CHANNEL_ID}/{TEST_IDENTIFIER}/count")
            response.raise_for_status()
            count_info = response.json()
            
            print(f"✅ 车型评论统计:")
            print(f"   车型名称: {count_info['vehicle_name']}")
            print(f"   评论总数: {count_info['comment_count']}")
            
        except httpx.HTTPError as e:
            print(f"❌ 统计查询失败: {e}")

if __name__ == "__main__":
    print("🧪 原始评论更新processing_job集成测试")
    print("=" * 60)
    asyncio.run(test_raw_comment_processing_job()) 