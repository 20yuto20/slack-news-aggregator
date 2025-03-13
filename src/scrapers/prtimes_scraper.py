from typing import List, Dict, Any, Optional
from datetime import datetime
import re
import time
import logging

# --- ここから追加: Selenium 関連 ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

from bs4 import BeautifulSoup

# --- ここまで追加 ---

from .base_scraper import BaseScraper


class PRTimesScraper(BaseScraper):
    """
    PRTimes専用のスクレイパークラス (Selenium版)
    """

    def __init__(self, timeout: int = 30, retry: int = 3):
        super().__init__(timeout, retry)
        self.base_url = "https://prtimes.jp"

    def get_news(self, url: str) -> List[Dict[str, Any]]:
        """
        「もっと見る」ボタンをクリックして、表示されるすべての記事を取得する

        Args:
            url (str): 企業のプレスリリース一覧のURL

        Returns:
            List[Dict[str, Any]]: 取得した記事のリスト
        """
        articles_data = []
        driver = None
        try:
            # 1. Seleniumドライバーの初期化
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')  # 必要に応じてヘッドレス
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            # ChromeDriverのバージョン管理を改善
            driver_manager = ChromeDriverManager().install()
            
            service = ChromeService(executable_path=driver_manager)
            driver = webdriver.Chrome(
                service=service,
                options=options
            )
            driver.set_page_load_timeout(self.timeout)

            # 2. 対象URLを開く
            driver.get(url)

            # 3. 「もっと見る」ボタンをクリックして全記事をロード
            self._load_all_articles(driver)

            # 4. 最終的なページのHTMLを取得し、BeautifulSoupでパース
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')

            # 5. 記事一覧を探し出し、各記事をパース
            article_elements = self._find_articles(soup)
            for elem in article_elements:
                try:
                    article_data = self._parse_article(elem)
                    if article_data:
                        articles_data.append(article_data)
                except Exception as e:
                    self.logger.error(f"Failed to parse article: {str(e)}")
                    continue

        except Exception as e:
            self.logger.error(f"Failed to scrape PR Times: {str(e)}")
        finally:
            if driver:
                driver.quit()

        return articles_data

    def _load_all_articles(self, driver) -> None:
        """
        もっと見るボタンがある間クリックし続ける
        """
        while True:
            try:
                load_more_button = driver.find_element(By.CSS_SELECTOR, '[data-testid="load-more"]')
                load_more_button.click()
                time.sleep(1.5)  # ページ読み込み待ち
            except NoSuchElementException:
                # もっと見るボタンが見つからない -> 全部読み込み済
                break
            except ElementClickInterceptedException:
                # スクロールが必要な場合があるので、下へスクロールして再試行
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.0)
                continue

    def _find_articles(self, soup: BeautifulSoup) -> List[Any]:
        """
        「<ul data-testid="press-release-list">」の中にある
        「<article data-testid="release-item">」要素をすべて返す
        """
        container = soup.find('ul', {'data-testid': 'press-release-list'})
        if not container:
            return []

        return container.find_all('article', {'data-testid': 'release-item'})

    def _parse_article(self, article: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """
        個別の記事要素 (<article data-testid="release-item">) をパースして記事情報を抽出
        """
        try:
            # リンク (詳細ページURL)
            link_tag = article.find('a', class_='_wrapperLink_1xc1t_11')
            if not link_tag or not link_tag.get('href'):
                return None
            article_url = self.base_url + link_tag['href']

            # タイトル
            title_tag = article.find('h3', {'data-testid': 'release-title'})
            title_text = self._clean_text(title_tag.get_text()) if title_tag else None

            # 日時 (<time datetime="...")
            time_tag = article.find('time')
            published_at = None
            if time_tag and time_tag.has_attr('datetime'):
                # datetime属性からパース (2024-12-19T09:50:44+09:00 等)
                published_at_str = time_tag['datetime'].strip()
                published_at = self._parse_iso_date(published_at_str)
            elif time_tag:
                # テキストでもパース試みる
                published_at_str = time_tag.get_text(strip=True)
                published_at = self._parse_prtimes_date(published_at_str)

            # 会社名
            company_tag = article.find('a', class_='_infoCompany_1xc1t_36')
            company_name = self._clean_text(company_tag.get_text()) if company_tag else None

            # 画像URL (サムネイル)
            img_tag = article.find('img', class_='_thumbnail_1xc1t_17')
            image_url = img_tag['src'] if img_tag and img_tag.has_attr('src') else None

            return {
                'title': title_text,
                'url': article_url,
                'published_at': published_at,
                'company_name': company_name,
                'image_url': image_url,
                'source': 'prtimes'
            }
        except Exception as e:
            self.logger.error(f"Error parsing article: {str(e)}")
            return None

    def _parse_iso_date(self, date_str: str) -> Optional[datetime]:
        """
        例: 2024-12-19T09:50:44+09:00 形式の文字列を datetime にパース
        """
        try:
            # Python 3.11 以降なら zoneinfo も簡単に扱えますが、ここでは標準の strptime を想定
            # マイクロ秒が含まれる/含まれないなど細かい差異がある場合は dateutil を使うのも良いです
            from dateutil import parser
            return parser.parse(date_str)
        except Exception:
            return None

    def _parse_prtimes_date(self, date_str: str) -> Optional[datetime]:
        """
        例: '2024年12月19日 14時00分' のような文字列を解析
        """
        pattern = r'(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2})時(\d{1,2})分'
        match = re.search(pattern, date_str)
        if not match:
            return None

        try:
            year, month, day, hour, minute = map(int, match.groups())
            return datetime(year, month, day, hour, minute)
        except ValueError as e:
            self.logger.error(f"Error parsing date {date_str}: {str(e)}")
            return None

    def _clean_text(self, text: str) -> str:
        """
        テキストの前後空白を除去し、改行や連続空白を整形
        """
        if not text:
            return ""
        return " ".join(text.strip().split())
