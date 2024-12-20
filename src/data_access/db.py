from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from google.cloud import firestore
from firebase_admin import firestore as admin_firestore
import logging
from .models import Article, Company, ScrapingResult

class DatabaseManager:
    """
    データベース操作を管理するクラス
    Firestoreへのアクセスを抽象化し、高レベルなデータ操作インターフェースを提供
    """

    def __init__(self):
        self.db = admin_firestore.client()
        self.logger = logging.getLogger(__name__)

    def save_article(self, article: Article) -> str:
        """
        記事を保存

        Args:
            article: 保存する記事

        Returns:
            str: 保存した記事のドキュメントID
        """
        try:
            # URLの重複チェック
            if self._is_duplicate_article(article.url):
                self.logger.info(f"Duplicate article found: {article.url}")
                return ""

            # 記事データの作成
            doc_ref = self.db.collection('articles').document()
            doc_ref.set(article.to_dict())
            
            return doc_ref.id

        except Exception as e:
            self.logger.error(f"Error saving article: {str(e)}")
            raise

    def save_articles_batch(self, articles: List[Article]) -> List[str]:
        """
        複数の記事をバッチで保存

        Args:
            articles: 保存する記事のリスト

        Returns:
            List[str]: 保存した記事のドキュメントIDリスト
        """
        batch = self.db.batch()
        saved_ids = []

        try:
            for article in articles:
                if self._is_duplicate_article(article.url):
                    continue

                doc_ref = self.db.collection('articles').document()
                batch.set(doc_ref, article.to_dict())
                saved_ids.append(doc_ref.id)

            batch.commit()
            return saved_ids

        except Exception as e:
            self.logger.error(f"Error saving articles batch: {str(e)}")
            raise

    def get_recent_articles(
        self,
        company_id: Optional[str] = None,
        days: int = 7,
        limit: int = 100
    ) -> List[Article]:
        """
        最近の記事を取得

        Args:
            company_id: 企業ID（省略時は全企業）
            days: 取得する日数
            limit: 取得する最大件数

        Returns:
            List[Article]: 取得した記事のリスト
        """
        try:
            cutoff = datetime.now() - timedelta(days=days)
            query = self.db.collection('articles')
            
            if company_id:
                query = query.where('company_id', '==', company_id)
                
            query = (query
                    .where('status', '==', 'active')
                    .where('published_at', '>=', cutoff)
                    .order_by('published_at', direction=firestore.Query.DESCENDING)
                    .limit(limit))

            articles = []
            for doc in query.stream():
                data = doc.to_dict()
                data['id'] = doc.id
                articles.append(Article.from_dict(data))

            return articles

        except Exception as e:
            self.logger.error(f"Error getting recent articles: {str(e)}")
            raise

    def save_company(self, company: Company) -> str:
        """
        企業情報を保存

        Args:
            company: 保存する企業情報

        Returns:
            str: 保存した企業のドキュメントID
        """
        try:
            doc_ref = self.db.collection('companies').document(company.id)
            doc_ref.set(company.to_dict())
            return doc_ref.id

        except Exception as e:
            self.logger.error(f"Error saving company: {str(e)}")
            raise

    def get_company(self, company_id: str) -> Optional[Company]:
        """
        企業情報を取得

        Args:
            company_id: 企業ID

        Returns:
            Company: 取得した企業情報
        """
        try:
            doc = self.db.collection('companies').document(company_id).get()
            if not doc.exists:
                return None

            data = doc.to_dict()
            data['id'] = doc.id
            return Company.from_dict(data)

        except Exception as e:
            self.logger.error(f"Error getting company: {str(e)}")
            raise

    def get_all_companies(self) -> List[Company]:
        """
        全企業情報を取得

        Returns:
            List[Company]: 全企業のリスト
        """
        try:
            companies = []
            for doc in self.db.collection('companies').stream():
                data = doc.to_dict()
                data['id'] = doc.id
                companies.append(Company.from_dict(data))

            return companies

        except Exception as e:
            self.logger.error(f"Error getting all companies: {str(e)}")
            raise

    def save_scraping_result(self, result: ScrapingResult):
        """
        スクレイピング結果を保存

        Args:
            result: 保存するスクレイピング結果
        """
        try:
            doc_ref = self.db.collection('scraping_results').document()
            doc_ref.set(result.to_dict())

        except Exception as e:
            self.logger.error(f"Error saving scraping result: {str(e)}")
            raise

    def _is_duplicate_article(self, url: str) -> bool:
        """
        記事URLの重複チェック

        Args:
            url: チェックするURL

        Returns:
            bool: 重複している場合True
        """
        docs = (self.db.collection('articles')
               .where('url', '==', url)
               .limit(1)
               .stream())
        return len(list(docs)) > 0

    def get_articles_stats(self) -> Dict[str, Any]:
        """
        記事の統計情報を取得

        Returns:
            Dict: 統計情報
        """
        try:
            stats = {
                'total_count': 0,
                'by_company': {},
                'by_source': {},
                'by_month': {}
            }

            articles = self.db.collection('articles').stream()
            for doc in articles:
                data = doc.to_dict()
                stats['total_count'] += 1
                
                # 企業別集計
                company_id = data.get('company_id')
                stats['by_company'][company_id] = stats['by_company'].get(company_id, 0) + 1
                
                # ソース別集計
                source = data.get('source')
                stats['by_source'][source] = stats['by_source'].get(source, 0) + 1
                
                # 月別集計
                if 'published_at' in data:
                    month = data['published_at'].strftime('%Y-%m')
                    stats['by_month'][month] = stats['by_month'].get(month, 0) + 1

            return stats

        except Exception as e:
            self.logger.error(f"Error getting articles stats: {str(e)}")
            raise