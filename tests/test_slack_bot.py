# tests/test_slack_bot.py
import pytest
from unittest.mock import patch, MagicMock
from src.slack_bot.client import SlackClient
from src.slack_bot.handlers import SlackEventHandler

@pytest.fixture
def mock_slack_client(monkeypatch):
    # SlackClient のWebClientをモック化
    client = SlackClient()
    mock_web_client = MagicMock()
    monkeypatch.setattr(client, "client", mock_web_client)
    return client, mock_web_client

def test_send_message(mock_slack_client):
    client, mock_web_client = mock_slack_client
    client.send_message("Hello test", "#test")
    mock_web_client.chat_postMessage.assert_called_once()

def test_handle_mention_help():
    # handlersはSlackのイベントを受け取り、特定のコマンド文字列に応じて動作
    web_client = MagicMock()
    handler = SlackEventHandler(web_client)
    event = {
        "type": "app_mention",
        "text": "<@BOTID> help",
        "channel": "C12345"
    }

    handler.handle_mention(event)
    web_client.chat_postMessage.assert_called()

def test_handle_mention_recent():
    web_client = MagicMock()
    handler = SlackEventHandler(web_client)
    event = {
        "type": "app_mention",
        "text": "<@BOTID> recent 10days",
        "channel": "C12345"
    }

    with patch.object(handler.db, "get_recent_articles", return_value=[]):
        handler.handle_mention(event)
    # get_recent_articles が呼ばれているか確認
    handler.db.get_recent_articles.assert_called_with(None, 10)

def test_handle_mention_invalid():
    web_client = MagicMock()
    handler = SlackEventHandler(web_client)
    event = {
        "type": "app_mention",
        "text": "<@BOTID> something random",
        "channel": "C12345"
    }
    handler.handle_mention(event)
    # 「help」を表示するパスに入るはず
    web_client.chat_postMessage.assert_called()
