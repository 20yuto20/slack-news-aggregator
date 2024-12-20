from typing import Optional
from datetime import datetime
import re
from urllib.parse import urljoin, urlparse
import unicodedata
import logging

logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """
    テキストのクリーニング

    Args:
        text: クリーニング対象のテキスト

    Returns:
        str: クリーニング済みのテキスト
    """
    if not text:
        return ""

    # Unicode正規化
    text = unicodedata.normalize('NFKC', text)
    
    # 空白文字の正規化
    text = re.sub(r'\s+', ' ', text)
    
    # 前後の空白を削除
    text = text.strip()
    
    # 特殊文字の削除
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    return text

def extract_date(text: str) -> Optional[datetime]:
    """
    テキストから日付を抽出

    Args:
        text: 日付を含むテキスト

    Returns:
        datetime: 抽出した日付。抽出失敗時はNone
    """
    # 正規化
    text = clean_text(text)
    
    # よくある日付パターン
    patterns = [
        # 2023年12月25日 15:30
        r'(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日\s*(\d{1,2}):(\d{2})',
        # 2023/12/25 15:30
        r'(\d{4})/(\d{1,2})/(\d{1,2})\s*(\d{1,2}):(\d{2})',
        # 2023-12-25 15:30
        r'(\d{4})-(\d{1,2})-(\d{1,2})\s*(\d{1,2}):(\d{2})',
        # 2023年12月25日
        r'(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日',
        # 2023/12/25
        r'(\d{4})/(\d{1,2})/(\d{1,2})',
        # 2023-12-25
        r'(\d{4})-(\d{1,2})-(\d{1,2})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                groups = match.groups()
                if len(groups) >= 5:  # 時刻あり
                    return datetime(
                        year=int(groups[0]),
                        month=int(groups[1]),
                        day=int(groups[2]),
                        hour=int(groups[3]),
                        minute=int(groups[4])
                    )
                else:  # 日付のみ
                    return datetime(
                        year=int(groups[0]),
                        month=int(groups[1]),
                        day=int(groups[2])
                    )
            except ValueError as e:
                logger.warning(f"Invalid date values in text '{text}': {str(e)}")
                continue
    
    return None

def normalize_url(url: str, base_url: str) -> str:
    """
    URLを正規化

    Args:
        url: 正規化対象のURL
        base_url: ベースURL

    Returns:
        str: 正規化したURL
    """
    # 相対URLを絶対URLに変換
    url = urljoin(base_url, url)
    
    # URLをパースして正規化
    parsed = urlparse(url)
    
    # スキームがない場合はhttpsを使用
    scheme = parsed.scheme or 'https'
    
    # クエリパラメータを並び替え
    query = '&'.join(sorted(parsed.query.split('&'))) if parsed.query else ''
    
    # フラグメントは削除
    fragment = ''
    
    # 正規化したURLを組み立て
    normalized = f"{scheme}://{parsed.netloc}{parsed.path}"
    if query:
        normalized += f"?{query}"
    if fragment:
        normalized += f"#{fragment}"
    
    return normalized

def extract_title(text: str, max_length: int = 100) -> str:
    """
    テキストからタイトルとして適切な部分を抽出

    Args:
        text: 抽出対象のテキスト
        max_length: 最大文字数

    Returns:
        str: 抽出したタイトル
    """
    if not text:
        return ""

    # テキストをクリーニング
    text = clean_text(text)
    
    # 改行で分割して最初の意味のある行を取得
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if not lines:
        return ""
    
    title = lines[0]
    
    # 最大文字数で切る
    if len(title) > max_length:
        title = title[:max_length-3] + "..."
    
    return title

def is_valid_article_url(url: str) -> bool:
    """
    URLが記事として有効かチェック

    Args:
        url: チェック対象のURL

    Returns:
        bool: 有効な場合True
    """
    if not url:
        return False

    try:
        parsed = urlparse(url)
        
        # スキームチェック
        if parsed.scheme not in ['http', 'https']:
            return False
        
        # ホスト名チェック
        if not parsed.netloc:
            return False
        
        # 拡張子チェック
        if parsed.path:
            invalid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip']
            if any(parsed.path.lower().endswith(ext) for ext in invalid_extensions):
                return False
        
        return True
        
    except Exception:
        return False

def extract_company_name(text: str) -> Optional[str]:
    """
    テキストから企業名を抽出

    Args:
        text: 抽出対象のテキスト

    Returns:
        str: 抽出した企業名。抽出失敗時はNone
    """
    # 企業名のパターン
    patterns = [
        r'株式会社[^\s\d「」（）\(\)]{2,}',
        r'[^\s\d「」（）\(\)]{2,}株式会社',
        r'合同会社[^\s\d「」（）\(\)]{2,}',
        r'[^\s\d「」（）\(\)]{2,}合同会社'
    ]
    
    text = clean_text(text)
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    
    return None