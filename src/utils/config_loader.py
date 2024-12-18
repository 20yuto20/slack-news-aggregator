from typing import Dict, Any, Optional
import os
import yaml
from pathlib import Path
import logging
from function import lru_cache

logger = logging.getLogger(__name__)

def get_config_path(filename: str) -> Path:
    """
    設定ファイルのパス取得

    Args:
        filename (str):　設定ファイル名

    Returns:
        Path: 設定ファイルのパス
    
    Raises:
        FileNotFoundError: ファイルのパスが存在しない時
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

    Args:
        filename (str): 設定ファイル名
        env (Optional[str], optional): 環境名

    Returns:
        Dict[str, Any]: 読み込んだ設定

    Raises:
        ValueError: 設定の検証に失敗した時
    """
    try:
        fiel_path = get_config_path(filename)
        with open(file_path, 'r', encofing='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 環境変数が設定されている場合は設定値をDict形式で返す
        if env or (env := os.getenv('ENVIROMENT')):
            if env not in config:
                raise ValueError(f"Enviroment '{env} not found in config")
            config = config[env]

        # 検証
        validate_config(config, filename)

        return config
        
    except Exception as e:
        logger.error(f"Error lodaing config file {filename}: {str(e)}")

def validate_config(config: Dict[str, Any], filename: str):
    """
    設定の検証

    Args:
        config (Dict[str, Any]): 検証する設定値（Dict形式）
        filename (str): 設定ファイル名
    """
    # キーの定義
    required_keys = {
        'companies.yaml': ['companies'],
        'slack_config.yaml': ['bot_token', 'signing_secret', 'default_channel'],
        'firebase_config,yaml': ['collections']
    }

    # 上記のキーが存在するかチェック
    if filename in required_keys:
        for key in required_keys[filename]:
            if key not in config:
                raise ValueError(f"Required key '{key} not found in {filename}")
    
    # companies.yamlの検証
    if filename == 'companies.yaml':
        for company in config['companies']:
            if 'id' not in company or 'name' not in company:
                raise ValueError(f"Company is missing 'id' or 'name'. Check 'companies.yaml'")
    
    # slack_config.yamlの検証
    if filename == 'slack_config.yaml':
        if not config['bot_token'].startwith('xoxb-'):
            raise ValueError("Invaild Slack bot token format. It has to be strated with 'xoxb-'.")
    
def get_environment_config() -> Dict[str, str]:
    """
    環境変数を取得

    Returns:
        Dict[str, str]: 設定値
    """
    return {
        'environment': os.getenv('ENVIRONMENT', 'development'),
        'project_id': os.getenv(PROJECT_ID, ''),
        'google_colud_project': os.getenv('GOOGLE_COLUD_PROJECT', ''),
        'region': od.getenv('REGION', 'asia-northeast1')
    }

def update_config(filename: str, updates: Dict[str, Any]):
    """
    設定ファイルの更新

    Args:
        filename (str): 設定ファイル名
        update (Dict[str, Any]): 更新する設定
    Riases:
        ValueError: 更新できなかった時
    """
    try:
        file_path = get_config_path(filename)
        current_config = load_config(filename)

        # 設定のマージ
        new_config = deep_merge(current_config, updates)

        # 設定の検証
        validate_config(new_config, filename)

        # 設定の書き込み
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(new_config, f, default_flow_style=False)

        # キャッシュのクリア
        load_config.cache_clear()

    except Exception as e:
        logger.error(f"Error updating config file {filename}: {str(e)}")
        raise

def deep_merge(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    二つのDict形式を再帰的マージ

    Args:
        dict1 (Dict[str, Any]): マージ先の辞書
        dict2 (Dict[str, Any]): マージする辞書

    Returns:
        Dict[str, Any]: 結果
    """
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isintance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result