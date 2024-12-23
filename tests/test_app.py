# tests/test_app.py
import pytest
from src.app import app

@pytest.fixture
def client():
    # Flaskのテストクライアント
    with app.test_client() as client:
        yield client

def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "healthy"

def test_stats_endpoint(client, monkeypatch):
    mock_data = {
        "total_articles": 100,
        "articles_by_company": {"B23000199": 50},
        "articles_by_source": {"prtimes": 50},
        "latest_articles": []
    }
    # FirestoreClient のインスタンス化をモックして、 get_stats() が常に mock_data を返すように
    def mock_init(*args, **kwargs):
        pass

    class MockFirestoreClient:
        def get_total_articles_count(self):
            return 100
        def get_articles_count_by_company(self):
            return {"B23000199": 50}
        def get_articles_count_by_source(self):
            return {"prtimes": 50}
        def get_latest_articles(self, limit=5):
            return []

    monkeypatch.setattr("src.app.FirestoreClient.__init__", mock_init)
    monkeypatch.setattr("src.app.FirestoreClient", MockFirestoreClient)

    response = client.get("/stats")
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["total_articles"] == 100

def test_run_scraping_endpoint(client, monkeypatch):
    def mock_run(*args, **kwargs):
        pass

    class MockCollector:
        def run(self):
            return mock_run()

    monkeypatch.setattr("src.app.NewsCollector", MockCollector)
    response = client.get("/run")
    assert response.status_code == 200
    assert response.get_json()["status"] == "success"
