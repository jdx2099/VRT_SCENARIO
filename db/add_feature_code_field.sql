-- =================================================================
-- SQL DDL Script: 为产品功能表添加业务编码字段
-- Version: V2.3
-- Dialect: MySQL
-- Date: 2025-01-02
-- =================================================================

-- 为已存在的 product_features 表添加 feature_code 字段
ALTER TABLE `product_features`
ADD COLUMN `feature_code` VARCHAR(255) NOT NULL
COMMENT '产品功能的业务编码，业务上唯一'
AFTER `product_feature_id`;

-- 为新添加的 feature_code 字段创建唯一索引
ALTER TABLE `product_features`
ADD UNIQUE INDEX `uk_feature_code` (`feature_code`);