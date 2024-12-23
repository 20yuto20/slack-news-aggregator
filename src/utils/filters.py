from typing import Optional
import re
from urllib.parse import urlparse, urljoin, urlunparse
import unicodedata
import html
import logging

logger = logging.getLogger(__name__)

def clean_text(text: str, max_length: Optional[int] = None) -> str:
    """
    テキストをクリーニング
    """
    if not text:
        return ""

    text = html.unescape(text)
    text = unicodedata.normalize('NFKC', text)
    text = re.sub(r'[\n\t\r]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)

    if max_length and len(text) > max_length:
        text = text[:max_length] + '...'

    return text

def normalize_url(url: str, base_url: Optional[str] = None) -> str:
    """
    URLを正規化
    """
    if not url:
        return ""
    if base_url:
        url = urljoin(base_url, url)

    parsed = urlparse(url)
    scheme = parsed.scheme.lower() or 'https'
    netloc = parsed.netloc.lower()
    path = parsed.path
    if not path:
        path = '/'
    elif not path.startswith('/'):
        path = '/' + path

    query = '&'.join(sorted(parsed.query.split('&'))) if parsed.query else ''
    fragment = ''

    return urlunparse((scheme, netloc, path, '', query, fragment))

def validate_url(url: str) -> bool:
    """
    URLの形式を検証
    """
    if not url:
        return False
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ['http', 'https']:
            return False
        if not parsed.netloc:
            return False
        if parsed.path:
            forbidden_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip']
            if any(parsed.path.lower().endswith(ext) for ext in forbidden_extensions):
                return False
        return True
    except Exception:
        return False

def extract_text_content(html_text: str) -> str:
    """
    HTMLからテキストを抽出
    """
    text = re.sub(r'<[^>]+>', ' ', html_text)
    text = html.unescape(text)
    text = clean_text(text)
    return text

def filter_japanese_text(text: str) -> str:
    """
    日本語テキストのみを抽出
    """
    jp_pattern = r'[ぁ-んァ-ン一-龥]'
    lines = []
    for line in text.split('\n'):
        if re.search(jp_pattern, line):
            lines.append(line)
    return '\n'.join(lines)

def remove_noise_words(text: str, noise_words: Optional[list] = None) -> str:
    """
    ノイズワードを除去
    """
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
    """
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = re.sub(r'\s+', '_', filename)
    filename = filename.strip('._')
    return filename
