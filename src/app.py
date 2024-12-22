from flask import Flask, request, jsonify, Response
from slack_sdk.signature import SignatureVerifier
from slack_sdk.web import WebClient
import yaml
import os
import logging
from functools import wraps
import json
from datetime import datetime

from slack_bot.handlers import SlackEventHandler
from data_access.firestore_client import FirestoreClient
from run_script import NewsCollector

# Flaskアプリケーションの初期化
app = Flask(__name__)

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Slack設定の読み込み
def load_slack_config():
    config_path = os.path.join(os.path.dirname(__file__), 'configs/slack_config.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        env = os.getenv('ENVIRONMENT', 'development')
        return config[env]

# Slack認証の初期化
slack_config = load_slack_config()
signature_verifier = SignatureVerifier(slack_config['signing_secret'])
slack_client = WebClient(token=slack_config['bot_token'])
event_handler = SlackEventHandler(slack_client)

def verify_slack_signature(f):
    """Slackリクエストの署名を検証するデコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not verify_request():
            return jsonify({'error': 'Invalid request signature'}), 401
        return f(*args, **kwargs)
    return decorated_function

def verify_request() -> bool:
    """Slackリクエストの署名を検証"""
    timestamp = request.headers.get('X-Slack-Request-Timestamp', '')
    signature = request.headers.get('X-Slack-Signature', '')
    body = request.get_data().decode('utf-8')
    
    return signature_verifier.is_valid(
        body=body,
        timestamp=timestamp,
        signature=signature
    )

@app.route('/slack/events', methods=['POST'])
@verify_slack_signature
def slack_events():
    """Slackイベントを処理するエンドポイント"""
    data = request.json

    # URL Verification
    if data.get('type') == 'url_verification':
        return jsonify({'challenge': data['challenge']})

    # イベント処理
    if data.get('type') == 'event_callback':
        event = data.get('event', {})
        
        # メンションイベントの処理
        if event.get('type') == 'app_mention':
            try:
                event_handler.handle_mention(event)
            except Exception as e:
                logger.error(f"Error handling mention: {str(e)}")
                return jsonify({'error': str(e)}), 500

    return jsonify({'status': 'ok'})

@app.route('/run', methods=['GET'])
def run_scraping():
    """スクレイピングを実行するエンドポイント"""
    try:
        collector = NewsCollector()
        collector.run()
        return jsonify({
            'status': 'success',
            'message': 'Scraping process completed',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error running scraping: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """ヘルスチェックエンドポイント"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/stats', methods=['GET'])
def get_stats():
    """統計情報を取得するエンドポイント"""
    try:
        db = FirestoreClient()
        stats = {
            'total_articles': db.get_total_articles_count(),
            'articles_by_company': db.get_articles_count_by_company(),
            'articles_by_source': db.get_articles_count_by_source(),
            'latest_articles': db.get_latest_articles(limit=5)
        }
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port)