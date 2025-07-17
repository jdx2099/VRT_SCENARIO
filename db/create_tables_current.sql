-- =================================================================
-- SQL DDL Scripts for Project Database
-- Version: V2.1 (13 Tables) - 与当前数据库状态适配
-- Dialect: MySQL
-- Date: 2025-01-02
-- =================================================================

-- Part 1: Core Tables with No or Self-Dependencies
-- -----------------------------------------------------------------

-- 1. 用户表
CREATE TABLE `users` (
    `user_id` INT AUTO_INCREMENT PRIMARY KEY,
    `username` VARCHAR(255) NOT NULL UNIQUE COMMENT '登录用户名',
    `password_hash` VARCHAR(255) NOT NULL COMMENT '哈希后的密码',
    `full_name` VARCHAR(255) NULL COMMENT '用户全名',
    `role` VARCHAR(50) NOT NULL DEFAULT 'user' COMMENT '用户角色，如：user, admin',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB COMMENT='系统用户信息表';

-- 2. 渠道表
CREATE TABLE `channels` (
    `channel_id` INT AUTO_INCREMENT PRIMARY KEY,
    `channel_name` VARCHAR(255) NOT NULL UNIQUE COMMENT '渠道名称，如：汽车之家',
    `channel_base_url` TEXT NULL COMMENT '渠道基础URL或配置信息',
    `channel_description` TEXT NULL COMMENT '渠道描述信息',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB COMMENT='评论来源渠道信息表';

-- 3. 标准车型表
CREATE TABLE `vehicles` (
    `vehicle_id` INT AUTO_INCREMENT PRIMARY KEY,
    `brand_name` VARCHAR(255) NOT NULL COMMENT '品牌名称',
    `manufacturer_name` VARCHAR(255) NULL COMMENT '制造商名称',
    `series_name` VARCHAR(255) NOT NULL COMMENT '车系名称',
    `model_year` VARCHAR(50) NULL COMMENT '年款',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB COMMENT='标准化的车型信息表';

-- 4. 产品功能表 (标准)
CREATE TABLE `product_features` (
    `product_feature_id` INT AUTO_INCREMENT PRIMARY KEY,
    `feature_name` VARCHAR(255) NOT NULL COMMENT '产品功能的名称，如：蓝牙、智能钥匙',
    `feature_description` TEXT NULL COMMENT '功能的详细描述（可用于生成嵌入）',
    `feature_embedding` TEXT NULL COMMENT '功能的文本嵌入向量，以JSON数组或特定格式的文本存储',
    `parent_id_fk` INT NULL COMMENT '指向父级功能ID，形成层级结构',
    `hierarchy_level` INT NOT NULL COMMENT '层级: 1, 2, 或 3',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`parent_id_fk`) REFERENCES `product_features`(`product_feature_id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='标准化的、面向用户的产品功能表（含嵌入向量）';

-- 5. 工程组织/公司表
CREATE TABLE `engineering_organizations` (
    `org_id` INT AUTO_INCREMENT PRIMARY KEY,
    `org_name` VARCHAR(255) NOT NULL UNIQUE COMMENT '组织/公司的名称',
    `org_description` TEXT NULL COMMENT '组织/公司的描述',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB COMMENT='工程开发组织/公司信息表';


-- Part 2: Tables with Dependencies
-- -----------------------------------------------------------------

-- 6. 任务批次表 (新增pipeline_version字段)
CREATE TABLE `processing_jobs` (
    `job_id` INT AUTO_INCREMENT PRIMARY KEY,
    `job_type` VARCHAR(100) NOT NULL COMMENT '任务类型，如：comment_processing, vehicle_consolidation',
    `status` VARCHAR(50) NOT NULL DEFAULT 'pending' COMMENT '任务状态: pending, running, completed, failed',
    `parameters` JSON NULL COMMENT '任务启动时的参数',
    `created_by_user_id_fk` INT NULL COMMENT '任务发起人',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `started_at` TIMESTAMP NULL,
    `completed_at` TIMESTAMP NULL,
    `result_summary` TEXT NULL COMMENT '任务结果摘要',
    `pipeline_version` VARCHAR(50) NOT NULL DEFAULT '1.0.0' COMMENT '处理管道版本号', -- <== 新增字段
    FOREIGN KEY (`created_by_user_id_fk`) REFERENCES `users`(`user_id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='异步任务批次管理表';

-- 7. 车型渠道详情表 (支持迭代)
CREATE TABLE `vehicle_channel_details` (
    `vehicle_channel_id` INT AUTO_INCREMENT PRIMARY KEY,
    `vehicle_id_fk` INT NULL COMMENT '关联到标准车型表，前期可为空',
    `channel_id_fk` INT NOT NULL COMMENT '关联到渠道表',
    `identifier_on_channel` VARCHAR(255) NOT NULL COMMENT '该车型在源渠道上的业务ID',
    `name_on_channel` VARCHAR(255) NOT NULL COMMENT '该车型在源渠道上的显示名称',
    `url_on_channel` VARCHAR(2048) NULL COMMENT '该车型在源渠道上的页面URL',
    `temp_brand_name` VARCHAR(255) NULL COMMENT '临时冗余字段：品牌名称',
    `temp_series_name` VARCHAR(255) NULL COMMENT '临时冗余字段：车系名称',
    `temp_model_year` VARCHAR(50) NULL COMMENT '临时冗余字段：年款',
    `last_comment_crawled_at` TIMESTAMP NULL COMMENT '上次成功爬取评论的时间，NULL表示从未爬取过',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `uk_channel_identifier` (`channel_id_fk`, `identifier_on_channel`),
    FOREIGN KEY (`vehicle_id_fk`) REFERENCES `vehicles`(`vehicle_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (`channel_id_fk`) REFERENCES `channels`(`channel_id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='车型在特定渠道的详情，支持数据迭代';

-- 8. 工程功能表
CREATE TABLE `engineering_features` (
    `engineering_feature_id` INT AUTO_INCREMENT PRIMARY KEY,
    `org_id_fk` INT NOT NULL COMMENT '所属组织ID',
    `feature_name` VARCHAR(255) NOT NULL COMMENT '工程功能的名称，如：蓝牙连接',
    `feature_description` TEXT NULL COMMENT '功能的详细描述',
    `parent_id_fk` INT NULL COMMENT '指向父级功能ID',
    `hierarchy_level` INT NOT NULL COMMENT '层级: 1, 2, 或 3',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`org_id_fk`) REFERENCES `engineering_organizations`(`org_id`) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (`parent_id_fk`) REFERENCES `engineering_features`(`engineering_feature_id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='各公司实际的工程开发功能模块表';

-- 9. 原始评论表 (新增processing_status字段)
CREATE TABLE `raw_comments` (
    `raw_comment_id` INT AUTO_INCREMENT PRIMARY KEY,
    `vehicle_channel_id_fk` INT NOT NULL COMMENT '关联的车型渠道详情ID',
    `identifier_on_channel` VARCHAR(255) NOT NULL COMMENT '该评论在源渠道上的业务ID',
    `comment_source_url` VARCHAR(2048) NULL COMMENT '评论在源渠道的原始URL',
    `comment_content` TEXT NOT NULL COMMENT '评论原始内容文本',
    `posted_at_on_channel` TIMESTAMP NULL COMMENT '评论在源渠道的发布时间',
    `crawled_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '评论爬取入库时间',
    `processing_status` ENUM('new', 'processing', 'completed', 'failed', 'skipped') NOT NULL DEFAULT 'new' COMMENT '处理状态', -- <== 新增字段
    UNIQUE KEY `uk_vehicle_channel_comment_identifier` (`vehicle_channel_id_fk`, `identifier_on_channel`),
    FOREIGN KEY (`vehicle_channel_id_fk`) REFERENCES `vehicle_channel_details`(`vehicle_channel_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='从各渠道收集的原始评论数据表';

-- 10. 功能映射表
CREATE TABLE `feature_mapping` (
    `product_feature_id_fk` INT NOT NULL COMMENT '关联到产品功能',
    `engineering_feature_id_fk` INT NOT NULL COMMENT '关联到工程功能',
    PRIMARY KEY (`product_feature_id_fk`, `engineering_feature_id_fk`),
    FOREIGN KEY (`product_feature_id_fk`) REFERENCES `product_features`(`product_feature_id`) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (`engineering_feature_id_fk`) REFERENCES `engineering_features`(`engineering_feature_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='产品功能与工程功能的映射关系表';

-- 11. 公共已处理评论表
CREATE TABLE `processed_comments` (
    `processed_comment_id` INT AUTO_INCREMENT PRIMARY KEY,
    `raw_comment_id_fk` INT NOT NULL COMMENT '关联的原始评论ID',
    `product_feature_id_fk` INT NULL COMMENT '检索匹配到的唯一功能模块',
    `feature_similarity_score` DECIMAL(18, 17) NULL COMMENT '功能模块与文本片段的相似度得分',
    `job_id_fk` INT NULL COMMENT '关联到创建本条记录的任务批次',
    `scene_actor` VARCHAR(255) NULL COMMENT '场景中的行动者/用户角色',
    `scene_time_context` VARCHAR(255) NULL COMMENT '场景发生的时间上下文',
    `scene_location_context` VARCHAR(255) NULL COMMENT '场景发生的地点上下文',
    `scene_activity_or_task` VARCHAR(255) NULL COMMENT '场景中发生的活动或用户执行的任务',
    `sentiment_label` VARCHAR(100) NULL COMMENT '情感分析标签',
    `sentiment_confidence` DECIMAL(5,4) NULL COMMENT '情感分析结果的置信度',
    `comment_analysis_summary` TEXT NULL COMMENT '对评论内容分析后给出的原因或摘要',
    `comment_chunk_text` TEXT NULL COMMENT '用于本次分析的评论片段原文',
    `comment_chunk_vector` TEXT NULL COMMENT '评论片段的向量表示(JSON格式存储)',
    `feature_search_details` JSON NULL COMMENT 'Top-K相似度检索结果详情',
    `processed_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '评论处理完成时间',
    FOREIGN KEY (`raw_comment_id_fk`) REFERENCES `raw_comments`(`raw_comment_id`) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (`product_feature_id_fk`) REFERENCES `product_features`(`product_feature_id`) ON DELETE SET NULL ON UPDATE CASCADE,
    FOREIGN KEY (`job_id_fk`) REFERENCES `processing_jobs`(`job_id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='标准格式的、公共的已处理评论数据';


-- Part 3: Tables for Deferred Features (Create Now, Use Later)
-- -----------------------------------------------------------------

-- 12. 用户自定义输出格式表
CREATE TABLE `user_defined_output_formats` (
    `format_id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id_fk` INT NOT NULL COMMENT '格式定义者',
    `format_name` VARCHAR(255) NOT NULL COMMENT '用户为该格式指定的名称',
    `format_definition` JSON NOT NULL COMMENT '格式的具体定义，如字段、提示词等',
    `format_description` TEXT NULL COMMENT '格式的描述信息',
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE COMMENT '格式是否启用',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `uk_user_format_name` (`user_id_fk`, `format_name`),
    FOREIGN KEY (`user_id_fk`) REFERENCES `users`(`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='(暂缓开发) 用户自定义输出格式定义表';

-- 13. 用户个性化处理数据表
CREATE TABLE `user_personalized_processed_data` (
    `personalized_data_id` INT AUTO_INCREMENT PRIMARY KEY,
    `raw_comment_id_fk` INT NOT NULL COMMENT '关联的原始评论ID',
    `owner_user_id_fk` INT NOT NULL COMMENT '数据所有者',
    `output_format_id_fk` INT NOT NULL COMMENT '使用的自定义输出格式ID',
    `product_feature_id_fk` INT NULL COMMENT '检索匹配到的唯一功能模块',
    `feature_similarity_score` DECIMAL(18, 17) NULL COMMENT '功能模块与文本片段的相似度得分',
    `job_id_fk` INT NULL COMMENT '关联到创建本条记录的任务批次',
    `dynamic_output_payload` JSON NOT NULL COMMENT '存储用户自定义字段及其解析值的JSON对象',
    `processed_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '数据处理完成时间',
    FOREIGN KEY (`raw_comment_id_fk`) REFERENCES `raw_comments`(`raw_comment_id`) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (`owner_user_id_fk`) REFERENCES `users`(`user_id`) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (`output_format_id_fk`) REFERENCES `user_defined_output_formats`(`format_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (`product_feature_id_fk`) REFERENCES `product_features`(`product_feature_id`) ON DELETE SET NULL ON UPDATE CASCADE,
    FOREIGN KEY (`job_id_fk`) REFERENCES `processing_jobs`(`job_id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='(暂缓开发) 用户私有的个性化处理数据表';


-- =================================================================
-- 索引优化 (可选)
-- =================================================================

-- 为新增字段添加索引以提高查询性能
-- CREATE INDEX idx_raw_comments_processing_status ON raw_comments(processing_status);
-- CREATE INDEX idx_processing_jobs_pipeline_version ON processing_jobs(pipeline_version);


-- =================================================================
-- 变更说明
-- =================================================================
-- V2.1 相对于 V2.0 的变更：
-- 1. processing_jobs表新增 pipeline_version 字段 (VARCHAR(50), 默认'1.0.0')
-- 2. raw_comments表新增 processing_status 字段 (ENUM, 默认'new') 
-- 3. 用于支持数据爬取和大模型处理的解耦管理
-- =================================================================

-- =================================================================
-- 变更说明
-- =================================================================
-- V2.2 相对于 V2.1 的变更：
-- 1. vehicle_channel_details表新增 last_comment_crawled_at 字段 (TIMESTAMP NULL)
-- 2. 用于记录每个车型最后一次成功爬取评论的时间，NULL表示从未爬取过
-- 3. 为后续定时爬取评论功能提供时间锚点
-- =================================================================