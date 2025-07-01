# Postman 快速参考

## 🎯 接口配置

**URL**: `http://localhost:8000/api/raw-comments/query`
**Method**: `POST`
**Headers**: `Content-Type: application/json`

## 📋 测试用例

### ✅ 成功用例
```json
{
  "channel_id": 1,
  "identifier_on_channel": "s7855"
}
```
**期望**: 200 状态码，返回 5 条评论

### ✅ 空数据用例
```json
{
  "channel_id": 1,
  "identifier_on_channel": "s3170"
}
```
**期望**: 200 状态码，返回 0 条评论

### ❌ 错误用例
```json
{
  "channel_id": 999,
  "identifier_on_channel": "nonexistent"
}
```
**期望**: 404 状态码

## 🔄 其他接口

**评论统计**: `GET http://localhost:8000/api/raw-comments/vehicle/1/s7855/count`
**渠道列表**: `GET http://localhost:8000/api/vehicle-update/channels` 