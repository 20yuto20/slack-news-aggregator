import pytest
import os
from src.utils.scheduler import TaskScheduler

@pytest.mark.integration
def test_create_daily_scraper_schedule():
    """
    TaskSchedulerを用いて、毎朝8時(JST)に実行されるジョブを作成し、正しく作成されることを確認。
    テスト用ジョブなので最後に削除まで行う。
    実際にGCPのCloud Scheduler APIを呼ぶため、以下の環境変数が設定されている必要があります:
      - PROJECT_ID
      - REGION
      - GOOGLE_APPLICATION_CREDENTIALS
    """
    project_id = os.getenv('PROJECT_ID')
    location = os.getenv('REGION')
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

    # 必要な環境変数が揃っていなければテストスキップ
    if not project_id or not location:
        pytest.skip("PROJECT_ID or REGION is not set. Skipping integration test.")

    # 認証ファイルが設定されていて実在しない場合もスキップ
    if not credentials_path or not os.path.exists(credentials_path):
        pytest.skip("GOOGLE_APPLICATION_CREDENTIALS not found or file doesn't exist. Skipping integration test.")

    # TaskSchedulerのインスタンスを生成
    scheduler = TaskScheduler(project_id=project_id, location=location)

    job_name = "test-daily-scraper-job"
    target_url = "https://<your-cloud-function-url>/run"  # 実際に動かす先の関数URL

    # create_daily_scraper_schedule() を呼び出すと "0 8 * * *" のスケジュールで作成
    job = scheduler.create_daily_scraper_schedule(
        job_name=job_name,
        target_url=target_url
    )

    # 作成されたジョブの検証
    assert job.name.endswith(job_name), "Job name does not match"
    assert job.schedule == "0 8 * * *", "Schedule is not set to 8 AM JST daily"

    # ここではテスト用なので、作成したジョブは後で削除
    scheduler.delete_job(job_name)
