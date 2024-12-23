from typing import List, Dict, Any, Optional
from datetime import datetime
import re
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

class PRTimesScraper(BaseScraper):
    """
    PRTimes専用のスクレイパークラス
    """

    def __init__(self, timeout: int = 30, retry: int = 3):
        super().__init__(timeout, retry)
        self.base_url = "https://prtimes.jp"

    def get_news(self, url: str) -> List[Dict[str, Any]]:
        """
        PRTimesからの企業のプレスリリース一覧を取得する
        """
        soup = self._fetch_page(url)
        if not soup:
            return []

        articles = []
        for article in self._find_articles(soup):
            try:
                article_data = self._parse_article(article)
                if article_data:
                    articles.append(article_data)
            except Exception as e:
                self.logger.error(f"Failed to parse article: {str(e)}")
                continue
        
        return articles

    def _find_articles(self, soup: BeautifulSoup) -> List[Any]:
        """
        PRTimesからニュースCardを全て取得
        """
        return soup.find_all('article', class_='list-article')

    def _parse_article(self, article: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """
        個別の記事要素をパースして記事情報を抽出
        """
        try:
            # タイトルとURLの取得
            title_elem = article.find('h2', class_='list-article_title')
            if not title_elem or not title_elem.find('a'):
                return None

            title = self._clean_text(title_elem.find('a').text)
            url = self.base_url + title_elem.find('a')['href']

            # 公開日時の取得
            date_elem = article.find('time')
            if not date_elem:
                return None

            published_at = self._parse_prtimes_date(date_elem.text)
            if not published_at:
                return None
            
            # 画像URLの取得
            image_url = None
            img_elem = article.find('img', class_='list-article_image')
            if img_elem and 'src' in img_elem.attrs:
                image_url = img_elem['src']

            # 概要文の取得
            content = None
            content_elem = article.find('p', class_='list-article__summary')
            if content_elem:
                content = self._clean_text(content_elem.text)

            return {
                'title': title,
                'url': url,
                'published_at': published_at,
                'content': content,
                'image_url': image_url,
                'source': 'prtimes'
            }

        except Exception as e:
            self.logger.error(f"Error parsing article: {str(e)}")
            return None

    def _parse_prtimes_date(self, date_str: str) -> Optional[datetime]:
        """
        PR Times固有の日付フォーマットをパース
        """
        pattern = r'(\d{4})年(\d{1,2})月(\d{1,2})日\s+(\d{1,2}):(\d{2})'
        match = re.match(pattern, date_str)
        if not match:
            return None
            
        try:
            year, month, day, hour, minute = map(int, match.groups())
            return datetime(year, month, day, hour, minute)
        except ValueError as e:
            self.logger.error(f"Error parsing date {date_str}: {str(e)}")
            return None
