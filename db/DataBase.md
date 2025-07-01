数据库全景解析：从表到字段
我们将延续之前的逻辑分组，逐一解析每张表及其所有字段。

A. 基础实体组 (The "Nouns" of the System)
这些表定义了我们业务中最核心、最基本的实体。

1. channels (渠道表)
目的: 定义了所有信息来源的渠道，是数据的“出生地”名录。
channel_id (INT, PK): 系统唯一标识符。这是渠道在数据库中的内部“身份证号”，用于被其他表精确引用。
channel_name (VARCHAR, UNIQUE): 人类可读的名称。这是渠道的公开名称，如“汽车之家”，具有唯一性以防重复。
channel_base_url (VARCHAR): 参考信息。渠道的官网地址，方便运营人员或程序进行跳转和参考。
channel_description (TEXT): 补充描述。用于记录关于此渠道的更多备注信息。
2. vehicles (标准车型表)
目的: 定义了所有车型的“黄金标准”记录，是内部统一、干净的车型主数据。
vehicle_id (INT, PK): 系统唯一标识符。车型的内部“身份证号”。
brand_name, manufacturer_name, series_name, model_year (VARCHAR): 标准化的核心属性。这些字段共同构成了对一款车型的精确、无歧义的描述，是所有分析和报告的基准。
3. vehicle_channel_details (车型渠道详情表)
目的: 系统中最关键的“关联枢纽”之一，它精确描述了“在哪个渠道上出现的哪个具体车型”，并为迭代开发设计了冗余。
vehicle_channel_id (INT, PK): 关联关系的唯一标识符。
vehicle_id_fk (INT, FK, NULLABLE): 指向标准车型的“指针”。这是实现数据治理的关键。在初期，当标准车型数据不完善时，此字段可以为空。当后期数据被清洗、匹配上标准车型后，此字段会被填充，代表该条记录已被“归一化”。
channel_id_fk (INT, FK): 指向渠道的“指针”。明确了这条记录属于哪个渠道。
identifier_on_channel, name_on_channel, url_on_channel: 渠道专属属性。记录了该车型在特定渠道上的“本地化”信息（如它在该网站上的ID、名称和URL），这是保证数据来源可追溯性的重要信息。
temp_brand_name, temp_series_name, temp_model_year (VARCHAR): 临时冗余字段。这是为“先运行，后治理”的迭代策略而设计的。在vehicle_id_fk为空时，系统依赖这些临时字段来大致了解车型信息。
B. 核心数据流组 (The "Data Flow")
这些表代表了数据从原始输入到智能处理后的成品的完整流程。

4. raw_comments (原始评论表)
目的: 系统的“原材料”，完整保存从源头获取的、未经修改的评论文本。
raw_comment_id (INT, PK): 原始评论的唯一标识符。
vehicle_channel_id_fk (INT, FK): 上下文的关键链接。通过此字段，每一条原始评论都精确地知道自己的“出身”：关于“哪个渠道的哪个车型”的评论。
identifier_on_channel (VARCHAR): 评论的源ID。这是该评论在原始网站上的ID，用于数据同步、去重和反查。
comment_content (TEXT): 核心内容。未经任何处理的用户评论全文，是所有后续分析的起点。
posted_at_on_channel (TIMESTAMP): 源发布时间。记录了评论在原始渠道的发布时间，是进行时序分析的基础。
crawled_at (TIMESTAMP): 系统获取时间。记录了系统将该条评论入库的时间。
5. product_features (产品功能表)
目的: 系统的“分析大纲”和“知识库”，定义了所有分析的维度和主题。
product_feature_id (INT, PK): 产品功能的唯一标识符。是所有分析结果进行关联和聚合的核心“标签”。
feature_name, feature_description: 人类可读的定义。描述了这个功能是什么。feature_description 尤其重要，因为它常被用作生成嵌入向量的源文本。
feature_embedding (TEXT/JSON): 功能的“数学指纹”。这是该功能名称和描述经过文本嵌入模型计算后得到的向量。它是实现“相似度检索”步骤的核心数据，使得系统能“理解”文本和功能在语义上的接近程度。
parent_id_fk, hierarchy_level: 层级结构定义。这两个字段让功能可以形成树状结构（如：座舱 -> 屏幕 -> 分辨率），使得分析结果可以按不同粒度进行上卷和下钻。
6. processed_comments (公共已处理评论表)
目的: 系统的“标准化成品库”，存放经过智能流水线处理后的结构化数据洞察。
processed_comment_id (INT, PK): 已处理结果的唯一标识符。
raw_comment_id_fk (INT, FK): 来源追溯链接。指向原始评论，保证每一条分析结果都能找到其原文。
product_feature_id_fk (INT, FK): 主题标签。指明了这条分析结果是关于哪个产品功能的，这是“相似度检索”步骤的直接产出。
feature_similarity_score (DECIMAL): 匹配置信度。记录了评论文本与匹配到的产品功能之间的相似度得分。这是一个关键的质量控制指标，分数越高代表匹配越可靠。
job_id_fk (INT, FK): 生产批次号。指向processing_jobs表，说明这条结果是由哪个“生产工单”创建的，用于追踪和审计。
scene_*, sentiment_*, comment_analysis_summary: 核心洞察载荷。这些是由大型语言模型(LLM)最终提取出的结构化信息，是本系统最有价值的产出。
C. 任务管理组 (The "Factory Management")
7. users (用户表)
目的: 系统的操作员和管理员的身份管理。
user_id, username, password_hash, full_name: 身份认证信息。用于登录和识别用户。
role (VARCHAR): 权限控制字段。用于区分不同用户组的权限，是实现访问控制的基础。
8. processing_jobs (任务批次表)
目的: 对所有自动化数据处理任务进行监控、管理和记录的“中央控制室”。
job_id (INT, PK): 任务的唯一标识符。
job_type (VARCHAR): 任务分类。说明此任务是做什么的（例如，'comment_processing'）。
status (VARCHAR): 任务生命周期状态。追踪任务是“待处理”、“运行中”、“已完成”还是“失败”，是监控系统健康度的核心。
parameters (JSON): 任务输入参数。以JSON格式记录了启动此任务时的所有参数（如处理哪个渠道），保证了任务的可复现性。
created_by_user_id_fk: 任务发起人。记录了是哪个用户触发了此任务（对于手动任务而言）。
created_at, started_at, completed_at: 时间戳审计。完整记录了任务的生命周期时间点。
result_summary (TEXT): 任务结果快照。用于快速了解任务的执行结果，如“成功处理1000条，失败20条”。
D. 远期扩展组 (The "Future Blueprint")
工程映射模块 (4张表)
engineering_organizations: org_id 和 org_name 定义了不同的工程实体。
engineering_features: engineering_feature_id, org_id_fk, feature_name, parent_id_fk 等字段，为每个公司内部建立了一套平行的、私有的功能层级体系。
feature_mapping: product_feature_id_fk 和 engineering_feature_id_fk 这两个字段共同作为主键，构建了一座“桥梁”，将公共的、面向市场的产品功能与私有的、面向内部的工程功能连接起来。
用户个性化模块 (2张表)
user_defined_output_formats: 核心是 format_definition (JSON) 字段，它允许用户以灵活的JSON格式定义自己想要的、独特的分析模板。
user_personalized_processed_data: 核心是 dynamic_output_payload (JSON) 字段，它用于存储根据上述用户自定义模板解析出的、结构不固定的结果。这两个JSON字段的设计，完美地解决了“在结构化数据库中存储非结构化、动态定义的数据”这一挑战。