# このモジュールは廃止され、手動設定に置き換えられます
# scheduler.py

"""
このファイルの機能は廃止されました。
Cloud Schedulerは手動でGoogle Cloudコンソールから設定してください。

手順:
1. Google Cloudコンソールにアクセス
2. Cloud Schedulerを選択
3. ジョブを作成をクリック
4. 以下の設定で新規ジョブを作成:
   - 名前: daily-news-scraper
   - 説明: 毎日のニュース収集ジョブ
   - 頻度: 0 8 * * * (毎朝8時)
   - タイムゾーン: Asia/Tokyo
   - ターゲットタイプ: HTTPSエンドポイント
   - URL: https://[YOUR-REGION]-[YOUR-PROJECT-ID].cloudfunctions.net/new_collector/run
   - HTTPメソッド: GET
   - 認証ヘッダー: 必要に応じて設定

注意: このファイルはレガシーコードとして保持していますが、
アプリケーションからは使用されません。
"""