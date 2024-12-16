import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict

from aiormq import AMQPError
from fastapi import APIRouter, Request, status, HTTPException
from kombu.exceptions import KombuError

from app.api.email.utils import get_request_id
from models import BatchSendResponse, BatchSendRequestBody, StatusEnum
from conf import EMAIL_PERSONALIZATION_QUEUE
from worker.tasks.process_and_send_email import process_and_send_email

router = APIRouter(prefix="/email", tags=["email"])
logger = logging.getLogger()
logging.basicConfig()
logger.setLevel(logging.INFO)


@router.post('/batchSend', response_model=BatchSendResponse, status_code=status.HTTP_202_ACCEPTED)
async def email_batch_send(request: Request, body: BatchSendRequestBody) -> Dict:
    """
    Handles batch email sending requests by processing the provided emails data and enqueues the task
    for asynchronous execution.
    """
    request_id: str = get_request_id(request)
    body_dict = body.model_dump()
    body_dict["request_id"] = request_id
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        try:
            await loop.run_in_executor(executor, lambda: process_and_send_email.apply_async(
                args=[body_dict],
                queue=EMAIL_PERSONALIZATION_QUEUE,
            ))
        except (AMQPError, KombuError) as e:
            logger.error(e)
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                                detail={"status": StatusEnum.errored, "request_id": request_id,
                                        "error_message": str(e)}) from e
    return {"status": StatusEnum.submitted, "request_id": request_id}
