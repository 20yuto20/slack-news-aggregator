# test_slack_token.py
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Slack Botトークンを設定（実際のトークンに置き換えてください）
SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')

# WebClientの初期化
client = WebClient(token=SLACK_BOT_TOKEN)

# 接続テスト
try:
    response = client.api_test()
    print(f"API Test Response: {response}")
    
    # チャンネルにメッセージを送信してみる
    msg_response = client.chat_postMessage(
        channel="#cs-news",  # 実際のチャンネル名に変更してください
        text="Hello from test script!"
    )
    print(f"Message sent successfully: {msg_response['ts']}")
    
except SlackApiError as e:
    print(f"Error testing Slack API: {e}")