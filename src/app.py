from flask import Flask, request, jsonify
from slack_sdk.signature import SignatureVerifier
from slack_sdk.web import WebClient
import yaml
import os
import logging
from functools import wraps
from datetime import datetime
from pathlib import Path

# インポートパスを修正
from src.slack_bot.handlers import SlackEventHandler
from src.data_access.firestore_client import FirestoreClient
from src.run_script import NewsCollector

app = Flask(__name__)

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_slack_config():
    try:
        config_path = os.path.join(Path(__file__).parent, 'configs/slack_config.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            env = os.environ.get('ENVIRONMENT', 'development')
            return config[env]
    except Exception as e:
        logger.error(f"Failed to load slack config: {e}")
        # フォールバック設定を環境変数から直接読み込む
        return {
            'signing_secret': os.environ.get('SLACK_SIGNING_SECRET', ''),
            'bot_token': os.environ.get('SLACK_BOT_TOKEN', '')
        }

# 設定の読み込みを遅延させる
def get_slack_config():
    if not hasattr(get_slack_config, 'config'):
        get_slack_config.config = load_slack_config()
    return get_slack_config.config

def get_signature_verifier():
    config = get_slack_config()
    return SignatureVerifier(config['signing_secret'])

def get_slack_client():
    config = get_slack_config()
    token = config['bot_token']
    
    # 環境変数展開サポート
    if token and token.startswith('${') and token.endswith('}'):
        env_var = token[2:-1]
        token = os.environ.get(env_var, '')
    
    # トークンのログ記録 (開発目的)
    if token:
        logger.info(f"Using Slack token starting with: {token[:4]}..." if len(token) > 4 else "Token is too short!")
    else:
        logger.error("Slack token is empty!")
    
    return WebClient(token=token, base_url="https://slack.com/api/")

# リクエスト時に初期化する
@app.before_request
def initialize_slack():
    if not hasattr(app, 'event_handler'):
        app.event_handler = SlackEventHandler(get_slack_client())
        logger.info("Initialized Slack event handler")

# ヘルスチェック用のエンドポイント
@app.route('/_ah/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

# デバッグ用のエンドポイント
@app.route('/', methods=['GET'])
def root():
    return jsonify({
        'status': 'ok',
        'message': 'Server is running',
        'endpoints': [
            '/health',
            '/run',
            '/stats',
            '/slack/events'
        ]
    })

def verify_slack_request():
    """Slackリクエストの署名を検証する"""
    # 開発環境では検証をスキップ
    if os.getenv('ENVIRONMENT') == 'development':
        return True
        
    # Slackからのリクエストでない場合はスキップ
    if request.path != '/slack/events':
        return True
        
    timestamp = request.headers.get('X-Slack-Request-Timestamp')
    signature = request.headers.get('X-Slack-Signature')
    
    if not timestamp or not signature:
        return False
    
    try:
        body = request.get_data().decode('utf-8')
        return get_signature_verifier().is_valid(
            body=body,
            timestamp=timestamp,
            signature=signature
        )
    except Exception as e:
        logger.error(f"Signature verification failed: {e}")
        return False

@app.before_request
def verify_slack_signature():
    """リクエスト前に署名を検証"""
    if not verify_slack_request():
        return jsonify({'error': 'Invalid request signature'}), 403

@app.route('/slack/events', methods=['POST'])
def slack_events():
    data = request.json

    if data.get('type') == 'url_verification':
        return jsonify({'challenge': data['challenge']})

    if data.get('type') == 'event_callback':
        event = data.get('event', {})
        if event.get('type') == 'app_mention':
            try:
                # Fix: app.event_handlerを使用する
                app.event_handler.handle_mention(event)
            except Exception as e:
                logger.error(f"Error handling mention: {str(e)}")
                return jsonify({'error': str(e)}), 500

    return jsonify({'status': 'ok'})

@app.route('/run', methods=['GET'])
def run_scraping():
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

@app.route('/stats', methods=['GET'])
def get_stats():
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
    # Cloud Run環境では PORT 環境変数を使用する必要がある
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port)