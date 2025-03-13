import os
import yaml
import logging
from datetime import datetime
import time
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# ▼ 修正: インポート先頭に src.をつける
from src.data_access.firestore_client import FirestoreClient
from src.data_access.models import ScrapingResult
from src.scrapers.prtimes_scraper import PRTimesScraper
from src.slack_bot.notifications import SlackNotifier

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
        config_path = os.path.join(os.path.dirname(__file__), 'configs/companies.yaml')
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

            self.notifier.notify_scraping_result(results)

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
        results = []
        company_name = company['name']
        logger.info(f"Processing company: {company_name}")

        if company.get('prtimes', {}).get('enabled', True):
            try:
                prtimes_url = company['prtimes']['url']
                scraper = PRTimesScraper()
                articles = scraper.get_news(prtimes_url)

                # Firestoreに保存 (URL重複はスキップ)
                saved_ids = self.db.save_articles(articles, company['id'])

                if saved_ids:
                    # 実際に保存された記事を抽出 (あるいは全件通知したいならこのままでもOK)
                    self.notifier.notify_new_articles(articles, company_name)

                results.append(ScrapingResult(
                    company_id=company['id'],
                    source='prtimes',
                    success=True,
                    articles_count=len(articles)
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
