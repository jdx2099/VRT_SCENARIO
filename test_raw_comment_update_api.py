"""
原始评论更新API测试脚本
"""
import requests
import json
from typing import Dict, Any


def test_api(endpoint: str, method: str = "GET", data: Dict[str, Any] = None, params: Dict[str, Any] = None):
    """
    测试API接口
    """
    base_url = "http://localhost:8000/api"
    url = f"{base_url}{endpoint}"
    
    print(f"\n🔍 测试 {method} {endpoint}")
    if data:
        print(f"📤 请求数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
    if params:
        print(f"📋 请求参数: {params}")
    
    try:
        if method.upper() == "POST":
            response = requests.post(url, json=data, params=params)
        else:
            response = requests.get(url, params=params)
        
        print(f"📊 响应状态: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 响应成功:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return result
        else:
            print(f"❌ 响应失败: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败 - 请确保FastAPI服务器正在运行 (python -m uvicorn main:app --reload)")
        return None
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return None


def main():
    """主测试函数"""
    print("🚀 开始测试原始评论更新API...")
    
    # 1. 首先测试获取车型数据（从车型更新模块）
    print("\n" + "="*50)
    print("1️⃣  获取支持的渠道列表")
    channels = test_api("/vehicle-update/channels")
    
    if not channels or not channels.get("supported_channels"):
        print("❌ 需要先有渠道数据才能继续测试")
        return
    
    # 获取第一个渠道的ID
    first_channel_key = list(channels["supported_channels"].keys())[0]
    channel_id = channels["supported_channels"][first_channel_key]["channel_id"]
    
    # 2. 测试查询原始评论ID（需要先有车型数据）
    print("\n" + "="*50)
    print("2️⃣  查询指定车型的原始评论ID")
    
    # 使用有测试评论数据的车型
    test_data = {
        "channel_id": channel_id,
        "identifier_on_channel": "s7855"  # 这个车型有5条测试评论
    }
    
    result = test_api("/raw-comments/query", method="POST", data=test_data)
    
    if result:
        print(f"\n🎯 测试结果总结:")
        print(f"  - 车型渠道ID: {result['vehicle_channel_info']['vehicle_channel_id']}")
        print(f"  - 车型名称: {result['vehicle_channel_info']['name_on_channel']}")
        print(f"  - 评论总数: {result['total_comments']}")
        print(f"  - 评论ID列表: {result['raw_comment_ids']}")
    
    # 3. 测试评论数量统计接口
    print("\n" + "="*50)
    print("3️⃣  获取车型评论数量")
    
    test_api(f"/raw-comments/vehicle/{channel_id}/s7855/count")
    
    # 4. 测试无效参数
    print("\n" + "="*50)
    print("4️⃣  测试无效参数处理")
    
    invalid_data = {
        "channel_id": 999,
        "identifier_on_channel": "nonexistent"
    }
    
    test_api("/raw-comments/query", method="POST", data=invalid_data)
    
    print("\n🎉 API测试完成!")
    print("\n💡 提示:")
    print("  - 如果提示连接失败，请运行: python -m uvicorn main:app --reload")
    print("  - 如果提示找不到车型，请先运行车型更新接口添加数据")
    print("  - 如果需要添加测试评论数据，请运行: python test_raw_comment.py")


if __name__ == "__main__":
    main() 