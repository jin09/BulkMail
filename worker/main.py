from celery import Celery

from conf import AMQP_URL, EMAIL_PERSONALIZATION_QUEUE

celery_app = Celery("tasks", broker=AMQP_URL)

celery_app.conf.update(
    imports=['worker.tasks.process_and_send_email'],  # path to your celery tasks file
    broker_connection_retry_on_startup=True,
    task_track_started=True,
    task_serializer='json',
    accept_content=['json'],
    task_routes={
        'tasks.process_and_send_email': {'queue': EMAIL_PERSONALIZATION_QUEUE}
    }
)
