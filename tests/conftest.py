# tests/conftest.py
import pytest
import os

@pytest.fixture(scope="session", autouse=True)
def set_test_environment():
    """
    テスト全体の共通フィクスチャ。
    例えば、DB接続をテスト用に差し替えたり、テスト用の環境変数を設定したりする。
    """
    # テスト時にENVIRONMENTをdevelopmentにセット
    os.environ["ENVIRONMENT"] = "development"
    
    # 必要に応じてさらに環境変数をセット
    # os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/path/to/test/service_account.json"
    
    yield

    # テスト終了時の後処理があれば実行
    # （特になければ何もしない）
