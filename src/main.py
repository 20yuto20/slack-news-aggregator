import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# .envファイルを読み込む（存在する場合のみ）
env_path = os.path.join(Path(__file__).parent, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

# プロジェクトルートへのパスを追加
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from firebase_functions import https_fn
from flask import Flask
from src.app import app

@https_fn.on_request(
    region="us-central1",
    memory=256,
    min_instances=0,
    max_instances=10,
    concurrency=1,
    timeout_sec=60
)
def main(req: https_fn.Request) -> https_fn.Response:
    """
    Cloud Functions のエントリーポイント
    """
    with app.app_context():
        return app.wsgi_app(req.environ, req.start_response)

if __name__ == "__main__":
    # ローカル開発用のサーバー起動
    debug = os.environ.get('ENVIRONMENT') == 'development'
    port = int(os.environ.get('PORT', 8080))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug,
        use_reloader=debug
    )
