# tests/test_run_script.py
import pytest
from unittest.mock import patch, MagicMock
from src.run_script import NewsCollector
from src.data_access.models import ScrapingResult

@pytest.fixture
def mock_collector(monkeypatch):
    collector = NewsCollector()
    mock_db = MagicMock()
    monkeypatch.setattr(collector, "db", mock_db)
    mock_notifier = MagicMock()
    monkeypatch.setattr(collector, "notifier", mock_notifier)
    return collector, mock_db, mock_notifier

def test_run_successful(mock_collector):
    collector, mock_db, mock_notifier = mock_collector

    # config の companies.yaml を読み込み済みとして扱う
    collector.config = {
        "companies": [
            {"id": "B23000199", "name": "TestCompany", "prtimes": {"url": "https://test.com", "enabled": True}}
        ]
    }

    with patch("src.scrapers.prtimes_scraper.PRTimesScraper.get_news", return_value=[
        {"title": "Article1", "url": "http://example.com/1", "published_at": None, "source": "prtimes"}
    ]):
        mock_db.save_articles.return_value = ["fake_doc_id"]
        
        collector.run()
        # スクレイピング結果通知が呼ばれたか
        assert mock_notifier.notify_scraping_result.call_count == 1

def test_process_company_disabled_scraping(mock_collector):
    collector, mock_db, mock_notifier = mock_collector
    company = {"id": "B99999999", "name": "DisabledCorp", "prtimes": {"enabled": False}}
    # prtimes が disabled の場合、ScrapingResult 0件で success=True / articles_count=0のまま返す
    results = collector._process_company(company)
    assert len(results) == 0, "enabled=Falseの場合はスクレイピングを実行しない"
