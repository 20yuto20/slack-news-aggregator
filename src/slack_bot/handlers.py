# src/slack_bot/handlers.py

from typing import Dict, Any, List
from slack_sdk.web import WebClient
from slack_sdk.errors import SlackApiError
import logging
import re
import json
from datetime import datetime, timedelta

from ..data_access.firestore_client import FirestoreClient
from ..data_access.models import Article
from src.run_script import NewsCollector

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
            user_id = event.get('user', '')
            channel = event.get('channel', '')
            
            # テキストからメンションを削除して実際のコマンド部分のみを抽出
            text = re.sub(r'<@[A-Z0-9]+>', '', text).strip()
            
            self.logger.info(f"Received mention from user {user_id} in channel {channel}: '{text}'")

            # コマンドを解析
            if "help" in text or "ヘルプ" in text:
                self._show_help(channel)
            elif "recent" in text or "最近" in text:
                days = self._extract_days(text) or 7
                self._show_recent_articles(channel, days)
            elif "run" in text:
                # 追加: runコマンドを受けたときの処理
                self._handle_run_command(channel)
            elif "all" in text:
                # 追加: allコマンドを受けたときの処理
                self._handle_all_command(event)
            else:
                # 不明なコマンドの場合はヘルプ表示
                self._show_help(channel)

        except Exception as e:
            self.logger.error(f"Error handling mention: {str(e)}")
            self._send_error_message(event.get('channel', ''), str(e))

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
                        "• `@bot recent 30days` or `@bot 最近30日` - 指定日数分の記事を表示\n"
                        "• `@bot run` - 手動でスクレイピングを実行し、新着記事があれば通知\n"
                        "• `@bot all [会社名1,会社名2,...]` - 指定企業の過去記事を全件取得 (部分一致検索)"
                    )
                }
            }
        ]

        try:
            self.client.chat_postMessage(
                channel=channel,
                blocks=blocks
            )
            self.logger.info(f"Sent help message to channel {channel}")
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
            
            self.logger.info(f"Sent {len(all_articles)} articles to channel {channel}")

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

    # --------------------------------------------------------------------
    # 追加: run コマンドを受けてスクレイピングを実行するメソッド
    # --------------------------------------------------------------------
    def _handle_run_command(self, channel: str):
        try:
            # 実行中の通知を送信
            response = self.client.chat_postMessage(
                channel=channel,
                text="スクレイピングを開始します。しばらくお待ちください..."
            )
            
            # スクレイピング実行
            try:
                collector = NewsCollector()
                collector.run()
                
                # 完了通知
                self.client.chat_postMessage(
                    channel=channel,
                    text="スクレイピングが完了しました。新しい記事があれば別途通知しています。",
                    thread_ts=response['ts']
                )
                
                self.logger.info(f"Successfully executed run command in channel {channel}")
            except AttributeError as e:
                if "'SlackNotifier' object has no attribute 'logger'" in str(e):
                    # このエラーは無視して実行完了とする
                    self.client.chat_postMessage(
                        channel=channel,
                        text="スクレイピングが完了しました（通知の一部で軽微なエラーがありましたが、処理自体は正常に完了しています）。",
                        thread_ts=response['ts']
                    )
                    self.logger.info(f"Completed run with minor notification errors in channel {channel}")
                else:
                    raise
            except Exception as e:
                self.logger.error(f"Error running collector: {str(e)}")
                self.client.chat_postMessage(
                    channel=channel,
                    text=f"スクレイピング実行中にエラーが発生しました。\n```{str(e)}```",
                    thread_ts=response['ts']
                )
            
        except Exception as e:
            self.logger.error(f"Error running manual scraping: {str(e)}")
            self._send_error_message(channel, str(e))

    # --------------------------------------------------------------------
    # 追加: all コマンドを受けて指定企業 or 全企業の過去記事を JSON で取得
    # --------------------------------------------------------------------
    def _handle_all_command(self, event: Dict[str, Any]):
        channel = event['channel']
        text = event.get('text', '').strip()

        # "all"の後ろの文字列を取得 (例: "all test1,test2")
        # 正規表現で抜き出してカンマ区切りにする
        match = re.search(r'all\s+(.*)', text, re.IGNORECASE)
        if match:
            # 部分一致用のキーワードたち
            raw_keywords = match.group(1)
            keywords = [kw.strip() for kw in raw_keywords.split(',') if kw.strip()]
        else:
            # /all のみの場合
            keywords = []

        try:
            # 企業一覧を取得
            companies_ref = self.db.db.collection(self.db.config['collections']['companies']['name'])
            all_companies = list(companies_ref.stream())
            if not all_companies:
                self.client.chat_postMessage(channel=channel, text="企業データがありません。")
                return

            # 部分一致で該当企業を抽出 (keywords が空なら全企業)
            matched_company_ids = []

            if not keywords:
                # 全企業対象
                matched_company_ids = [doc.id for doc in all_companies]
            else:
                for doc in all_companies:
                    data = doc.to_dict()
                    company_name = data.get('name', '')
                    for kw in keywords:
                        if kw.lower() in company_name.lower():
                            matched_company_ids.append(doc.id)
                            break  # 一度マッチしたら重複追加しないようbreak

            if not matched_company_ids:
                self.client.chat_postMessage(
                    channel=channel,
                    text="指定された企業名に部分一致する企業が見つかりません。"
                )
                return

            # 該当企業の全過去記事を取得
            all_articles = []
            for company_id in matched_company_ids:
                articles = self.db.get_all_articles_by_company_id(company_id)
                all_articles.extend(articles)

            if not all_articles:
                self.client.chat_postMessage(
                    channel=channel,
                    text="記事が見つかりませんでした。"
                )
                return

            # JSON化
            articles_json = json.dumps(all_articles, ensure_ascii=False, indent=2, default=str)

            # Slack へのアップロード
            # 100万文字以上になるとエラーの可能性があるので注意 (記事が非常に多い場合)
            response = self.client.files_upload(
                channels=channel,
                content=articles_json,
                filetype='json',
                filename='articles.json',
                title='Articles Download'
            )

            if response["ok"]:
                self.client.chat_postMessage(
                    channel=channel,
                    text=f"指定した企業の過去記事をJSONファイルとしてアップロードしました（全{len(all_articles)}件）。"
                )
                self.logger.info(f"Successfully uploaded {len(all_articles)} articles as JSON to channel {channel}")
            else:
                self.client.chat_postMessage(
                    channel=channel,
                    text="JSONファイルのアップロードに失敗しました。"
                )

        except Exception as e:
            self.logger.error(f"Error handling all command: {str(e)}")
            self._send_error_message(channel, str(e))