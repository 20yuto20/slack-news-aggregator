from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

@dataclass
class Article:
    # TODO: 必要に応じてデータの構造を変える
    """
    記事データのモデルクラス
    """
    id: str
    company_id: str
    title: str
    url: str
    published_at: datetime
    content: Optional[str]
    image_url: Optional[str]
    source: str
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict:
        """
        記事データを辞書形式に変換
        
        Returns:
            dict: 記事データの辞書
        """
        return {
            'id': self.id,
            'company_id': self.company_id,
            'title': self.title,
            'url': self.url,
            'published_at': self.published_at,
            'content': self.content,
            'image_url': self.image_url,
            'source': self.source,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

@dataclass
class Company:
    """企業データのモデルクラス"""
    id: str
    name: str
    hp_url: Optional[str]
    prtimes_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict:
        """
        企業データを辞書形式に変換
        
        Returns:
            dict: 企業データの辞書
        """
        return {
            'id': self.id,
            'name': self.name,
            'hp_url': self.hp_url,
            'prtimes_url': self.prtimes_url,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

@dataclass
class ScrapingResult:
    """スクレイピング結果のモデルクラス"""
    company_id: str
    source: str
    success: bool
    articles_count: int
    error_message: Optional[str] = None
    execution_time: Optional[float] = None

    def to_dict(self) -> dict:
        """
        スクレイピング結果を辞書形式に変換
        
        Returns:
            dict: スクレイピング結果の辞書
        """
        return {
            'company_id': self.company_id,
            'source': self.source,
            'success': self.success,
            'articles_count': self.articles_count,
            'error_message': self.error_message,
            'execution_time': self.execution_time
        }