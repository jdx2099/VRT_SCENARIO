# 原始评论更新模块文档

## 📋 模块概述

原始评论模块是用于查询和管理车型评论数据的核心模块。该模块允许前端通过渠道ID和车型标识来查询指定车型下的所有原始评论ID列表。

## 🏗️ 文件结构

```
app/
├── models/
│   ├── vehicle_update.py          # 车型更新相关模型
│   └── raw_comment_update.py      # 原始评论更新模型（独立文件）
├── schemas/
│   └── raw_comment_update.py      # 原始评论更新相关的数据校验模式
├── services/
│   └── raw_comment_update_service.py  # 原始评论更新业务逻辑服务
└── api/
    └── endpoints/
        └── raw_comment_update.py  # 原始评论更新API端点

# 测试文件
test_raw_comment.py                 # 模块功能测试脚本（建议重命名为test_raw_comment_update.py）
test_raw_comment_update_api.py      # API接口测试脚本
```

## 📊 数据模型

### RawComment 模型
- `raw_comment_id`: 原始评论ID (主键)
- `vehicle_channel_id_fk`: 关联的车型渠道详情ID (外键)
- `identifier_on_channel`: 评论在源渠道上的业务ID
- `comment_source_url`: 评论在源渠道的原始URL
- `comment_content`: 评论原始内容文本
- `posted_at_on_channel`: 评论在源渠道的发布时间
- `crawled_at`: 评论爬取入库时间

## 🔄 业务流程

1. **前端请求**: 传入 `channel_id` 和 `identifier_on_channel`
2. **查询车型**: 在 `vehicle_channel_details` 表中查找匹配的车型
3. **获取车型ID**: 提取 `vehicle_channel_id`
4. **查询评论**: 使用 `vehicle_channel_id` 在 `raw_comments` 表中查询所有评论ID
5. **返回结果**: 返回车型信息和评论ID列表

## 🚀 API接口

### 1. 查询原始评论ID
- **端点**: `POST /api/raw-comments/query`
- **功能**: 根据渠道ID和车型标识查询该车型下的所有原始评论ID
- **请求参数**:
  ```json
  {
    "channel_id": 1,
    "identifier_on_channel": "s3170"
  }
  ```
- **响应数据**:
  ```json
  {
    "vehicle_channel_info": {
      "vehicle_channel_id": 123,
      "channel_id": 1,
      "identifier_on_channel": "s3170",
      "name_on_channel": "奥迪A3",
      "url_on_channel": "https://www.autohome.com.cn/spec/s3170/",
      "temp_brand_name": "奥迪",
      "temp_series_name": "一汽奥迪",
      "temp_model_year": null
    },
    "raw_comment_ids": [1, 2, 3, 4, 5],
    "total_comments": 5
  }
  ```

### 2. 获取车型评论数量
- **端点**: `GET /api/raw-comments/vehicle/{channel_id}/{identifier}/count`
- **功能**: 统计指定车型的评论数量
- **响应数据**:
  ```json
  {
    "channel_id": 1,
    "identifier_on_channel": "s3170",
    "vehicle_channel_id": 123,
    "vehicle_name": "奥迪A3",
    "comment_count": 5
  }
  ```

## 🧪 测试方法

### 1. 直接测试模块功能
```bash
python test_raw_comment.py
```
这个脚本会：
- 检查车型数据
- 添加测试评论数据
- 测试查询功能
- 测试异常处理

### 2. 测试API接口
```bash
# 先启动服务器
python -m uvicorn main:app --reload

# 在另一个终端运行API测试
python test_raw_comment_update_api.py
```

## ⚠️ 注意事项

1. **数据依赖**: 需要先有车型数据（`vehicle_channel_details`表）才能查询评论
2. **外键约束**: `raw_comments` 表通过 `vehicle_channel_id_fk` 关联到 `vehicle_channel_details` 表
3. **唯一性约束**: 每个车型渠道下的评论标识必须唯一
4. **异常处理**: 当车型不存在时会抛出 `ValueError` 异常并返回404状态码

## 🔮 扩展方向

该模块为后续的评论爬虫和处理功能打下了基础，可以在此基础上扩展：

1. **评论爬虫**: 实际从各渠道爬取评论数据
2. **评论更新**: 增量更新评论数据
3. **评论分析**: 对评论内容进行情感分析和特征提取
4. **评论过滤**: 根据条件筛选和分页显示评论 