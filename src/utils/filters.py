from typing import Optional
import re
from urllib.parse import urlparse, urljoin, urlunparse
import unicodedata
import html
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def clean_text(text: str, max_length: Optional[int] = None) -> str:
    """
    テキストをクリーニング

    Args:
        text: クリーニング対象のテキスト
        max_length: 最大文字数

    Returns:
        str: クリーニング済みのテキスト
    """
    if not text:
        return ""

    # HTMLエスケープを解除
    text = html.unescape(text)

    # Unicode正規化
    text = unicodedata.normalize('NFKC', text)

    # 改行・タブ・スペースの正規化
    text = re.sub(r'[\n\t\r]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)

    # 前後の空白を削除
    text = text.strip()

    # 不要な文字を削除
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)

    # 最大文字数で切る
    if max_length and len(text) > max_length:
        text = text[:max_length] + '...'

    return text

def normalize_url(url: str, base_url: Optional[str] = None) -> str:
    """
    URLを正規化

    Args:
        url: 正規化対象のURL
        base_url: ベースURL（相対URLの場合に使用）

    Returns:
        str: 正規化したURL
    """
    if not url:
        return ""

    # 相対URLを絶対URLに変換
    if base_url:
        url = urljoin(base_url, url)

    # URLをパース
    parsed = urlparse(url)

    # スキームとホストを小文字に
    scheme = parsed.scheme.lower() or 'https'
    netloc = parsed.netloc.lower()

    # パスの正規化
    path = parsed.path
    if not path:
        path = '/'
    elif not path.startswith('/'):
        path = '/' + path

    # クエリパラメータを並び替え
    query = '&'.join(sorted(parsed.query.split('&'))) if parsed.query else ''

    # フラグメントは削除
    fragment = ''

    # 正規化したURLを組み立て
    return urlunparse((scheme, netloc, path, '', query, fragment))

def validate_url(url: str) -> bool:
    """
    URLの形式を検証

    Args:
        url: 検証するURL

    Returns:
        bool: 有効なURLの場合True
    """
    if not url:
        return False

    try:
        parsed = urlparse(url)
        
        # スキームのチェック
        if parsed.scheme not in ['http', 'https']:
            return False
            
        # ホスト名のチェック
        if not parsed.netloc:
            return False
            
        # パスのチェック
        if parsed.path:
            # 禁止拡張子のチェック
            forbidden_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip']
            if any(parsed.path.lower().endswith(ext) for ext in forbidden_extensions):
                return False
                
        return True
        
    except Exception:
        return False

def extract_text_content(html_text: str) -> str:
    """
    HTMLからテキストを抽出

    Args:
        html_text: HTML文字列

    Returns:
        str: 抽出したテキスト
    """
    # HTMLタグを削除
    text = re.sub(r'<[^>]+>', ' ', html_text)
    
    # 特殊文字を置換
    text = html.unescape(text)
    
    # 空白文字を正規化
    text = clean_text(text)
    
    return text

def filter_japanese_text(text: str) -> str:
    """
    日本語テキストのみを抽出

    Args:
        text: 抽出対象のテキスト

    Returns:
        str: 日本語テキストのみを含む文字列
    """
    # 日本語文字（ひらがな、カタカナ、漢字）のパターン
    jp_pattern = r'[ぁ-んァ-ン一-龥]'
    
    # 日本語を含む行のみを抽出
    lines = []
    for line in text.split('\n'):
        if re.search(jp_pattern, line):
            lines.append(line)
    
    return '\n'.join(lines)

def remove_noise_words(text: str, noise_words: Optional[list] = None) -> str:
    """
    ノイズワードを除去

    Args:
        text: 対象テキスト
        noise_words: 除去するワードのリスト

    Returns:
        str: ノイズワードを除去したテキスト
    """
    # TODO: ワードのチョイスを仮決め
    if noise_words is None:
        noise_words = [
            'PR TIMES',
            'プレスリリース',
            '株式会社',
            '運営する',
            'お知らせ'
        ]
    
    for word in noise_words:
        text = text.replace(word, '')
    
    return clean_text(text)

def sanitize_filename(filename: str) -> str:
    """
    ファイル名を安全な形式に変換

    Args:
        filename: 変換対象のファイル名

    Returns:
        str: 安全なファイル名
    """
    # 使用できない文字を除去
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # 空白文字をアンダースコアに変換
    filename = re.sub(r'\s+', '_', filename)
    
    # 前後の不要な文字を削除
    filename = filename.strip('._')
    
    return filename