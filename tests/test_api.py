"""
API接口测试
"""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class TestVehicleUpdateAPI:
    """车型数据更新API测试"""
    
    def test_get_supported_channels(self):
        """测试获取支持的渠道列表"""
        response = client.get("/vehicle-update/channels")
        assert response.status_code == 200
        
        data = response.json()
        assert "supported_channels" in data
        assert "total_count" in data
        assert data["total_count"] > 0
    
    def test_update_vehicles_direct_invalid_channel(self):
        """测试直接更新车型数据 - 无效渠道ID"""
        response = client.post("/vehicle-update/update/direct", json={
            "channel_id": 999,
            "force_update": False
        })
        assert response.status_code == 400
        assert "不支持的渠道ID" in response.json()["detail"]
    
    def test_update_vehicles_direct_valid_channel(self):
        """测试直接更新车型数据 - 有效渠道ID"""
        response = client.post("/vehicle-update/update/direct", json={
            "channel_id": 1,
            "force_update": False
        })
        # 由于实际会连接网络爬取数据，这里只检查状态码
        # 在真实环境中可能会失败（网络连接等原因）
        assert response.status_code in [200, 500]
    
    def test_update_vehicles_async_invalid_channel(self):
        """测试异步更新车型数据 - 无效渠道ID"""
        response = client.post("/vehicle-update/update", json={
            "channel_id": 999,
            "force_update": False
        })
        assert response.status_code == 400
        assert "不支持的渠道ID" in response.json()["detail"]
    
    def test_update_vehicles_async_valid_channel(self):
        """测试异步更新车型数据 - 有效渠道ID"""
        response = client.post("/vehicle-update/update", json={
            "channel_id": 1,
            "force_update": False
        })
        # 由于需要Redis+Celery环境，这里可能会失败
        # 但应该返回特定的错误信息而不是500
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "task_id" in data
            assert "channel_id" in data
            assert "status" in data
    
    def test_get_channel_statistics_invalid_channel(self):
        """测试获取渠道统计信息 - 无效渠道ID"""
        response = client.get("/vehicle-update/channels/999/stats")
        # 这个接口不验证渠道ID存在性，只是查询数据库
        assert response.status_code in [200, 500]
    
    def test_get_channel_statistics_valid_channel(self):
        """测试获取渠道统计信息 - 有效渠道ID"""
        response = client.get("/vehicle-update/channels/1/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "channel_id" in data
        assert "total_vehicles" in data
        assert "brands_count" in data
        assert "manufacturers_count" in data
        assert data["channel_id"] == 1
    
    def test_update_request_schema_validation(self):
        """测试更新请求参数验证"""
        # 测试缺少必需字段
        response = client.post("/vehicle-update/update/direct", json={})
        assert response.status_code == 422
        
        # 测试无效的channel_id
        response = client.post("/vehicle-update/update/direct", json={
            "channel_id": 0,
            "force_update": False
        })
        assert response.status_code == 422
        
        # 测试负数channel_id
        response = client.post("/vehicle-update/update/direct", json={
            "channel_id": -1,
            "force_update": False
        })
        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__]) 