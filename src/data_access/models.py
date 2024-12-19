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
        記事のデータをdict形式に変換する

        Returns:
            dict: dictに変形された記事データ
        """
        return{
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