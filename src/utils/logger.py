import logging
import logging.config
import os
import json
from google.cloud import logging as cloud_logging
from typing import Optional, Dict, Any

def setup_logger(
    name: Optional[str] = None,
    level: str = 'INFO',
    use_cloud_logging: bool = False
) -> logging.Logger:
    """
    ロガーを設定する

    Args:
        name: ロガー名
        level: ログレベル
        use_cloud_logging: Cloud Loggingを使用するかどうか

    Returns:
        logging.Logger: 設定されたロガー
    """
    # 基本設定
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
            'json': {
                'class': 'pythonjsonlogger.jsonlogger.JsonFormatter',
                'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': level,
                'formatter': 'standard',
                'stream': 'ext://sys.stdout'
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': level,
                'formatter': 'json',
                'filename': 'app.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5
            }
        },
        'loggers': {
            '': {  # rootロガー
                'handlers': ['console', 'file'],
                'level': level,
                'propagate': True
            }
        }
    }

    # 本番環境でCloud Loggingを使用
    if use_cloud_logging and os.getenv('ENVIRONMENT') == 'production':
        try:
            client = cloud_logging.Client()
            handler = cloud_logging.handlers.CloudLoggingHandler(client)
            config['handlers']['cloud'] = {
                'class': 'google.cloud.logging.handlers.CloudLoggingHandler',
                'client': client,
                'name': os.getenv('GOOGLE_CLOUD_PROJECT'),
                'formatter': 'json'
            }
            config['loggers']['']['handlers'].append('cloud')
        except Exception as e:
            print(f"Failed to setup Cloud Logging: {str(e)}")

    # ログ設定を適用
    logging.config.dictConfig(config)

    # ロガーを取得
    logger = logging.getLogger(name)
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """
    既存のロガーを取得する

    Args:
        name: ロガー名

    Returns:
        logging.Logger: 取得したロガー
    """
    return logging.getLogger(name)

class StructuredLogger:
    """
    構造化ログを出力するロガークラス
    """

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.default_fields = {
            'service': 'news-collector',
            'environment': os.getenv('ENVIRONMENT', 'development')
        }

    def _log(self, level: int, message: str, **kwargs):
        """
        構造化ログを出力

        Args:
            level: ログレベル
            message: ログメッセージ
            **kwargs: 追加のフィールド
        """
        # 基本フィールドとマージ
        fields = {**self.default_fields, **kwargs}
        
        # メッセージをJSONに変換
        log_entry = {
            'message': message,
            'severity': logging.getLevelName(level),
            **fields
        }
        
        self.logger.log(level, json.dumps(log_entry))

    def info(self, message: str, **kwargs):
        """INFOレベルのログを出力"""
        self._log(logging.INFO, message, **kwargs)

    def error(self, message: str, **kwargs):
        """ERRORレベルのログを出力"""
        self._log(logging.ERROR, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """WARNINGレベルのログを出力"""
        self._log(logging.WARNING, message, **kwargs)

    def debug(self, message: str, **kwargs):
        """DEBUGレベルのログを出力"""
        self._log(logging.DEBUG, message, **kwargs)

    def add_default_fields(self, fields: Dict[str, Any]):
        """デフォルトフィールドを追加"""
        self.default_fields.update(fields)