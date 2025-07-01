"""
爬虫工具模块
"""
import asyncio
import aiohttp
import httpx
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from typing import List, Dict, Optional
from app.core.config import settings
from app.core.logging import app_logger

class BaseScraper:
    """
    基础爬虫类
    """
    
    def __init__(self):
        self.session = None
        self.logger = app_logger
        self.delay = settings.REQUEST_DELAY
        self.max_retry = settings.MAX_RETRY
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={'User-Agent': settings.SCRAPER_USER_AGENT}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def fetch_page(self, url: str) -> str:
        """
        获取页面内容（异步）
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url, 
                    headers={'User-Agent': settings.SCRAPER_USER_AGENT},
                    timeout=30.0
                )
                response.raise_for_status()
                return response.text
        except Exception as e:
            self.logger.error(f"Failed to fetch page {url}: {e}")
            raise
    
    def fetch_page_sync(self, url: str) -> str:
        """
        获取页面内容（同步）
        """
        try:
            response = requests.get(
                url,
                headers={'User-Agent': settings.SCRAPER_USER_AGENT},
                timeout=30
            )
            response.raise_for_status()
            return response.text
        except Exception as e:
            self.logger.error(f"Failed to fetch page {url}: {e}")
            raise
    
    async def parse_comments(self, html: str) -> List[Dict]:
        """
        解析评论数据
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            comments = []
            # 这里需要根据具体网站的HTML结构来实现
            # 示例代码：
            # comment_elements = soup.find_all('div', class_='comment')
            # for element in comment_elements:
            #     comment = {
            #         'content': element.get_text(strip=True),
            #         'author': element.find('span', class_='author').get_text(strip=True),
            #         'rating': self._extract_rating(element),
            #         'date': element.find('time').get('datetime', '')
            #     }
            #     comments.append(comment)
            return comments
        except Exception as e:
            self.logger.error(f"Failed to parse comments: {e}")
            return []

class SeleniumScraper(BaseScraper):
    """
    基于Selenium的动态页面爬虫
    """
    
    def __init__(self):
        super().__init__()
        self.driver: Optional[webdriver.Chrome] = None
    
    def setup_driver(self):
        """
        设置Chrome WebDriver
        """
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # 无头模式
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument(f'--user-agent={settings.SCRAPER_USER_AGENT}')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.logger.info("Chrome WebDriver initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Chrome WebDriver: {e}")
            raise
    
    def close_driver(self):
        """
        关闭WebDriver
        """
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def fetch_dynamic_page(self, url: str) -> str:
        """
        获取动态页面内容
        """
        if not self.driver:
            self.setup_driver()
        
        try:
            self.driver.get(url)
            # 等待页面加载
            asyncio.sleep(2)
            return self.driver.page_source
        except Exception as e:
            self.logger.error(f"Failed to fetch dynamic page {url}: {e}")
            raise

class AutoHomeScraper(BaseScraper):
    """
    汽车之家爬虫
    """
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.autohome.com.cn"
    
    async def crawl_car_reviews(self, car_id: str) -> List[Dict]:
        """
        爬取汽车评论
        """
        try:
            url = f"{self.base_url}/spec/{car_id}/review/"
            html = await self.fetch_page(url)
            return await self.parse_comments(html)
        except Exception as e:
            self.logger.error(f"Failed to crawl AutoHome reviews for car {car_id}: {e}")
            return []

class BitAutoScraper(BaseScraper):
    """
    易车网爬虫
    """
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.bitauto.com"
    
    async def crawl_car_reviews(self, car_id: str) -> List[Dict]:
        """
        爬取汽车评论
        """
        try:
            url = f"{self.base_url}/car/{car_id}/review/"
            html = await self.fetch_page(url)
            return await self.parse_comments(html)
        except Exception as e:
            self.logger.error(f"Failed to crawl BitAuto reviews for car {car_id}: {e}")
            return [] 