# tests/test_firebase_client.py
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from src.data_access.firestore_client import FirestoreClient, ScrapingResult

@pytest.fixture
def mock_firestore_client(monkeypatch):
    """
    FirestoreClientのdbをモック化し、firestoreへの実アクセスを回避する
    """
    client = FirestoreClient()
    
    # dbオブジェクトをモックに差し替え
    mock_db = MagicMock()
    monkeypatch.setattr(client, "db", mock_db)

    return client, mock_db

def test_save_articles(mock_firestore_client):
    client, mock_db = mock_firestore_client

    articles = [
        {
            "title": "Test Article",
            "url": "http://example.com/test",
            "published_at": datetime.now(),
            "content": "Test content",
            "image_url": None,
            "source": "prtimes"
        }
    ]

    # 重複チェックをモック
    with patch.object(client, "_is_duplicate", return_value=False):
        doc_ids = client.save_articles(articles, "B23000199")
        assert len(doc_ids) == 1
        assert mock_db.batch().set.call_count == 1

def test_save_scraping_result(mock_firestore_client):
    client, mock_db = mock_firestore_client

    result = ScrapingResult(
        company_id="B23000199",
        source="prtimes",
        success=True,
        articles_count=5
    )
    client.save_scraping_result(result)
    assert mock_db.collection().document().set.call_count == 1

def test_is_duplicate(mock_firestore_client):
    client, mock_db = mock_firestore_client
    # モックの返り値（URL重複に対するクエリ結果など）を制御
    mock_stream = [MagicMock(), MagicMock()]  # stream() が2個返ってくる
    mock_db.collection().where().limit().get.return_value = mock_stream

    dup = client._is_duplicate("http://example.com/test")
    assert dup is True

def test_get_recent_articles(mock_firestore_client):
    client, mock_db = mock_firestore_client
    # stream のモック。ドキュメントの to_dict() が返すものを擬似的にセット
    mock_doc = MagicMock()
    mock_doc.id = "fake_id"
    mock_doc.to_dict.return_value = {
        "company_id": "B23000199",
        "title": "Recent Article",
        "url": "http://example.com/recent",
        "published_at": datetime.now() - timedelta(days=1),
        "content": "some content",
        "image_url": None,
        "source": "prtimes",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "status": "active"
    }
    mock_db.collection().where().where().where().order_by().limit().get.return_value = [mock_doc]

    articles = client.get_recent_articles(None, days=7)
    assert len(articles) == 1
    assert articles[0].title == "Recent Article"
