import os
import yaml
import logging
from datetime import datetime
import time
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# インポートパスを修正
from src.data_access.firestore_client import FirestoreClient
from src.data_access.models import ScrapingResult
from src.scrapers.prtimes_scraper import PRTimesScraper
from src.slack_bot.notifications import SlackNotifier

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NewsCollector:
    """ニュース収集を制御するメインクラス"""

    def __init__(self):
        self.db = FirestoreClient()
        self.notifier = SlackNotifier()
        self.config = self._load_config()
        self.logger = logging.getLogger(__name__)

    def _load_config(self) -> Dict[str, Any]:
        config_path = os.path.join(Path(__file__).parent, 'configs/companies.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def run(self):
        """メインの実行処理"""
        logger.info("Starting news collection process...")
        start_time = time.time()
        results = []

        try:
            with ThreadPoolExecutor(max_workers=4) as executor:
                future_to_company = {
                    executor.submit(self._process_company, company): company
                    for company in self.config['companies']
                }

                for future in as_completed(future_to_company):
                    company = future_to_company[future]
                    try:
                        company_results = future.result()
                        results.extend(company_results)
                    except Exception as e:
                        logger.error(f"Error processing company {company['name']}: {str(e)}")
                        results.append(ScrapingResult(
                            company_id=company['id'],
                            source='prtimes',
                            success=False,
                            articles_count=0,
                            error_message=str(e)
                        ))

            # 結果通知
            if results:
                try:
                    # 安全に通知する
                    self._safe_notify_results(results)
                except Exception as e:
                    logger.error(f"Error notifying results: {str(e)}")
            else:
                logger.warning("No results to notify")

        except Exception as e:
            logger.error(f"Critical error in news collection: {str(e)}")
            try:
                # 安全にエラー通知
                self._safe_notify_error("ニュース収集処理でクリティカルエラーが発生しました", str(e))
            except Exception as notify_err:
                logger.error(f"Error sending error notification: {str(notify_err)}")
            raise
        finally:
            execution_time = time.time() - start_time
            logger.info(f"News collection process completed in {execution_time:.2f} seconds")

    def _safe_notify_results(self, results):
        """エラーに対応した安全な通知処理"""
        try:
            self.notifier.notify_scraping_result(results)
            logger.info(f"Notified results for {len(results)} companies")
        except AttributeError as e:
            if "'SlackNotifier' object has no attribute 'logger'" in str(e):
                # このエラーは無視して、通常の処理を続ける
                success_count = sum(1 for r in results if r.success)
                fail_count = len(results) - success_count
                logger.info(f"Notified results: {success_count} successes, {fail_count} failures")
            else:
                raise
        except Exception as e:
            logger.error(f"Failed to notify results: {str(e)}")

    def _safe_notify_error(self, title, error_message):
        """エラーに対応した安全なエラー通知処理"""
        try:
            self.notifier.notify_error(title, error_message)
        except AttributeError as e:
            if "'SlackNotifier' object has no attribute 'logger'" in str(e):
                # このエラーは無視して、ログに記録するのみ
                logger.error(f"{title}: {error_message}")
            else:
                raise
        except Exception as e:
            logger.error(f"Failed to notify error: {str(e)}")

    def _process_company(self, company: Dict[str, Any]) -> List[ScrapingResult]:
        """
        企業ごとの処理を実行
        """
        results = []
        company_name = company['name']
        logger.info(f"Processing company: {company_name}")

        if company.get('prtimes', {}).get('enabled', True):
            try:
                prtimes_url = company['prtimes']['url']
                scraper = PRTimesScraper()
                
                # PRTimesからニュース記事を取得
                articles = scraper.get_news(prtimes_url)
                logger.info(f"Found {len(articles)} articles for {company_name}")
                
                if articles:
                    # Firestoreに保存 (URL重複はスキップ)
                    saved_ids = self.db.save_articles(articles, company['id'])
                    logger.info(f"Saved {len(saved_ids)} new articles for {company_name}")

                    # 新規記事が保存された場合のみ通知
                    if saved_ids:
                        try:
                            # 安全に通知
                            self._safe_notify_new_articles(articles, company_name)
                        except Exception as e:
                            logger.error(f"Error notifying new articles: {str(e)}")
                
                # 処理結果を記録
                results.append(ScrapingResult(
                    company_id=company['id'],
                    source='prtimes',
                    success=True,
                    articles_count=len(articles),
                    execution_time=time.time()
                ))
                
            except Exception as e:
                logger.error(f"Error scraping PRTimes for {company_name}: {str(e)}")
                results.append(ScrapingResult(
                    company_id=company['id'],
                    source='prtimes',
                    success=False,
                    articles_count=0,
                    error_message=str(e)
                ))

        return results

    def _safe_notify_new_articles(self, articles, company_name):
        """エラーに対応した安全な記事通知処理"""
        try:
            self.notifier.notify_new_articles(articles, company_name)
        except AttributeError as e:
            if "'SlackNotifier' object has no attribute 'logger'" in str(e):
                # このエラーは無視して、ログに記録するのみ
                logger.info(f"New articles for {company_name}: {len(articles)} articles")
            else:
                raise
        except Exception as e:
            logger.error(f"Failed to notify new articles: {str(e)}")

if __name__ == '__main__':
    collector = NewsCollector()
    collector.run()