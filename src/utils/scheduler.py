from typing import Any, Callable, Dict, Optional
from google.cloud import scheduler_v1
from google.cloud import tasks_v2
from datetime import datetime, timedelta
import json
import logging
import os

class TaskScheduler:
    """
    Cloud SchedulerとCloud Tasksを使用したスケジューラー
    """

    def __init__(self, project_id: str, location, str):
        self.project_id = project_id
        self.location = location
        self.scheduler_client = scheduler_v1.CloudSchedulerClient()
        self.tasks_client = tasks_v2.CloudTasksClient()
        self.logger = logging.getLogger(__name__)
        self.parent = f"projects/{project_id}/locations/{location}"

    def create_scheduled_job(
        self, 
        job_name: str,
        schedule: str,
        target_url: str,
        http_method: str = 'POST',
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        description: str = ''
    ) -> scheduler_v1.Job:
        """
        定期ジョブ実行を作成

        Args:
            job_name (str): ジョブ名
            schedule (str): スケジュール(CRON形式)
            target_url (str): 実行するエンドポイントURL
            http_method (str, optional): HTTPメソッド
            body (Optional[Dict[str, Any]], optional): リクエストボディ
            headers (Optional[Dict[str, str]], optional): HTTPヘッダー
            description (str, optional): ジョブの説明

        Returns:
            scheduler_v1.Job: 作成したジョブ
        """
        try:
            job_path = f"{self.parent}/jobs/{job_name}"

            # HTTPターゲットの設定
            hhtp_target = scheduler_v1.HttpTarget()
            http_target.uri = target_url
            http_target.http_method = getattr(
                scheduler_v1.HttpMethod,
                http_method.upper()
            )

            if body:
                http_target.body = json.dumps(body).encode()

            if headers:
                http_target.headers = headers
            
            # ジョブの設定
            job = scheduler_v1.Job(
                name=job_path,
                http_target=http_target,
                schedule=schedule,
                time_zone="Asia/Tokyo",
                description=description
            )

            return self.scheduler_client.create_job(
                request={
                    "parent": self.parent,
                    "job": job
                }
            )

        except Exception as e:
            self.logger.error(f"Error creating scheduled job: {str(e)}")
            raise

    def update_job(
        self,
        job_name: str,
        schedule: Optional[str] = None,
        target_url: Optional[str] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> scheduler_v1.Job:
        """_summary_

        Args:
            job_name (str): 更新するジョブ
            schedule (Optional[str], optional): 新しいスケジュール
            target_url (Optional[str], optional): 新しいターゲットURL
            body (Optional[Dict[str, Any]], optional): 新しいリクエストbody

        Returns:
            scheduler_v1.Job: 更新したジョブ
        """
        try:
            job_path = f"{self.parent}/jobs/{job_name}"
            job = self.scheduler_client.get_job(name=job_path)

            update_mask = []

            if schedule:
                job.schedule = schedule
                update_mask.append("schedule")

            if target_url:
                job.http_target.uri = target_url
                update_mask.append("http_target.uri")

            if body:
                job.http_target.body = json.dumps(body).encode()
                update_mask.append("http_taget.body")

            return self.scheduler_client.update_job(
                request={
                    "job": job,
                    "update_mask": {"paths": update_mask}
                }
            )

        except Exception as e:
            self.logger.error(f"Error updating job: {str(e)}")
            raise

    def delete_job(self, job_name: str):
        """
        ジョブを削除

        Args:
            job_name (str): 削除したいジョブ名
        """
        try:
            job_path = f"{self.parent}/jobs/{job_name}"
            self.scheduler_client.delete_job(name=job_path)

        except Exception as e:
            self.logger.error(f"Error deleting job: {str(e)}")
            raise

    def create_one_time_task(
        self,
        queue_name: str,
        task_name: str,
        target_url: str,
        payload: Dict[str, Any],
        schedule_time: Optional[datetime] = None,
        service_account_email: Optional[str] = None
    ):
        """
        一回限りのタスクを作成

        Args:
            queue_name: タスクキュー名
            task_name: タスク名
            target_url: 実行するエンドポイントのURL
            payload: タスクのペイロード
            schedule_time: 実行予定時刻
            service_account_email: 実行に使用するサービスアカウント
        """
        try:
            parent = self.tasks_client.queue_path(
                self.project_id,
                self.location,
                queue_name
            )

            task = {
                'name': f'{parent}/tasks/{task_name}',
                'http_request': {
                    'http_method': tasks_v2.HttpMethod.POST,
                    'url': target_url,
                    'headers': {
                        'Content-Type': 'application/json',
                    },
                    'body': json.dumps(payload).encode(),
                }
            }

            if schedule_time:
                task['schedule_time'] = schedule_time.strftime('%Y-%m-%dT%H:%M:%SZ')

            if service_account_email:
                task['http_request']['oidc_token'] = {
                    'service_account_email': service_account_email
                }

            return self.tasks_client.create_task(
                request={
                    'parent': parent,
                    'task': task
                }
            )

        except Exception as e:
            self.logger.error(f"Error creating one-time task: {str(e)}")
            raise

    def get_job_status(self, job_name: str) -> Dict[str, Any]:
        """
        ジョブの状態を取得

        Args:
            job_name: ジョブ名

        Returns:
            Dict: ジョブの状態情報
        """
        try:
            job_path = f"{self.parent}/jobs/{job_name}"
            job = self.scheduler_client.get_job(name=job_path)

            return {
                'name': job.name,
                'state': job.state.name,
                'schedule': job.schedule,
                'last_attempt_time': job.last_attempt_time,
                'next_scheduled_time': job.next_scheduled_time,
                'attempt_deadline': job.attempt_deadline,
                'retry_config': {
                    'retry_count': job.retry_config.retry_count,
                    'max_retry_duration': job.retry_config.max_retry_duration,
                    'min_backoff_duration': job.retry_config.min_backoff_duration,
                    'max_backoff_duration': job.retry_config.max_backoff_duration
                }
            }

        except Exception as e:
            self.logger.error(f"Error getting job status: {str(e)}")
            raise