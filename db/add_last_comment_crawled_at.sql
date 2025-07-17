-- =================================================================
-- 数据库更新脚本：为vehicle_channel_details表添加last_comment_crawled_at字段
-- 执行日期: 2025-01-02
-- =================================================================

-- 为vehicle_channel_details表添加last_comment_crawled_at字段
ALTER TABLE `vehicle_channel_details` 
ADD COLUMN `last_comment_crawled_at` TIMESTAMP NULL 
COMMENT '上次成功爬取评论的时间，NULL表示从未爬取过' 
AFTER `temp_model_year`;

-- 验证字段添加成功
DESCRIBE `vehicle_channel_details`; 