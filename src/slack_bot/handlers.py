from typing import Dict, Any, List
from slack_sdk.web import WebClient
from slack_sdk.errors import SlackApiError
import logging
import re
from datetime import datetime, timedelta
from ..data_access.firestore_client import FirestoreClient
from ..data_access.models import Article

class SlackEventHandler:
    """Slackイベントを処理するハンドラクラス"""

    def __init__(self, client: WebClient):
        self.client = client
        self.db = FirestoreClient()
        self.logger = logging.getLogger(__name__)

    def handle_mention(self, event: Dict[str, Any]):
        """
        メンション(@)を処理 (同期的に動作)
        """
        try:
            text = event.get('text', '').lower()
            bot_id = event.get('bot_id')
            if bot_id:
                text = text.replace(f"<@{bot_id}>", "").strip()

            # コマンドを解析
            if "help" in text or "ヘルプ" in text:
                self._show_help(event['channel'])
            elif "最近" in text or "recent" in text:
                days = self._extract_days(text) or 7
                self._show_recent_articles(event['channel'], days)
            else:
                self._show_help(event['channel'])

        except Exception as e:
            self.logger.error(f"Error handling mention: {str(e)}")
            self._send_error_message(event['channel'], str(e))

    def _extract_days(self, text: str) -> int:
        """
        テキストから日数を抽出
        """
        pattern = r'(\d+)日|(\d+)\s*days'
        match = re.search(pattern, text)
        if match:
            return int(match.group(1) or match.group(2))
        return 7

    def _show_help(self, channel: str):
        """
        ヘルプメッセージを表示
        """
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🤖 ニュース Bot の使い方"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*使用可能なコマンド:*"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "• `@bot help` or `@bot ヘルプ` - このヘルプを表示\n"
                        "• `@bot recent` or `@bot 最近` - 直近7日間の記事を表示\n"
                        "• `@bot recent 30days` or `@bot 最近30日` - 指定日数分の記事を表示"
                    )
                }
            }
        ]

        try:
            self.client.chat_postMessage(
                channel=channel,
                blocks=blocks
            )
        except SlackApiError as e:
            self.logger.error(f"Error sending help message: {str(e)}")

    def _show_recent_articles(self, channel: str, days: int = 7):
        """
        最近の記事一覧を表示
        """
        try:
            # 全企業の記事を取得
            companies = self.db.db.collection(self.db.config['collections']['companies']['name']).stream()
            company_map = {}
            for cdoc in companies:
                cdata = cdoc.to_dict()
                company_map[cdoc.id] = cdata.get('name', 'NoName')

            all_articles: List[Article] = self.db.get_recent_articles(None, days)

            # 日付でソート
            all_articles.sort(key=lambda x: x.published_at, reverse=True)

            if not all_articles:
                self.client.chat_postMessage(
                    channel=channel,
                    text=f"過去{days}日間の新着記事はありません。"
                )
                return

            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"📰 過去{days}日間の記事一覧 (全{len(all_articles)}件)"
                    }
                },
                {"type": "divider"}
            ]

            # 記事をブロックに変換
            for article in all_articles:
                cname = company_map.get(article.company_id, "Unknown Company")
                blocks.extend([
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                f"*<{article.url}|{article.title}>*\n"
                                f"🏢 {cname}\n"
                                f"📅 {article.published_at.strftime('%Y年%m月%d日 %H:%M')}\n"
                                f"📰 {article.source.upper()}"
                            )
                        }
                    },
                    {"type": "divider"}
                ])

            # 長いメッセージは分割して送信
            for i in range(0, len(blocks), 50):
                chunk = blocks[i:i + 50]
                self.client.chat_postMessage(
                    channel=channel,
                    blocks=chunk
                )

        except SlackApiError as e:
            self.logger.error(f"Error sending articles message: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error retrieving articles: {str(e)}")
            self._send_error_message(channel, str(e))

    def _send_error_message(self, channel: str, error: str):
        """
        エラーメッセージを送信
        """
        try:
            self.client.chat_postMessage(
                channel=channel,
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"⚠️ エラーが発生しました:\n```{error}```"
                        }
                    }
                ]
            )
        except SlackApiError as e:
            self.logger.error(f"Error sending error message: {str(e)}")
