"""
简单的API测试脚本
避免PowerShell的curl编码问题
"""
import requests
import json

def test_api():
    base_url = "http://localhost:8000/api/vehicle-update"
    
    print("🔧 开始测试API接口...")
    
    # 测试1: 获取渠道列表
    print("\n1️⃣ 测试获取渠道列表")
    try:
        response = requests.get(f"{base_url}/channels")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("✅ 成功!")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"❌ 失败: {response.text}")
            return
    except Exception as e:
        print(f"❌ 错误: {e}")
        return
    
    # 测试2: 执行车型更新
    print("\n2️⃣ 测试车型数据更新")
    update_request = {
        "channel_id": 1,
        "force_update": True
    }
    
    print(f"请求参数: {json.dumps(update_request, ensure_ascii=False)}")
    print("⏳ 开始更新...")
    
    try:
        response = requests.post(
            f"{base_url}/update/direct",
            json=update_request,
            timeout=600  # 10分钟超时
        )
        
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print("✅ 更新成功!")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            # 简单统计
            total = result.get('total_crawled', 0)
            new_count = result.get('new_vehicles', 0)
            print(f"\n📊 统计: 总共{total}个车型，新增{new_count}个")
        else:
            print(f"❌ 更新失败: {response.text}")
    except Exception as e:
        print(f"❌ 错误: {e}")

if __name__ == "__main__":
    test_api() 