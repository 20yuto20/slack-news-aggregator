from typing import List, Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
import yaml
import os

class GenericScraper(BaseScraper):
    """企業HP用の汎用スクレイパークラス"""

    def __init__(self, company_id: str, timeout: int = 30, retry: int = 3):
        super().__init__(timeout, retry)
        self.company_id = company_id
        self.config = self._load_company_config()

    def _load_company_config(self) -> Dict[str, Any]:
        """
        companies.yamlから企業固有の設定を読み込む
        
        Returns:
            Dict: 企業のスクレイピング設定
        """
        config_path = os.path.join(os.path.dirname(__file__), '../configs/companies.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            companies = yaml.safe_load(f)
            
        for company in companies:
            if company['id'] == self.company_id:
                return company['hp_news']
                
        raise ValueError(f"Company config not found for ID: {self.company_id}")

    def get_news(self, url: str) -> List[Dict[str, Any]]:
        """
        企業HPからニュース記事を取得する
        
        Args:
            url: ニュースページのURL
            
        Returns:
            List[Dict]: 取得した記事のリスト
        """
        soup = self._fetch_page(url)
        if not soup:
            return []

        articles = []
        selectors = self.config['selector']
        
        # ニュース記事の一覧を取得
        article_wrapper = soup.find(class_=selectors.get('articles_wrapper', 'news-list'))
        if not article_wrapper:
            self.logger.error(f"Could not find news article wrapper for {url}")
            return []

        # 各記事要素を解析
        for article in article_wrapper.find_all(class_=selectors.get('article', 'news-item')):
            try:
                article_data = self._parse_article(article, selectors)
                if article_data:
                    article_data['url'] = self._make_absolute_url(url, article_data['url'])
                    articles.append(article_data)
            except Exception as e:
                self.logger.error(f"Failed to parse article: {str(e)}")
                continue

        return articles

    def _parse_article(self, article: BeautifulSoup, selectors: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        個別の記事要素をパースして記事情報を抽出
        
        Args:
            article: 個別の記事要素
            selectors: 要素を特定するためのセレクタ設定
            
        Returns:
            Dict: パースした記事情報
        """
        try:
            # タイトルの取得
            title_elem = article.find(class_=selectors['title'])
            if not title_elem:
                return None
            title = self._clean_text(title_elem.text)

            # URLの取得
            url = None
            link_elem = title_elem.find('a') if title_elem else None
            if link_elem and 'href' in link_elem.attrs:
                url = link_elem['href']
            else:
                return None

            # 公開日時の取得
            date_elem = article.find(class_=selectors['date'])
            if not date_elem:
                return None
            published_at = self._parse_date(self._clean_text(date_elem.text))
            if not published_at:
                return None

            # 概要文の取得
            content = None
            content_elem = article.find(class_=selectors.get('content'))
            if content_elem:
                content = self._clean_text(content_elem.text)

            # 画像URLの取得
            image_url = None
            img_elem = article.find('img')
            if img_elem and 'src' in img_elem.attrs:
                image_url = img_elem['src']

            return {
                'title': title,
                'url': url,
                'published_at': published_at,
                'content': content,
                'image_url': image_url,
                'source': 'hp'
            }

        except Exception as e:
            self.logger.error(f"Error parsing article: {str(e)}")
            return None

    def _make_absolute_url(self, base_url: str, relative_url: str) -> str:
        """
        相対URLを絶対URLに変換する
        
        Args:
            base_url: ベースとなるURL
            relative_url: 相対URL
            
        Returns:
            str: 絶対URL
        """
        if relative_url.startswith(('http://', 'https://')):
            return relative_url

        from urllib.parse import urljoin
        return urljoin(base_url, relative_url)