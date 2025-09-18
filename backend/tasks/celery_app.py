import os
from celery import Celery

# Celery app configured to use Redis as broker and backend
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery = Celery(
    "downloader",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

# Reasonable defaults for our workload
celery.conf.update(
    task_track_started=True,
    result_expires=3600,  # 1 hour
    worker_cancel_long_running_tasks_on_connection_loss=True,
)