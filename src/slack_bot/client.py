from typing import Dict, Any, Optional, List
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import logging
import os
import yaml
from pathlib import Path

class SlackClient:
    """
    SlackクライアントクラスはSlack APIとの通信を担当
    WebClientのラッパーとして機能し、エラーハンドリングと再試行ロジックを提供
    """

    def __init__(self):
        self.config = self._load_slack_config()
        self.token = self._get_bot_token()
        self.client = WebClient(token=self.token, base_url="https://slack.com/api/")
        self.logger = logging.getLogger(__name__)
        self.channel = self.config.get('default_channel')
        self.retry_count = 3
        self.retry_delay = 1  # seconds

    def _load_slack_config(self) -> Dict[str, Any]:
        """Slack設定を読み込む"""
        env = os.getenv('ENVIRONMENT', 'development')
        try:
            config_path = os.path.join(Path(__file__).parent.parent, 'configs/slack_config.yaml')
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config[env]
        except Exception as e:
            self.logger.error(f"Failed to load slack config: {e}")
            # フォールバック設定を環境変数から直接読み込む
            return {
                'signing_secret': os.environ.get('SLACK_SIGNING_SECRET', ''),
                'bot_token': os.environ.get('SLACK_BOT_TOKEN', ''),
                'default_channel': os.environ.get('SLACK_DEFAULT_CHANNEL', '#news-prod'),
                'notification': {
                    'success_color': "#36a64f",
                    'warning_color': "#ff9900",
                    'error_color': "#dc3545"
                }
            }

    def _get_bot_token(self) -> str:
        """
        Slack Bot Tokenを取得
        """
        # 環境変数から直接BOT_TOKENを取得
        token = os.getenv('SLACK_BOT_TOKEN')
        if token:
            self.logger.info(f"Using token from env var starting with: {token[:4]}..." if len(token) > 4 else "Token is too short!")
            return token
            
        # 環境変数に無い場合はconfigからのトークンを使用
        token = self.config.get('bot_token', '')
        # ${SLACK_BOT_TOKEN}形式の場合、環境変数から展開
        if token and token.startswith('${') and token.endswith('}'):
            env_var = token[2:-1]
            token = os.getenv(env_var, '')
            
        if not token:
            self.logger.error("Slack token is empty or not found!")
        
        return token

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

        # 環境変数BOT_TOKENをチェック (デバッグ用)
        token = os.getenv('SLACK_BOT_TOKEN', 'TOKEN_NOT_SET')
        self.logger.info(f"Using token starting with: {token[:4]}***" if len(token) > 4 else "Token is too short or not set!")

        while retry_count > 0:
            try:
                return self.client.chat_postMessage(
                    channel=channel,
                    text=text,
                    blocks=blocks,
                    thread_ts=thread_ts
                )
            except SlackApiError as e:
                error_msg = f"Error sending message: {str(e)}, Response: {e.response.data if hasattr(e, 'response') else 'No response data'}"
                self.logger.error(error_msg)
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

    def test_connection(self) -> bool:
        """
        Slack接続をテスト
        """
        try:
            response = self.client.api_test()
            return response['ok']
        except Exception as e:
            self.logger.error(f"Slack connection test failed: {str(e)}")
            return False