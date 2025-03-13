from typing import List, Dict, Any, Optional
from datetime import datetime
import re
import time
import logging

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

from bs4 import BeautifulSoup
from .base_scraper import BaseScraper


class PRTimesScraper(BaseScraper):
    """
    PRTimes専用のスクレイパークラス (Selenium版) - 2025年3月版
    """

    def __init__(self, timeout: int = 30, retry: int = 3):
        super().__init__(timeout, retry)
        self.base_url = "https://prtimes.jp"
        self.logger = logging.getLogger(__name__)

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
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            # ChromeDriverのバージョン管理を改善
            driver_manager = ChromeDriverManager().install()
            
            service = ChromeService(executable_path=driver_manager)
            driver = webdriver.Chrome(
                service=service,
                options=options
            )
            driver.set_page_load_timeout(self.timeout)

            # 2. 対象URLを開く
            self.logger.info(f"Opening URL: {url}")
            driver.get(url)
            time.sleep(3)  # ページ読み込み待ち

            # 3. 「もっと見る」ボタンをクリックして全記事をロード
            self._load_all_articles(driver)

            # 4. 最終的なページのHTMLを取得し、BeautifulSoupでパース
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')

            # 5. 記事一覧を探し出し、各記事をパース
            article_elements = self._find_articles(soup)
            self.logger.info(f"Found {len(article_elements)} article elements")
            
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
        try:
            # 初回のload-moreの検出を待つ
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="load-more"]'))
            )
        except TimeoutException:
            self.logger.info("No 'load more' button found, only showing initial articles")
            return
        
        max_clicks = 10  # 安全のために最大クリック回数を制限
        click_count = 0
        
        while click_count < max_clicks:
            try:
                # スクロールして「もっと見る」ボタンを表示
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight - 500);")
                time.sleep(1)
                
                # ボタンを探して押す
                load_more_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="load-more"]'))
                )
                
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", load_more_button)
                time.sleep(0.5)
                
                self.logger.info(f"Clicking 'load more' button (attempt {click_count + 1})")
                driver.execute_script("arguments[0].click();", load_more_button)
                click_count += 1
                time.sleep(2)  # ページ読み込み待ち
                
            except TimeoutException:
                self.logger.info("No more 'load more' button found - all content loaded")
                break
            except ElementClickInterceptedException:
                self.logger.warning("Click intercepted, trying to scroll and retry")
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                continue
            except Exception as e:
                self.logger.error(f"Error clicking 'load more' button: {str(e)}")
                break

    def _find_articles(self, soup: BeautifulSoup) -> List[Any]:
        """
        「<ul data-testid="press-release-list">」の中にある
        「<article data-testid="release-item">」要素をすべて返す
        """
        container = soup.find('ul', {'data-testid': 'press-release-list'})
        if not container:
            self.logger.warning("Could not find article container with data-testid='press-release-list'")
            return []

        articles = container.find_all('article', {'data-testid': 'release-item'})
        return articles

    def _parse_article(self, article: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """
        個別の記事要素 (<article data-testid="release-item">) をパースして記事情報を抽出
        """
        try:
            # リンク (詳細ページURL)
            link_tag = article.find('a', class_='_wrapperLink')
            if not link_tag:
                # クラス名の先頭部分で検索する（数字部分が変わる可能性があるため）
                link_tag = article.find('a', class_=lambda x: x and x.startswith('_wrapperLink'))
            
            if not link_tag or not link_tag.get('href'):
                return None
                
            article_url = self.base_url + link_tag['href']

            # タイトル
            title_tag = article.find('h2', {'data-testid': 'release-title'})
            if not title_tag:
                # h3タグの場合もある
                title_tag = article.find(['h2', 'h3'], {'data-testid': 'release-title'})
                
            title_text = self._clean_text(title_tag.get_text()) if title_tag else "No title found"

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
            company_tag = article.find('a', class_=lambda x: x and x.startswith('_infoCompany'))
            company_name = self._clean_text(company_tag.get_text()) if company_tag else None

            # 画像URL (サムネイル)
            img_tag = article.find('img', class_=lambda x: x and x.startswith('_thumbnail'))
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
        except Exception as e:
            self.logger.error(f"Error parsing ISO date '{date_str}': {str(e)}")
            return None

    def _parse_prtimes_date(self, date_str: str) -> Optional[datetime]:
        """
        例: '2025年3月6日 10時00分' のような文字列を解析
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