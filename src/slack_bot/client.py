from typing import Dict, Any, Optional, List
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import logging
import os
import yaml
from pathlib import Path
from ..utils.config_loader import load_config

class SlackClient:
    """
    SlackクライアントクラスはSlack APIとの通信を担当
    WebClientのラッパーとして機能し、エラーハンドリングと再試行ロジックを提供
    """

    def __init__(self):
        self.config = self._load_slack_config()
        self.client = WebClient(token=self._get_bot_token())
        self.logger = logging.getLogger(__name__)
        self.channel = self.config.get('default_channel')
        self.retry_count = 3
        self.retry_delay = 1  # seconds

    def _load_slack_config(self) -> Dict[str, Any]:
        """Slack設定を読み込む"""
        env = os.getenv('ENVIRONMENT', 'development')
        config = load_config('slack_config.yaml')
        return config[env]

    def _get_bot_token(self) -> str:
        """
        Slack Bot Tokenを取得
        """
        if os.getenv('ENVIRONMENT') == 'production':
            from google.cloud import secretmanager
            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{os.getenv('PROJECT_ID')}/secrets/slack-bot-token/versions/latest"
            response = client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        return os.getenv('SLACK_BOT_TOKEN', self.config['bot_token'])

    def send_message(
        self, 
        text: str, 
        channel: Optional[str] = None, 
        blocks: Optional[List[Dict[str, Any]]] = None,
        thread_ts: Optional[str] = None
    ):
        """
        メッセージを送信する (同期処理)
        """
        channel = channel or self.channel
        retry_count = self.retry_count

        while retry_count > 0:
            try:
                return self.client.chat_postMessage(
                    channel=channel,
                    text=text,
                    blocks=blocks,
                    thread_ts=thread_ts
                )
            except SlackApiError as e:
                self.logger.error(f"Error sending message: {str(e)}")
                retry_count -= 1
                if retry_count > 0:
                    import time
                    time.sleep(self.retry_delay)
                else:
                    raise

    def update_message(
        self,
        channel: str,
        ts: str,
        text: Optional[str] = None,
        blocks: Optional[List[Dict[str, Any]]] = None
    ):
        """
        既存のメッセージを更新する (同期処理)
        """
        try:
            return self.client.chat_update(
                channel=channel,
                ts=ts,
                text=text,
                blocks=blocks
            )
        except SlackApiError as e:
            self.logger.error(f"Error updating message: {str(e)}")
            raise

    def get_channel_id(self, channel_name: str) -> Optional[str]:
        """
        チャンネル名からチャンネルIDを取得 (同期処理)
        """
        try:
            response = self.client.conversations_list()
            for channel in response['channels']:
                if channel['name'] == channel_name:
                    return channel['id']
            return None
        except SlackApiError as e:
            self.logger.error(f"Error getting channel ID: {str(e)}")
            return None

    def get_thread_messages(
        self,
        channel: str,
        thread_ts: str
    ) -> List[Dict[str, Any]]:
        """
        スレッド内のメッセージを取得 (同期処理)
        """
        try:
            response = self.client.conversations_replies(
                channel=channel,
                ts=thread_ts
            )
            return response['messages']
        except SlackApiError as e:
            self.logger.error(f"Error getting thread messages: {str(e)}")
            return []

    def add_reaction(
        self,
        channel: str,
        timestamp: str,
        reaction: str
    ) -> None:
        """
        メッセージにリアクションを追加 (同期処理)
        """
        try:
            self.client.reactions_add(
                channel=channel,
                timestamp=timestamp,
                name=reaction.strip(':')
            )
        except SlackApiError as e:
            self.logger.error(f"Error adding reaction: {str(e)}")

    def is_valid_channel(self, channel: str) -> bool:
        """
        チャンネルが有効かを確認
        """
        try:
            self.client.conversations_info(channel=channel)
            return True
        except SlackApiError:
            return False
