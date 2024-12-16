import logging
import random
from enum import Enum
from typing import Dict, Optional

from pydantic import EmailStr

from conf import PROCESS_AND_SEND_EMAIL_RETRY_COUNT, MOCK_SUCCESS_RATE, EMAIL_PERSONALIZATION_QUEUE
from worker.exceptions import FailedRequestException
from worker.main import celery_app
from models import BatchEmailRequest
from worker.redis_client import RedisClient

logger = logging.getLogger()
logging.basicConfig()
logger.setLevel(logging.INFO)


class Status(str, Enum):
    """
    Represents an enumeration for status values.

    This class is used to define two constant string values: "success" and
    "failed". It can be utilized in contexts where a fixed set of predefined
    statuses is required.

    :ivar success: Indicates a successful operation or state.
    :type success: str
    :ivar failed: Indicates a failed operation or state.
    :type failed: str
    """
    success = "success"
    failed = "failed"


def generate_personalized_email_body(email: EmailStr, body: str,
                                     personalization_data: Dict[EmailStr, Dict[str, str]]) -> str:
    """
    Generates a personalized email body for a given recipient email using provided
    personalization data. The method substitutes placeholders in the email body
    with appropriate contextual data corresponding to the email address.

    :param email: The email address of the recipient for which the body is to
                  be personalized.
    :param body: The base email body containing placeholders to be replaced
                 with personalization data.
    :param personalization_data: A dictionary where keys are recipient email
                                 addresses, and values are dictionaries of
                                 personalization key-value pairs.

    :return: A string that contains the fully formatted, personalized email body.
    """
    return body.format(**personalization_data[email])


def set_failed_status_for_request(batch_email_request: BatchEmailRequest, redis_client: RedisClient):
    """
    Updates the status of all email requests in a batch to 'failed'. This function iterates
    through a list of email recipients contained in the batch email request and sets their
    status to 'failed' in the Redis database.

    :param batch_email_request: The request object containing the batch ID and the list of
        email recipients whose statuses need to be updated.
    :type batch_email_request: BatchEmailRequest
    :param redis_client: An instance of RedisClient that provides access to the Redis
        database where the statuses are stored.
    :type redis_client: RedisClient
    :return: None
    """
    for email in batch_email_request.recipients:
        redis_client.connection.set(f"{batch_email_request.request_id}::{email}", str(Status.failed).encode("utf-8"))


def set_success_status_for_email(email: EmailStr, batch_email_request: BatchEmailRequest, redis_client: RedisClient):
    """
    Sets the success status for a specific email identified by its unique request ID in a batch email request.
    The status is stored in the Redis database as "success", ensuring easy access for further operations or tracking.

    :param email: The email address for which the success status is to be set.
    :type email: EmailStr
    :param batch_email_request: The batch email request containing the unique request ID to associate with the status.
    :type batch_email_request: BatchEmailRequest
    :param redis_client: The Redis client used to store the status of the email in the database.
    :type redis_client: RedisClient
    :return: None
    """
    redis_client.connection.set(f"{batch_email_request.request_id}::{email}", str(Status.success).encode("utf-8"))


@celery_app.task(bind=True, max_retries=PROCESS_AND_SEND_EMAIL_RETRY_COUNT, acks_late=True)
def process_and_send_email(self, batch_email_request: Dict):
    """
    Handles processing and sending batch emails as a Celery task. This task simulates
    the sending process and manages email statuses using Redis. It retries the task
    if failures occur, up to a specified retry count. Emails are personalized based
    on provided data, and results are logged accordingly.

    :param self: Represents the task instance when method is executed by the Celery worker.
    :param batch_email_request: Dictionary containing all details required for processing
                                a batch email request.
    :type batch_email_request: Dict
    :return: None
    """
    try:
        batch_email_request = BatchEmailRequest(**batch_email_request)
        if random.random() < MOCK_SUCCESS_RATE:
            set_failed_status_for_request(batch_email_request, RedisClient())
            raise FailedRequestException("Simulation Failed")

        redis_client = RedisClient()

        for email in batch_email_request.recipients:
            email_send_status: Optional[bytes] = redis_client.connection.get(f"{batch_email_request.request_id}::{email}")
            if email_send_status and email_send_status.decode("utf-8") == str(Status.success):
                continue
            personalised_email_body = generate_personalized_email_body(email, batch_email_request.body,
                                                                       batch_email_request.personalization_data)

            logger.info(f"Email Sent to {email}! Subject: {batch_email_request.subject} Body: {personalised_email_body}")
            set_success_status_for_email(email, batch_email_request, RedisClient())
    except Exception as e:
        logger.error(f"task failed :: {e}")
        if self.request.retries >= PROCESS_AND_SEND_EMAIL_RETRY_COUNT:
            process_and_send_email.apply_async(args=[batch_email_request.model_dump()], queue=EMAIL_PERSONALIZATION_QUEUE)
        raise self.retry(exc=e, countdown=5)
