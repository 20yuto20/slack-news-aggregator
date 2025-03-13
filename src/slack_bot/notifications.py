from typing import List, Dict, Any, Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import yaml
import os
from datetime import datetime
import logging
from pathlib import Path
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
        config_path = os.path.join(Path(__file__).parent.parent, 'configs/slack_config.yaml')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                env = os.getenv('ENVIRONMENT', 'development')
                return config[env]
        except Exception as e:
            self.logger.error(f"Failed to load slack config: {e}")
            # フォールバック設定を返す
            return {
                'bot_token': os.environ.get('SLACK_BOT_TOKEN', ''),
                'signing_secret': os.environ.get('SLACK_SIGNING_SECRET', ''),
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
            return token
            
        # 環境変数に無い場合はconfigからのトークンを使用
        token = self.config.get('bot_token', '')
        # ${SLACK_BOT_TOKEN}形式の場合、環境変数から展開
        if token and token.startswith('${') and token.endswith('}'):
            env_var = token[2:-1]
            return os.getenv(env_var, '')
            
        return token

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
            if 'published_at' in article and article['published_at']:
                if isinstance(article['published_at'], datetime):
                    published_at_str = article['published_at'].strftime('%Y年%m月%d日 %H:%M')
                else:
                    # 文字列の場合はそのまま
                    published_at_str = str(article['published_at'])

            blocks.extend([
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"*<{article.get('url', '#')}|{article.get('title', 'No Title')}>*\n"
                            f"📅 {published_at_str}\n"
                            f"📰 {article.get('source', 'unknown').upper()}"
                        )
                    }
                },
                {"type": "divider"}
            ])

        try:
            self.client.chat_postMessage(
                channel=self.config.get('default_channel', '#news-alerts'),
                blocks=blocks
            )
            self.logger.info(f"Sent notification for {len(articles)} new articles")
        except SlackApiError as e:
            self.logger.error(f"Failed to send Slack notification: {str(e)}")

    def notify_scraping_result(self, results: List[ScrapingResult]):
        """
        スクレイピング実行結果を通知
        """
        if not results:
            self.logger.warning("No results to notify")
            return
            
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
                    error_text += f"• {result.company_id} ({result.source}): {result.error_message or 'Unknown error'}\n"

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",