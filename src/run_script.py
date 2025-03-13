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
                self.notifier.notify_scraping_result(results)
                logger.info(f"Notified results for {len(results)} companies")
            else:
                logger.warning("No results to notify")

        except Exception as e:
            logger.error(f"Critical error in news collection: {str(e)}")
            self.notifier.notify_error(
                "ニュース収集処理でクリティカルエラーが発生しました",
                str(e)
            )
            raise
        finally:
            execution_time = time.time() - start_time
            logger.info(f"News collection process completed in {execution_time:.2f} seconds")

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
                        self.notifier.notify_new_articles(articles, company_name)
                
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

if __name__ == '__main__':
    collector = NewsCollector()
    collector.run()