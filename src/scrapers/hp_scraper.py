from typing import List, Dict, Any, Optional
from datetime import datetime
import re
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from .utils import clean_text, extract_date, normalize_url
import logging

class HPScraper(BaseScraper):
    """企業HP専用のスクレイパークラス"""

    def __init__(self, company_id: str, timeout: int = 30, retry: int = 3):
        super().__init__(timeout, retry)
        self.company_id = company_id
        self.logger = logging.getLogger(__name__)
        self.parser_config = self._load_parser_config()

    def _load_parser_config(self) -> Dict[str, Any]:
        """企業固有のパース設定を読み込む"""
        company_config = self._get_company_config()
        return company_config.get('hp_news', {}).get('parser', {})

    def get_news(self, url: str) -> List[Dict[str, Any]]:
        """
        企業HPからニュース記事を取得

        Args:
            url: 企業のニュースページURL

        Returns:
            List[Dict]: 取得した記事のリスト
        """
        soup = self._fetch_page(url)
        if not soup:
            return []

        articles = []
        article_list = self._find_article_list(soup)
        
        if not article_list:
            self.logger.warning(f"No article list found for URL: {url}")
            return []

        for article_elem in article_list:
            try:
                article_data = self._parse_article(article_elem, base_url=url)
                if article_data:
                    articles.append(article_data)
            except Exception as e:
                self.logger.error(f"Error parsing article: {str(e)}")
                continue

        return articles

    def _find_article_list(self, soup: BeautifulSoup) -> List[Any]:
        """
        ニュース記事のリストを特定

        Args:
            soup: パース済みのページHTML

        Returns:
            List: 記事要素のリスト
        """
        selectors = [
            self.parser_config.get('list_selector', ''),
            'ul.news-list',
            'div.news-list',
            'div.news',
            'div.news-contents'
        ]

        for selector in selectors:
            if not selector:
                continue
            article_list = soup.select(selector)
            if article_list:
                return article_list

        # セレクタで見つからない場合は記事っぽい要素を探す
        return soup.find_all(['article', 'div', 'li'], 
                           class_=re.compile(r'news|article|post'))

    def _parse_article(self, article: BeautifulSoup, base_url: str) -> Optional[Dict[str, Any]]:
        """
        個別の記事要素をパース

        Args:
            article: 個別の記事要素
            base_url: 記事の基準URL

        Returns:
            Dict: パースした記事情報
        """
        try:
            # タイトルの取得
            title_elem = self._get_title_element(article)
            if not title_elem:
                return None
            
            title = clean_text(title_elem.text)
            if not title:
                return None

            # URLの取得
            url = self._get_article_url(title_elem, base_url)
            if not url:
                return None

            # 日付の取得
            date_elem = self._get_date_element(article)
            if not date_elem:
                return None
                
            published_at = extract_date(date_elem.text)
            if not published_at:
                return None

            # 概要文の取得
            content = None
            content_elem = self._get_content_element(article)
            if content_elem:
                content = clean_text(content_elem.text)

            # 画像URLの取得
            image_url = self._get_image_url(article, base_url)

            return {
                'title': title,
                'url': url,
                'published_at': published_at,
                'content': content,
                'image_url': image_url,
                'source': 'hp'
            }

        except Exception as e:
            self.logger.error(f"Error parsing article element: {str(e)}")
            return None

    def _get_title_element(self, article: BeautifulSoup) -> Optional[BeautifulSoup]:
        """タイトル要素を取得"""
        selectors = [
            self.parser_config.get('title_selector', ''),
            '.news-title',
            '.article-title',
            '.title'
        ]
        
        for selector in selectors:
            if not selector:
                continue
            title_elem = article.select_one(selector)
            if title_elem:
                return title_elem

        # セレクタで見つからない場合は見出し要素を探す
        return article.find(['h1', 'h2', 'h3', 'h4'])

    def _get_date_element(self, article: BeautifulSoup) -> Optional[BeautifulSoup]:
        """日付要素を取得"""
        selectors = [
            self.parser_config.get('date_selector', ''),
            '.news-date',
            '.article-date',
            '.date'
        ]
        
        for selector in selectors:
            if not selector:
                continue
            date_elem = article.select_one(selector)
            if date_elem:
                return date_elem

        # セレクタで見つからない場合は日付っぽい要素を探す
        return article.find(['time', 'span', 'div'], 
                          class_=re.compile(r'date|time|published'))

    def _get_content_element(self, article: BeautifulSoup) -> Optional[BeautifulSoup]:
        """概要文要素を取得"""
        selectors = [
            self.parser_config.get('content_selector', ''),
            '.news-content',
            '.article-content',
            '.description'
        ]
        
        for selector in selectors:
            if not selector:
                continue
            content_elem = article.select_one(selector)
            if content_elem:
                return content_elem

        return article.find(['p', 'div'], 
                          class_=re.compile(r'content|description|text'))

    def _get_article_url(self, title_elem: BeautifulSoup, base_url: str) -> Optional[str]:
        """記事URLを取得"""
        link = title_elem.find('a')
        if not link or 'href' not in link.attrs:
            return None
            
        url = link['href']
        return normalize_url(url, base_url)

    def _get_image_url(self, article: BeautifulSoup, base_url: str) -> Optional[str]:
        """画像URLを取得"""
        img = article.find('img')
        if not img or 'src' not in img.attrs:
            return None
            
        return normalize_url(img['src'], base_url)