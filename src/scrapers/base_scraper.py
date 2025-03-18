from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from bs4 import BeautifulSoup
import requests

class BaseScraper(ABC):
    """スクレイパーの基底クラス"""
    
    def __init__(self, timeout: int = 30, retry: int = 3):
        self.timeout = timeout
        self.retry = retry
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    @abstractmethod
    def get_news(self, url: str) -> List[Dict[str, Any]]:
        """
        ニュース記事を取得する抽象メソッド
        """
        pass

    def _fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """
        ページを取得してBeautifulSoupオブジェクトを返す
        """
        for i in range(self.retry):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                return BeautifulSoup(response.text, 'html.parser')
            except requests.RequestException as e:
                self.logger.error(f"Failed to fetch {url}: {str(e)}")
                if i == self.retry - 1:
                    return None
                continue
        return None

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        日付文字列をdatetimeオブジェクトにパースする
        """
        date_formats = [
            '%Y年%m月%d日',
            '%Y/%m/%d',
            '%Y-%m-%d',
            '%Y.%m.%d'
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        self.logger.warning(f"Failed to parse date string: {date_str}")
        return None

    def _clean_text(self, text: str) -> str:
        """
        テキストの前後の空白を除去し、改行を正規化する
        """
        if not text:
            return ""
        return " ".join(text.strip().split())
