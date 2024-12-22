import os
import logging
from logging.config import dictConfig
import yaml
from typing import Dict, Any

# ロギング設定
def setup_logging():
    """アプリケーションのロギング設定を初期化"""
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            },
        },
        'handlers': {
            'default': {
                'level': 'INFO',
                'formatter': 'standard',
                'class': 'logging.StreamHandler',
                'stream': 'ext://sys.stdout',
            },
            'error_file': {
                'level': 'ERROR',
                'formatter': 'standard',
                'class': 'logging.FileHandler',
                'filename': 'error.log',
                'mode': 'a',
            },
        },
        'loggers': {
            '': {  # root logger
                'handlers': ['default', 'error_file'],
                'level': 'INFO',
                'propagate': True
            },
            'werkzeug': {
                'handlers': ['default'],
                'level': 'INFO',
                'propagate': False
            },
        }
    }
    dictConfig(config)

def load_config() -> Dict[str, Any]:
    """アプリケーションの設定を読み込む"""
    config = {}
    config_dir = os.path.join(os.path.dirname(__file__), 'configs')
    
    # 各設定ファイルを読み込み
    config_files = [
        'companies.yaml',
        'slack_config.yaml',
        'firebase_config.yaml'
    ]
    
    for filename in config_files:
        filepath = os.path.join(config_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            config_name = filename.split('.')[0]
            config[config_name] = yaml.safe_load(f)
    
    return config

def init_firebase():
    """Firebase Adminを初期化"""
    import firebase_admin
    from firebase_admin import credentials
    
    if not firebase_admin._apps:
        cred_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if not cred_path:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)

def init_app():
    """アプリケーションを初期化"""
    # ロギングの設定
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting application initialization...")
    
    try:
        # 設定の読み込み
        config = load_config()
        
        # Firebase初期化
        init_firebase()
        
        # Flaskアプリケーションのインポートと初期化
        from .app import app
        
        logger.info("Application initialization completed successfully")
        return app
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        raise

# エントリーポイント
app = init_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)