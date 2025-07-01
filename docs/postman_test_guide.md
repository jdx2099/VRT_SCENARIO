# Postman 测试指南 - 原始评论更新接口

## 🎯 接口信息

- **接口名称**: 查询原始评论ID
- **请求方法**: POST
- **请求路径**: `/api/raw-comments/query`
- **完整URL**: `http://localhost:8000/api/raw-comments/query`

## 🔧 Postman 配置步骤

### 步骤 1: 创建新请求
1. 打开 Postman
2. 点击 "New" → "Request"
3. 输入请求名称：`查询原始评论ID`

### 步骤 2: 配置请求基本信息
1. **Method**: 选择 `POST`
2. **URL**: 输入 `http://localhost:8000/api/raw-comments/query`

### 步骤 3: 设置请求头
1. 点击 **Headers** 标签
2. 添加以下头部信息：
   ```
   Key: Content-Type
   Value: application/json
   ```

### 步骤 4: 配置请求体
1. 点击 **Body** 标签
2. 选择 **raw** 单选按钮
3. 在右侧下拉菜单选择 **JSON**
4. 在文本框中输入请求体（见下方测试用例）

## 📋 测试用例

### 测试用例 1: 查询有评论的车型 ✅
**请求体**:
```json
{
  "channel_id": 1,
  "identifier_on_channel": "s7855"
}
```

**预期响应** (Status: 200 OK):
```json
{
  "vehicle_channel_info": {
    "vehicle_channel_id": 1,
    "channel_id": 1,
    "identifier_on_channel": "s7855",
    "name_on_channel": "奥迪A5L",
    "url_on_channel": "https://www.autohome.com.cn/spec/s7855/",
    "temp_brand_name": "奥迪",
    "temp_series_name": "一汽奥迪",
    "temp_model_year": null
  },
  "raw_comment_ids": [1, 2, 3, 4, 5],
  "total_comments": 5
}
```

### 测试用例 2: 查询无评论的车型 ✅
**请求体**:
```json
{
  "channel_id": 1,
  "identifier_on_channel": "s3170"
}
```

**预期响应** (Status: 200 OK):
```json
{
  "vehicle_channel_info": {
    "vehicle_channel_id": 5,
    "channel_id": 1,
    "identifier_on_channel": "s3170",
    "name_on_channel": "奥迪A3",
    "url_on_channel": "https://www.autohome.com.cn/spec/s3170/",
    "temp_brand_name": "奥迪",
    "temp_series_name": "一汽奥迪",
    "temp_model_year": null
  },
  "raw_comment_ids": [],
  "total_comments": 0
}
```

### 测试用例 3: 无效参数测试 ❌
**请求体**:
```json
{
  "channel_id": 999,
  "identifier_on_channel": "nonexistent"
}
```

**预期响应** (Status: 404 Not Found):
```json
{
  "detail": "未找到匹配的车型: channel_id=999, identifier=nonexistent"
}
```

### 测试用例 4: 参数验证测试 ❌
**请求体**:
```json
{
  "channel_id": 0,
  "identifier_on_channel": ""
}
```

**预期响应** (Status: 422 Unprocessable Entity):
```json
{
  "detail": [
    {
      "type": "greater_than_equal",
      "loc": ["body", "channel_id"],
      "msg": "Input should be greater than or equal to 1"
    },
    {
      "type": "string_too_short",
      "loc": ["body", "identifier_on_channel"], 
      "msg": "String should have at least 1 character"
    }
  ]
}
```

## 🧪 测试验证点

### ✅ 成功场景验证
- [ ] 响应状态码为 200
- [ ] 返回的 `vehicle_channel_info` 包含完整车型信息
- [ ] `raw_comment_ids` 是整数数组
- [ ] `total_comments` 等于 `raw_comment_ids` 数组长度
- [ ] 响应时间 < 500ms

### ❌ 错误场景验证
- [ ] 无效车型返回 404 状态码
- [ ] 参数验证失败返回 422 状态码
- [ ] 错误信息描述准确

## 🔄 其他测试接口

### 评论数量统计接口
- **Method**: GET
- **URL**: `http://localhost:8000/api/raw-comments/vehicle/1/s7855/count`
- **预期响应**:
```json
{
  "channel_id": 1,
  "identifier_on_channel": "s7855",
  "vehicle_channel_id": 1,
  "vehicle_name": "奥迪A5L",
  "comment_count": 5
}
```

### 渠道列表接口（用于获取可用渠道）
- **Method**: GET  
- **URL**: `http://localhost:8000/api/vehicle-update/channels`

## ⚠️ 注意事项

1. **服务器启动**: 测试前确保 FastAPI 服务器正在运行
2. **数据准备**: 如果没有测试数据，先运行 `python test_raw_comment.py` 添加测试数据
3. **端口检查**: 确认服务器运行在 8000 端口
4. **网络连接**: 确保 localhost 连接正常

## 🚀 快速开始

1. 启动服务器: `python -m uvicorn main:app --reload`
2. 打开 Postman
3. 导入或手动创建上述请求
4. 按顺序执行测试用例
5. 验证响应结果

---

**🎉 完成测试后，您应该能看到原始评论更新接口的完整功能！** 