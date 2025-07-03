"""
汽车之家渠道解析器
实现汽车之家网站的车型数据爬取和解析
"""
import string
import asyncio
import random
import json
import httpx
import time
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from datetime import datetime

from app.core.config import settings
from app.core.logging import app_logger


class Brand:
    """
    品牌类 - 解析汽车之家页面中的品牌信息
    """
    def __init__(self, html_element):
        self.html = html_element
        self.brand_id = self._parse_brand_id()
        self.brand_name = self._parse_brand_name()
        self.manufactor_list = self._parse_manufactor_list()
    
    def _parse_brand_id(self):
        """解析品牌ID"""
        try:
            return self.html.attrs['id']
        except KeyError:
            return None

    def _parse_brand_name(self):
        """解析品牌名称"""
        brand_name_element = self.html.find('dt')
        try:
            return brand_name_element.text.strip() if brand_name_element else None
        except:
            return None

    def _parse_manufactor_list(self):
        """解析厂商和车型列表"""
        manufactor_list = self.html.find_all('ul')
        result = []
        for ul in manufactor_list:
            # 查找对应的厂商名称
            manufactor_div = ul.find_previous('div', attrs={'class': 'h3-tit'})
            if manufactor_div:
                result.append((manufactor_div, ul))
        return result


class AutoHomeParser:
    """
    汽车之家渠道解析器
    专门处理汽车之家网站的车型数据解析
    """
    
    def __init__(self):
        self.delay_range = (1, 3)  # 请求间隔范围（秒）
        self.timeout = 10
        self.headers = {
            'User-Agent': settings.SCRAPER_USER_AGENT
        }
        self.extraction_stats = {
            "pages_processed": 0,
            "vehicles_found": 0,
            "brands_found": 0,
            "start_time": None,
            "end_time": None
        }
        self.logger = app_logger
    
    def _log_progress(self, message: str, level: str = "info"):
        """记录进度日志"""
        if level == "info":
            self.logger.info(f"[汽车之家解析器] {message}")
        elif level == "warning":
            self.logger.warning(f"[汽车之家解析器] {message}")
        elif level == "error":
            self.logger.error(f"[汽车之家解析器] {message}")
    
    async def extract_vehicles(self, channel_id: int) -> List[Dict]:
        """
        提取汽车之家的车型数据
        
        Args:
            channel_id: 渠道ID
            
        Returns:
            车型信息列表
        """
        self.extraction_stats["start_time"] = datetime.utcnow()
        
        try:
            self._log_progress("开始提取车型数据")
            
            # 从数据库获取渠道信息
            from app.core.database import AsyncSessionLocal
            from app.models.vehicle_update import Channel
            from sqlalchemy import select
            
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Channel).where(Channel.channel_id == channel_id)
                )
                channel = result.scalar_one_or_none()
                
                if not channel:
                    raise ValueError(f"渠道ID {channel_id} 不存在")
                
                # 解析channel_base_url JSON
                try:
                    url_config = json.loads(channel.channel_base_url)
                    brand_overview_url = url_config['brand_overview']['url']
                    self._log_progress(f"获取到品牌总览URL模板: {brand_overview_url}")
                except (json.JSONDecodeError, KeyError) as e:
                    raise ValueError(f"渠道URL配置格式错误: {e}")
                
                # 提取所有车型
                vehicles = await self._extract_all_vehicles(
                    brand_overview_url, 
                    channel_id, 
                    channel.channel_name
                )
            
            self.extraction_stats["vehicles_found"] = len(vehicles)
            self.extraction_stats["end_time"] = datetime.utcnow()
            
            self._log_progress(f"车型提取完成，共获取 {len(vehicles)} 个车型")
            
            return vehicles
            
        except Exception as e:
            self._log_progress(f"车型提取失败: {e}", "error")
            raise
    
    async def _extract_all_vehicles(self, brand_overview_url: str, channel_id: int, channel_name: str) -> List[Dict]:
        """
        提取所有车型数据
        
        Args:
            brand_overview_url: 品牌总览URL模板
            channel_id: 渠道ID
            channel_name: 渠道名称
            
        Returns:
            车型信息列表
        """
        vehicles = []
        
        try:
            # 获取所有页面的品牌信息
            brands_with_letter = await self._get_page_brands(brand_overview_url)
            
            # 遍历品牌、厂商、车型
            for brand, letter in brands_with_letter:
                if not brand.brand_id or not brand.brand_name:
                    continue
                    
                self._log_progress(f"处理品牌: {brand.brand_name} (ID: {brand.brand_id})")
                
                # 遍历厂商和车型
                for manufactor_div, ul in brand.manufactor_list:
                    if not manufactor_div or not ul:
                        continue
                        
                    manufactor = manufactor_div.get_text(strip=True)
                    
                    # 遍历车型
                    for li in ul.find_all('li'):
                        vehicle_id = li.get('id')
                        if not vehicle_id:
                            continue
                            
                        h4 = li.find('h4')
                        vehicle_name = h4.get_text(strip=True) if h4 else None
                        
                        if not vehicle_name:
                            continue
                        
                        # 构建车型详情URL
                        vehicle_url = f"https://www.autohome.com.cn/spec/{vehicle_id}/"
                        
                        # 创建车型记录
                        vehicle_record = {
                            "channel_id": channel_id,
                            "channel_name": channel_name, 
                            "vehicle_id": vehicle_id,
                            "vehicle_name": vehicle_name,
                            "brand_id": brand.brand_id,
                            "brand_name": brand.brand_name,
                            "manufactor": manufactor,
                            "vehicle_url": vehicle_url,
                            "extracted_at": datetime.utcnow().isoformat()
                        }
                        vehicles.append(vehicle_record)
            
            self.extraction_stats["brands_found"] = len(set(brand.brand_id for brand, _ in brands_with_letter if brand.brand_id))
            
        except Exception as e:
            self._log_progress(f"提取车型数据失败: {e}", "error")
            raise
        
        return vehicles
    
    async def _get_page_brands(self, website_base_url: str) -> List[tuple]:
        """
        根据base_url和字母序，获取各个页面中的品牌信息
        
        Args:
            website_base_url: URL模板，包含{}占位符
            
        Returns:
            (Brand, letter) 元组列表
        """
        brands = []
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # 爬取完整的26个字母 (约10分钟)
            # 使用完整字母表以获取所有品牌
            letters = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
            self._log_progress(f"开始爬取 {len(letters)} 个字母的品牌页面")
            
            for letter in letters:
                try:
                    # 构建当前字母对应的URL
                    start_url = website_base_url.format(letter.lower())
                    self._log_progress(f"正在处理品牌字母: {letter}, URL: {start_url}")
                    
                    # 发送HTTP请求
                    response = await client.get(start_url, headers=self.headers)
                    response.raise_for_status()
                    
                    # 解析HTML
                    html = BeautifulSoup(response.content, "html.parser")
                    
                    # 查找所有品牌区块 (dl标签)
                    for dl in html.find_all('dl'):
                        try:
                            brand = Brand(dl)
                            if brand.brand_id and brand.brand_name:  # 只保留有效的品牌
                                brands.append((brand, letter))
                        except Exception as e:
                            self._log_progress(f"解析品牌区块出错: {e}", "warning")
                    
                    self.extraction_stats["pages_processed"] += 1
                    
                    # 添加延迟避免被封
                    await asyncio.sleep(random.uniform(*self.delay_range))
                    
                except Exception as e:
                    self._log_progress(f"请求 {start_url} 失败: {e}", "warning")
                    continue
        
        return brands
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取解析统计信息"""
        return {
            "channel_name": "汽车之家",
            "extraction_stats": self.extraction_stats,
            "last_extraction_time": self.extraction_stats.get("end_time"),
            "total_extracted": self.extraction_stats.get("vehicles_found", 0),
            "parser_version": "2.0.0"
        }

 