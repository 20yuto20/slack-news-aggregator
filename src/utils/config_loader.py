# src/utils/config_loader.py

from typing import Dict, Any, Optional
import os
import yaml
from pathlib import Path
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

def get_config_path(filename: str) -> Path:
    """
    設定ファイルのパス取得
    """
    base_path = Path(__file__).parent.parent / 'configs'
    file_path = base_path / filename

    if not file_path.exists():
        raise FileNotFoundError(f"Config file not found: {filename}")

    return file_path

@lru_cache(maxsize=32)
def load_config(filename: str, env: Optional[str] = None) -> Dict[str, Any]:
    """
    設定ファイルの読み込み関数
    """
    try:
        file_path = get_config_path(filename)
        with open(file_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        if env or (env := os.getenv('ENVIRONMENT')):
            if env not in config:
                raise ValueError(f"Environment '{env}' not found in config")
            config = config[env]

        validate_config(config, filename)
        return config
    except Exception as e:
        logger.error(f"Error loading config file {filename}: {str(e)}")
        raise

def validate_config(config: Dict[str, Any], filename: str):
    """
    設定の検証
    """
    required_keys = {
        'companies.yaml': ['companies'],
        'slack_config.yaml': ['bot_token', 'signing_secret', 'default_channel'],
        'firebase_config.yaml': ['collections']
    }

    if filename in required_keys:
        for key in required_keys[filename]:
            if key not in config:
                raise ValueError(f"Required key '{key}' not found in {filename}")

    if filename == 'companies.yaml':
        for company in config['companies']:
            if 'id' not in company or 'name' not in company:
                raise ValueError(f"Company is missing 'id' or 'name'. Check 'companies.yaml'")

    if filename == 'slack_config.yaml':
        if not config['bot_token'].startswith('xoxb-'):
            raise ValueError("Invalid Slack bot token format. It has to start with 'xoxb-'.")

def get_environment_config() -> Dict[str, str]:
    """
    環境変数を取得
    """
    return {
        'environment': os.getenv('ENVIRONMENT', 'development'),
        'project_id': os.getenv('PROJECT_ID', ''),
        'google_cloud_project': os.getenv('GOOGLE_CLOUD_PROJECT', ''),
        'region': os.getenv('REGION', 'asia-northeast1')
    }

def update_config(filename: str, updates: Dict[str, Any]):
    """
    設定ファイルの更新
    """
    try:
        file_path = get_config_path(filename)
        current_config = load_config(filename)

        new_config = deep_merge(current_config, updates)
        validate_config(new_config, filename)

        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(new_config, f, default_flow_style=False)

        load_config.cache_clear()

    except Exception as e:
        logger.error(f"Error updating config file {filename}: {str(e)}")
        raise

def deep_merge(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    二つのDict形式を再帰的マージ
    """
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result
