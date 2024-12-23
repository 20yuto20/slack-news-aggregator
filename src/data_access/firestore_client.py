# src/data_access/firestore_client.py

from typing import List, Any, Dict, Optional
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore
import yaml
import os
import logging

from .models import Article, ScrapingResult

class FirestoreClient:
    """
    Firestore接続とデータ操作を行うクラス
    """

    def __init__(self):
        self._initialize_firebase()
        self.db = firestore.client()
        self.config = self._load_config()
        self.logger = logging.getLogger(__name__)

    def _initialize_firebase(self):
        """
        Firebase Admin SDKの初期化
        """
        if not firebase_admin.apps:
            cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if not cred_path:
                raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)

    def _load_config(self) -> Dict[str, Any]:
        """
        Firestore設定のファイル読み込み

        Returns:
            Dict[str, Any]: yamlファイルの中身
        """
        config_path = os.path.join(os.path.dirname(__file__), '../configs/firebase_config.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    # --------------------------------------------------------------------
    # 記事 (articles) 関連のメソッド
    # --------------------------------------------------------------------

    def save_articles(self, articles: List[Dict[str, Any]], company_id: str) -> List[str]:
        """
        新規記事をデータベースに保存する

        Args:
            articles (List[Dict[str, Any]]): 保存する記事 (dict形式)
            company_id (str): 企業ID

        Returns:
            List[str]: 保存した記事のドキュメントIDリスト
        """
        saved_ids = []
        batch = self.db.batch()
        collection = self.db.collection(self.config['collections']['articles']['name'])

        for article in articles:
            if not self._is_duplicate(article['url']):
                doc_ref = collection.document()
                article_data = {
                    'company_id': company_id,
                    'title': article['title'],
                    'url': article['url'],
                    'published_at': article['published_at'],
                    'content': article.get('content'),
                    'image_url': article.get('image_url'),
                    'source': article['source'],
                    'status': 'active',
                    'created_at': firestore.SERVER_TIMESTAMP,
                    'updated_at': firestore.SERVER_TIMESTAMP
                }
                batch.set(doc_ref, article_data)
                saved_ids.append(doc_ref.id)

        batch.commit()
        return saved_ids

    def _is_duplicate(self, url: str) -> bool:
        """
        記事のURLの重複チェック

        Args:
            url (str): チェックするURL

        Returns:
            bool: 重複している場合はTrue
        """
        articles = self.db.collection(self.config['collections']['articles']['name'])
        existing = articles.where('url', '==', url).limit(1).get()
        return len(existing) > 0

    def get_recent_articles(self, company_id: Optional[str] = None, days: int = 7, limit: int = 100) -> List[Article]:
        """
        指定期間内の記事を取得する

        Args:
            company_id (str): 企業ID（省略時は全企業）
            days (int): 取得する日数
            limit (int): 取得する最大件数

        Returns:
            List[Article]: 取得した記事をリストで返す
        """
        cutoff = datetime.now() - timedelta(days=days)
        articles_ref = self.db.collection(self.config['collections']['articles']['name'])

        query = articles_ref.where('status', '==', 'active').where('published_at', '>=', cutoff)

        if company_id:
            query = query.where('company_id', '==', company_id)

        query = query.order_by('published_at', direction=firestore.Query.DESCENDING).limit(limit)

        results = []
        for doc in query.get():
            data = doc.to_dict()
            results.append(Article(
                id=doc.id,
                company_id=data['company_id'],
                title=data['title'],
                url=data['url'],
                published_at=data['published_at'],
                content=data.get('content'),
                image_url=data.get('image_url'),
                source=data['source'],
                created_at=data.get('created_at'),
                updated_at=data.get('updated_at')
            ))

        return results

    def update_article_status(self, article_id: str, status: str):
        """
        記事のステータスを更新

        Args:
            article_id (str): 更新する記事のID
            status (str): 新しいステータス
        """
        article_ref = self.db.collection(self.config['collections']['articles']['name']).document(article_id)
        article_ref.update({
            'status': status,
            'updated_at': firestore.SERVER_TIMESTAMP
        })

    # --------------------------------------------------------------------
    # 企業 (companies) 関連のメソッド
    # --------------------------------------------------------------------

    def get_company_info(self, company_id: str) -> Optional[Dict[str, Any]]:
        """
        企業情報を取得する

        Args:
            company_id (str): 企業ID

        Returns:
            Optional[Dict[str, Any]]: 企業情報
        """
        companies = self.db.collection(self.config['collections']['companies']['name'])
        doc = companies.document(company_id).get()
        return doc.to_dict() if doc.exists else None

    def save_company_info(self, company_data: Dict[str, Any]):
        """
        企業情報を保存・更新

        Args:
            company_data (Dict[str, Any]): 保存する情報
        """
        companies = self.db.collection(self.config['collections']['companies']['name'])
        doc_ref = companies.document(company_data['company_id'])

        if doc_ref.get().exists:
            doc_ref.update({
                **company_data,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
        else:
            doc_ref.set({
                **company_data,
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            })

    # --------------------------------------------------------------------
    # スクレイピング結果 (scraping_results) 関連のメソッド
    # --------------------------------------------------------------------

    def save_scraping_result(self, result: ScrapingResult):
        """
        スクレイピング結果を保存
        """
        try:
            doc_ref = self.db.collection('scraping_results').document()
            doc_ref.set(result.to_dict())
        except Exception as e:
            self.logger.error(f"Error saving scraping result: {str(e)}")
            raise

    # --------------------------------------------------------------------
    # 統計情報 (stats) 用のメソッド
    # --------------------------------------------------------------------

    def get_total_articles_count(self) -> int:
        """
        全記事数を取得
        """
        articles_ref = self.db.collection(self.config['collections']['articles']['name'])
        docs = articles_ref.stream()
        return len(list(docs))

    def get_articles_count_by_company(self) -> Dict[str, int]:
        """
        企業IDごとの記事数を取得
        """
        counts = {}
        articles_ref = self.db.collection(self.config['collections']['articles']['name'])
        for doc in articles_ref.stream():
            data = doc.to_dict()
            cid = data.get('company_id', '')
            counts[cid] = counts.get(cid, 0) + 1
        return counts

    def get_articles_count_by_source(self) -> Dict[str, int]:
        """
        ソースごとの記事数を取得
        """
        counts = {}
        articles_ref = self.db.collection(self.config['collections']['articles']['name'])
        for doc in articles_ref.stream():
            data = doc.to_dict()
            source = data.get('source', '')
            counts[source] = counts.get(source, 0) + 1
        return counts

    def get_latest_articles(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        最新の記事を取得 (生のdictで返す)
        """
        articles_ref = self.db.collection(self.config['collections']['articles']['name'])
        query = (articles_ref
                 .order_by('published_at', direction=firestore.Query.DESCENDING)
                 .limit(limit))

        docs = query.get()
        results = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            results.append(data)
        return results
