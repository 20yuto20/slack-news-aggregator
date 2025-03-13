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
from src.app import app

@https_fn.on_request(
    region="asia-northeast1",
    memory=256,
    min_instances=0,
    max_instances=10,
    concurrency=1,
    timeout_sec=60
)
def new_collector(req: https_fn.Request) -> https_fn.Response:
    """
    Cloud Functions のエントリーポイント
    """
    # Firebase Functionsのリクエストを処理するために、
    # Flaskアプリケーションを直接呼び出す
    with app.request_context(req.environ):
        return app.full_dispatch_request()