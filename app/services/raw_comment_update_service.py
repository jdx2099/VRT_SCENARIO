"""
原始评论更新服务
处理原始评论查询和更新相关业务逻辑
"""
from typing import List, Optional, Set
from sqlalchemy.orm import Session
from sqlalchemy import select, text
import httpx
import json
import time
import random
import asyncio
from datetime import datetime
from tqdm import tqdm

from app.core.database import AsyncSessionLocal
from app.core.logging import app_logger
from app.models.vehicle_update import VehicleChannelDetail, Channel
from app.models.raw_comment_update import RawComment, ProcessingStatus
from app.schemas.raw_comment_update import (
    RawCommentQueryRequest, RawCommentQueryResult, 
    VehicleChannelInfo, RawCommentCrawlRequest, RawCommentCrawlResult,
    NewCommentInfo
)


class RawCommentUpdateService:
    """
    原始评论更新服务类
    负责处理原始评论相关的业务逻辑
    """
    
    def __init__(self):
        self.logger = app_logger

    async def crawl_new_comments_async(self, crawl_request: RawCommentCrawlRequest) -> "RawCommentCrawlTaskSchema":
        """
        启动原始评论异步爬取任务
        
        Args:
            crawl_request: 爬取请求参数
            
        Returns:
            异步任务信息
        """
        try:
            # 验证车型存在性
            vehicle_detail = await self.get_vehicle_by_channel_and_identifier(
                crawl_request.channel_id, crawl_request.identifier_on_channel
            )
            
            if not vehicle_detail:
                raise ValueError(f"未找到匹配的车型: channel_id={crawl_request.channel_id}, identifier={crawl_request.identifier_on_channel}")
            
            # 导入Celery任务（避免循环导入）
            from app.tasks.crawler_tasks import crawl_raw_comments_async
            from app.schemas.raw_comment_update import RawCommentCrawlTaskSchema
            from datetime import datetime
            
            # 启动异步任务
            task = crawl_raw_comments_async.delay(
                channel_id=crawl_request.channel_id,
                identifier_on_channel=crawl_request.identifier_on_channel,
                max_pages=crawl_request.max_pages
            )
            
            # 创建任务记录
            task_schema = RawCommentCrawlTaskSchema(
                task_id=task.id,
                channel_id=crawl_request.channel_id,
                identifier_on_channel=crawl_request.identifier_on_channel,
                status="pending",
                message=f"已启动 {vehicle_detail.name_on_channel} 原始评论爬取任务",
                created_at=datetime.utcnow()
            )
            
            self.logger.info(f"🚀 原始评论爬取任务已启动: {task.id}")
            
            return task_schema
            
        except Exception as e:
            self.logger.error(f"❌ 启动原始评论爬取任务失败: {e}")
            raise

    async def get_vehicle_raw_comment_ids(self, query_request: RawCommentQueryRequest) -> RawCommentQueryResult:
        """
        根据渠道ID和车型标识获取该车型下的所有原始评论ID
        
        Args:
            query_request: 查询请求参数
            
        Returns:
            查询结果，包含车型信息和评论ID列表
            
        Raises:
            ValueError: 当车型不存在时
        """
        try:
            async with AsyncSessionLocal() as db:
                # 第一步：根据channel_id和identifier_on_channel查询车型渠道详情
                self.logger.info(f"🔍 查询车型: channel_id={query_request.channel_id}, identifier={query_request.identifier_on_channel}")
                
                vehicle_result = await db.execute(
                    select(VehicleChannelDetail).where(
                        VehicleChannelDetail.channel_id_fk == query_request.channel_id,
                        VehicleChannelDetail.identifier_on_channel == query_request.identifier_on_channel
                    )
                )
                vehicle_detail = vehicle_result.scalar_one_or_none()
                
                if not vehicle_detail:
                    raise ValueError(f"未找到匹配的车型: channel_id={query_request.channel_id}, identifier={query_request.identifier_on_channel}")
                
                self.logger.info(f"✅ 找到车型: vehicle_channel_id={vehicle_detail.vehicle_channel_id}, name={vehicle_detail.name_on_channel}")
                
                # 第二步：使用vehicle_channel_id查询所有相关的原始评论ID
                comment_result = await db.execute(
                    select(RawComment.raw_comment_id).where(
                        RawComment.vehicle_channel_id_fk == vehicle_detail.vehicle_channel_id
                    ).order_by(RawComment.raw_comment_id)
                )
                raw_comment_ids = comment_result.scalars().all()
                
                self.logger.info(f"📊 找到 {len(raw_comment_ids)} 条原始评论")
                
                # 构建车型渠道信息
                vehicle_channel_info = VehicleChannelInfo(
                    vehicle_channel_id=vehicle_detail.vehicle_channel_id,
                    channel_id=vehicle_detail.channel_id_fk,
                    identifier_on_channel=vehicle_detail.identifier_on_channel,
                    name_on_channel=vehicle_detail.name_on_channel,
                    url_on_channel=vehicle_detail.url_on_channel,
                    temp_brand_name=vehicle_detail.temp_brand_name,
                    temp_series_name=vehicle_detail.temp_series_name,
                    temp_model_year=vehicle_detail.temp_model_year
                )
                
                # 构建查询结果
                result = RawCommentQueryResult(
                    vehicle_channel_info=vehicle_channel_info,
                    raw_comment_ids=list(raw_comment_ids),
                    total_comments=len(raw_comment_ids)
                )
                
                return result
                
        except Exception as e:
            self.logger.error(f"❌ 查询车型原始评论ID失败: {e}")
            raise
    
    async def get_vehicle_by_channel_and_identifier(self, channel_id: int, identifier_on_channel: str) -> Optional[VehicleChannelDetail]:
        """
        根据渠道ID和车型标识获取车型详情
        
        Args:
            channel_id: 渠道ID
            identifier_on_channel: 车型在渠道上的标识
            
        Returns:
            车型渠道详情对象，如果不存在则返回None
        """
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(VehicleChannelDetail).where(
                        VehicleChannelDetail.channel_id_fk == channel_id,
                        VehicleChannelDetail.identifier_on_channel == identifier_on_channel
                    )
                )
                return result.scalar_one_or_none()
        except Exception as e:
            self.logger.error(f"❌ 查询车型详情失败: {e}")
            raise
    
    async def count_raw_comments_by_vehicle_channel_id(self, vehicle_channel_id: int) -> int:
        """
        统计指定车型渠道详情ID下的原始评论数量
        
        Args:
            vehicle_channel_id: 车型渠道详情ID
            
        Returns:
            评论数量
        """
        try:
            async with AsyncSessionLocal() as db:
                from sqlalchemy import func
                result = await db.execute(
                    select(func.count(RawComment.raw_comment_id)).where(
                        RawComment.vehicle_channel_id_fk == vehicle_channel_id
                    )
                )
                return result.scalar()
        except Exception as e:
            self.logger.error(f"❌ 统计原始评论数量失败: {e}")
            raise
    
    async def crawl_new_comments(self, crawl_request: RawCommentCrawlRequest) -> RawCommentCrawlResult:
        """
        爬取新的原始评论
        
        Args:
            crawl_request: 爬取请求参数
            
        Returns:
            爬取结果，包含新增评论信息
        """
        start_time = time.time()
        
        try:
            async with AsyncSessionLocal() as db:
                # 第一步：获取车型信息
                self.logger.info(f"🔍 开始爬取评论: channel_id={crawl_request.channel_id}, identifier={crawl_request.identifier_on_channel}")
                
                vehicle_detail = await self._get_vehicle_detail(db, crawl_request.channel_id, crawl_request.identifier_on_channel)
                if not vehicle_detail:
                    raise ValueError(f"未找到匹配的车型: channel_id={crawl_request.channel_id}, identifier={crawl_request.identifier_on_channel}")
                
                # 第二步：获取渠道配置
                channel_config = await self._get_channel_config(db, crawl_request.channel_id)
                if not channel_config:
                    raise ValueError(f"未找到渠道配置: channel_id={crawl_request.channel_id}")
                
                # 第三步：获取已有评论ID列表
                existing_comment_ids = await self._get_existing_comment_identifiers(db, vehicle_detail.vehicle_channel_id)
                self.logger.info(f"📊 数据库中已有 {len(existing_comment_ids)} 条评论")
                
                # 第四步：获取评论总页数
                total_pages = await self._count_pages(channel_config, crawl_request.identifier_on_channel)
                self.logger.info(f"📄 共发现 {total_pages} 页评论")
                
                # 限制最大爬取页数
                max_pages = min(total_pages, crawl_request.max_pages or total_pages)
                
                # 第五步：爬取新评论
                new_comments = await self._collect_new_comments(
                    channel_config, 
                    crawl_request.identifier_on_channel,
                    max_pages,
                    existing_comment_ids,
                    vehicle_detail.vehicle_channel_id
                )
                
                # 第六步：爬取评论详细内容
                if new_comments:
                    self.logger.info(f"📝 开始爬取 {len(new_comments)} 条评论的详细内容...")
                    await self._scrape_comments_contents(new_comments, channel_config)
                
                # 第七步：保存新评论到数据库
                saved_count = await self._save_new_comments(db, new_comments, vehicle_detail.vehicle_channel_id)
                
                # 构建车型渠道信息
                vehicle_channel_info = VehicleChannelInfo(
                    vehicle_channel_id=vehicle_detail.vehicle_channel_id,
                    channel_id=vehicle_detail.channel_id_fk,
                    identifier_on_channel=vehicle_detail.identifier_on_channel,
                    name_on_channel=vehicle_detail.name_on_channel,
                    url_on_channel=vehicle_detail.url_on_channel,
                    temp_brand_name=vehicle_detail.temp_brand_name,
                    temp_series_name=vehicle_detail.temp_series_name,
                    temp_model_year=vehicle_detail.temp_model_year
                )
                
                crawl_duration = time.time() - start_time
                
                result = RawCommentCrawlResult(
                    vehicle_channel_info=vehicle_channel_info,
                    total_pages_crawled=max_pages,
                    total_comments_found=len(new_comments),
                    new_comments_count=saved_count,
                    new_comments=[
                        NewCommentInfo(
                            identifier_on_channel=comment["identifier_on_channel"],
                            comment_content=comment["comment_content"],
                            posted_at_on_channel=comment["posted_at_on_channel"],
                            comment_source_url=comment.get("comment_source_url")
                        ) for comment in new_comments[:10]  # 只返回前10条用于展示
                    ],
                    crawl_duration=round(crawl_duration, 2)
                )
                
                self.logger.info(f"✅ 爬取完成: 发现 {len(new_comments)} 条新评论, 保存 {saved_count} 条, 耗时 {crawl_duration:.2f}秒")
                
                return result
                
        except Exception as e:
            self.logger.error(f"❌ 爬取评论失败: {e}")
            raise
    
    async def _get_vehicle_detail(self, db, channel_id: int, identifier_on_channel: str) -> Optional[VehicleChannelDetail]:
        """获取车型详情"""
        result = await db.execute(
            select(VehicleChannelDetail).where(
                VehicleChannelDetail.channel_id_fk == channel_id,
                VehicleChannelDetail.identifier_on_channel == identifier_on_channel
            )
        )
        return result.scalar_one_or_none()
    
    async def _get_channel_config(self, db, channel_id: int) -> Optional[dict]:
        """获取渠道配置"""
        result = await db.execute(
            select(Channel).where(Channel.channel_id == channel_id)
        )
        channel = result.scalar_one_or_none()
        if not channel or not channel.channel_base_url:
            return None
        
        try:
            # 解析channel_base_url中的JSON配置
            config = json.loads(channel.channel_base_url)
            return config
        except json.JSONDecodeError:
            self.logger.error(f"❌ 渠道配置JSON解析失败: channel_id={channel_id}")
            return None
    
    async def _get_existing_comment_identifiers(self, db, vehicle_channel_id: int) -> Set[str]:
        """获取已有评论标识符集合"""
        result = await db.execute(
            select(RawComment.identifier_on_channel).where(
                RawComment.vehicle_channel_id_fk == vehicle_channel_id
            )
        )
        identifiers = result.scalars().all()
        return set(identifiers)
    
    async def _count_pages(self, channel_config: dict, identifier: str) -> int:
        """计算评论总页数"""
        try:
            # 从渠道配置中获取URL模板
            koubei_config = channel_config.get("koubei_series", {})
            url_template = koubei_config.get("url", "")
            
            if not url_template:
                raise ValueError("渠道配置中未找到koubei_series.url")
            
            # 构建第一页的URL来获取总页数
            # URL模板格式: {series_id} 替换为第一个{}，{page} 替换为第二个{}
            first_page_url = url_template.format(identifier, 1)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(first_page_url)
                response.raise_for_status()
                
                data = response.json()
                page_count = data.get("result", {}).get("pagecount", 1)
                
                self.logger.info(f"📄 从API获取到总页数: {page_count}")
                return int(page_count)
                
        except Exception as e:
            self.logger.error(f"❌ 获取页数失败: {e}")
            # 如果获取失败，返回默认值1
            return 1
    
    async def _collect_new_comments(
        self, 
        channel_config: dict, 
        identifier: str, 
        max_pages: int,
        existing_identifiers: Set[str],
        vehicle_channel_id: int
    ) -> List[dict]:
        """收集新评论"""
        koubei_config = channel_config.get("koubei_series", {})
        url_template = koubei_config.get("url", "")
        
        if not url_template:
            raise ValueError("渠道配置中未找到koubei_series.url")
        
        new_comments = []
        seen_identifiers = set()
        
        self.logger.info(f"🕷️ 开始爬取 {max_pages} 页评论...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for page in tqdm(range(1, max_pages + 1), desc="爬取评论页面"):
                try:
                    # 构建当前页面URL
                    # URL模板格式: {series_id} 替换为第一个{}，{page} 替换为第二个{}
                    page_url = url_template.format(identifier, page)
                    
                    response = await client.get(page_url)
                    response.raise_for_status()
                    
                    data = response.json()
                    comment_list = data.get("result", {}).get("list", [])
                    
                    for item in comment_list:
                        # 获取评论ID（对应老代码中的Koubeiid）
                        koubei_id = str(item.get("Koubeiid", ""))
                        if not koubei_id:
                            continue
                        
                        # 检查是否已存在或重复
                        if koubei_id in existing_identifiers or koubei_id in seen_identifiers:
                            continue
                        
                        seen_identifiers.add(koubei_id)
                        
                        # 解析评论基本数据（内容将在后续步骤中爬取）
                        comment_data = {
                            "identifier_on_channel": koubei_id,
                            "comment_content": "",  # 内容将在详情爬取步骤中填充
                            "posted_at_on_channel": self._parse_post_time(item.get("posttime", "")),
                            "comment_source_url": ""  # URL将在详情爬取步骤中设置
                        }
                        
                        new_comments.append(comment_data)
                    
                    # 添加随机延迟避免反爬虫
                    if page < max_pages:
                        await asyncio.sleep(random.uniform(1.0, 1.5))
                        
                except Exception as e:
                    self.logger.warning(f"⚠️ 第 {page} 页爬取失败: {e}")
                    continue
        
        self.logger.info(f"🎯 收集到 {len(new_comments)} 条新评论")
        return new_comments
    
    async def _scrape_comments_contents(self, new_comments: List[dict], channel_config: dict):
        """
        爬取评论详细内容
        
        参数：
            new_comments: 新评论列表，每个元素包含 identifier_on_channel 等字段
            channel_config: 渠道配置，包含 koubei_detail.url 模板
        """
        try:
            # 获取详情API配置
            koubei_detail_config = channel_config.get("koubei_detail", {})
            detail_url_template = koubei_detail_config.get("url", "")
            
            if not detail_url_template:
                self.logger.warning("⚠️ 未找到 koubei_detail.url 配置，跳过内容爬取")
                return
            
            self.logger.info(f"🔧 使用详情API模板: {detail_url_template}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                for i, comment_data in enumerate(new_comments):
                    koubei_id = comment_data["identifier_on_channel"]
                    
                    try:
                        # 爬取单个评论详细内容
                        content = await self._scrape_single_comment_content(
                            client, koubei_id, detail_url_template
                        )
                        
                        # 更新评论数据
                        comment_data["comment_content"] = content
                        comment_data["comment_source_url"] = detail_url_template.format(koubei_id)
                        
                        self.logger.info(f"📝 [{i+1}/{len(new_comments)}] 成功爬取评论内容 - KoubeiID: {koubei_id}")
                        
                        # 添加延迟避免反爬虫
                        if i < len(new_comments) - 1:
                            await asyncio.sleep(random.uniform(1.0, 1.5))
                            
                    except Exception as e:
                        self.logger.warning(f"⚠️ [{i+1}/{len(new_comments)}] 爬取失败 - KoubeiID: {koubei_id}, 错误: {e}")
                        # 设置默认值，避免保存时出错
                        comment_data["comment_content"] = ""
                        comment_data["comment_source_url"] = detail_url_template.format(koubei_id)
            
            self.logger.info(f"✅ 评论内容爬取完成")
            
        except Exception as e:
            self.logger.error(f"❌ 评论内容爬取失败: {e}")
            # 为所有评论设置默认值
            for comment_data in new_comments:
                if "comment_content" not in comment_data:
                    comment_data["comment_content"] = ""
    
    async def _scrape_single_comment_content(
        self, 
        client: httpx.AsyncClient, 
        koubei_id: str, 
        url_template: str
    ) -> str:
        """
        爬取单个评论的详细内容
        
        参数：
            client: HTTP客户端
            koubei_id: 口碑ID
            url_template: URL模板
            
        返回：
            评论内容字符串
        """
        try:
            # 构建详情URL
            detail_url = url_template.format(koubei_id)
            
            # 发送请求
            response = await client.get(detail_url)
            response.raise_for_status()
            
            # 解析JSON数据
            data = response.json()
            
            # 提取评论内容
            if data and "result" in data and "content" in data["result"]:
                content = data["result"]["content"]
                if content and content.strip():
                    return content.strip()
                else:
                    self.logger.debug(f"📄 KoubeiID {koubei_id} 内容为空")
                    return ""
            else:
                self.logger.warning(f"⚠️ KoubeiID {koubei_id} JSON格式异常: {data}")
                return ""
                
        except httpx.HTTPStatusError as e:
            self.logger.warning(f"⚠️ HTTP错误 - KoubeiID: {koubei_id}, 状态码: {e.response.status_code}")
            return ""
        except Exception as e:
            self.logger.warning(f"⚠️ 请求异常 - KoubeiID: {koubei_id}, 错误: {e}")
            return ""
    
    def _parse_post_time(self, time_str: str) -> Optional[datetime]:
        """解析发布时间"""
        if not time_str:
            return None
        
        try:
            # 尝试解析不同的时间格式
            time_formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
                "%Y/%m/%d %H:%M:%S",
                "%Y/%m/%d"
            ]
            
            for fmt in time_formats:
                try:
                    return datetime.strptime(time_str, fmt)
                except ValueError:
                    continue
            
            self.logger.warning(f"⚠️ 无法解析时间格式: {time_str}")
            return None
            
        except Exception as e:
            self.logger.warning(f"⚠️ 时间解析异常: {e}")
            return None
    
    async def _save_new_comments(self, db, new_comments: List[dict], vehicle_channel_id: int) -> int:
        """保存新评论到数据库"""
        if not new_comments:
            return 0
        
        try:
            saved_count = 0
            
            for comment_data in new_comments:
                comment = RawComment(
                    vehicle_channel_id_fk=vehicle_channel_id,
                    identifier_on_channel=comment_data["identifier_on_channel"],
                    comment_content=comment_data["comment_content"],
                    posted_at_on_channel=comment_data["posted_at_on_channel"],
                    comment_source_url=comment_data["comment_source_url"],
                    # 新增：设置处理状态为新建状态
                    processing_status=ProcessingStatus.NEW
                )
                
                db.add(comment)
                saved_count += 1
            
            await db.commit()
            self.logger.info(f"💾 成功保存 {saved_count} 条新评论到数据库")
            
            return saved_count
            
        except Exception as e:
            await db.rollback()
            self.logger.error(f"❌ 保存评论失败: {e}")
            raise


# 全局服务实例
raw_comment_update_service = RawCommentUpdateService() 