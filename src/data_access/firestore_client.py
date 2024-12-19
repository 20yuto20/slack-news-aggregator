from typing import List, Any, Dict, Optional
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore
import yaml
import os
from .models import Article

class FirestoreClient:
    """
    Firestore接続とデータ操作をするクラス
    """
    def __init__(self):
        self.__initialize__firebase()
        self.db = firestore.client()
        self.config = self.__load__config()

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

    def __load__config(self) -> Dict[str, Any]:
        """
        Firestore設定のファイル読み込み
        Returns:
            Dict[str, Any]: yamlファイルの中身
        """
        config_path = os.path.join(os.path.dirname(__file__), '../configs/firebase_config.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def save_articles(self, articles: List[Dict[str, Any]], company_id: str) -> List[str]:
        """
        新規記事をデータベースに保存する

        Args:
            articles (List[Dict[str, Any]]): 保存する記事
            company_id (str): 企業ID（社内）

        Returns:
            List[str]: 保存した記事のドキュメントIDリスト
        """
        saved_id = []
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
        return saved_id
    
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
        return len(list(exisiting)) > 0

    def get_recent_articles(self, company_id: str, days: int = 7) -> List[Article]:
        """
        指定期間内の記事を取得する

        Args:
            company_id (str): 企業ID（社内）
            days (int, optional): 取得する日数

        Returns:
            List[Article]: 取得した記事をリストで返す
        """
        cutoff = datetime.now() - timedelta(days=days)
        articles = self.db.collection(self.config['collections']['articles']['name'])
        query = (
            articles
            .where('company_id', '==', company_id)
            .where('published_at', '>=', cutoff)
            .where('status', '==', 'active')
            .where('published_at', direction=firestore.Query.DESCENDING)
        )

        results = []
        for doc in query.get():
            data = doc.to_dict()
            result.append(Article(
                id=doc.id,
                company_id=data['company_id'],
                title=data['title'],
                url=data['url'],
                published_at=data['published_at'],
                content=data.get('content'),
                image_url=data.get('image_url'),
                source=data['source'],
                created_at=data['created_at'],
                updated_at=data['updated_at']
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
            'updated_at': firestore.SEVER_TIMESTAMP
        })

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
            doc_ref.upadate({
                **company_data,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
        else:
            doc_ref.set({
                **company_data,
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            })