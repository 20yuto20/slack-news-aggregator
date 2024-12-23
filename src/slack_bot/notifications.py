from typing import List, Dict, Any, Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import yaml
import os
from datetime import datetime
import logging
from ..data_access.models import Article, ScrapingResult

class SlackNotifier:
    """Slack通知を管理するクラス"""

    def __init__(self):
        self.config = self._load_config()
        self.client = WebClient(token=self._get_bot_token())
        self.logger = logging.getLogger(__name__)

    def _load_config(self) -> Dict[str, Any]:
        """
        Slack設定ファイルを読み込む
        """
        config_path = os.path.join(os.path.dirname(__file__), '../configs/slack_config.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            env = os.getenv('ENVIRONMENT', 'development')
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
        return self.config['bot_token']

    def notify_new_articles(self, articles: List[Dict[str, Any]], company_name: str):
        """
        新規記事をSlackに通知
        """
        if not articles:
            return

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🆕 {company_name}の新着記事 ({len(articles)}件)"
                }
            },
            {"type": "divider"}
        ]

        for article in articles:
            published_at_str = ""
            if 'published_at' in article and isinstance(article['published_at'], datetime):
                published_at_str = article['published_at'].strftime('%Y年%m月%d日 %H:%M')

            blocks.extend([
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"*<{article['url']}|{article['title']}>*\n"
                            f"📅 {published_at_str}\n"
                            f"📰 {article['source'].upper()}"
                        )
                    }
                },
                {"type": "divider"}
            ])

        try:
            self.client.chat_postMessage(
                channel=self.config['default_channel'],
                blocks=blocks
            )
        except SlackApiError as e:
            self.logger.error(f"Failed to send Slack notification: {str(e)}")

    def notify_scraping_result(self, results: List[ScrapingResult]):
        """
        スクレイピング実行結果を通知
        """
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🤖 スクレイピング実行結果"
                }
            },
            {"type": "divider"}
        ]

        success_count = sum(1 for r in results if r.success)
        fail_count = len(results) - success_count
        total_articles = sum(r.articles_count for r in results)

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*実行結果サマリー*\n"
                    f"✅ 成功: {success_count}件\n"
                    f"❌ 失敗: {fail_count}件\n"
                    f"📄 取得記事数: {total_articles}件\n"
                    f"🕒 実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
            }
        })

        if fail_count > 0:
            error_text = "*エラー詳細:*\n"
            for result in results:
                if not result.success:
                    error_text += f"• {result.company_id} ({result.source}): {result.error_message}\n"

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": error_text
                }
            })

        try:
            self.client.chat_postMessage(
                channel=self.config['default_channel'],
                blocks=blocks
            )
        except SlackApiError as e:
            self.logger.error(f"Failed to send Slack notification: {str(e)}")

    def notify_error(self, error_message: str, error_detail: Optional[str] = None):
        """
        エラーを通知
        """
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "⚠️ エラーが発生しました"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*エラー内容:*\n{error_message}"
                }
            }
        ]

        if error_detail:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*詳細:*\n```{error_detail}```"
                }
            })

        try:
            self.client.chat_postMessage(
                channel=self.config['default_channel'],
                blocks=blocks,
                attachments=[{
                    "color": self.config['notification']['error_color'],
                    "footer": f"発生時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }]
            )
        except SlackApiError as e:
            self.logger.error(f"Failed to send error notification: {str(e)}")
