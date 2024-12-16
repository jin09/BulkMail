from enum import Enum
from typing import List, Dict
from uuid import UUID

from pydantic import BaseModel, EmailStr


class BatchSendRequestBody(BaseModel):
    recipients: List[EmailStr]
    subject: str
    body: str
    personalization_data: Dict[EmailStr, Dict[str, str]]


class BatchEmailRequest(BatchSendRequestBody):
    request_id: UUID


class StatusEnum(str, Enum):
    submitted = "submitted"
    errored = "errored"


class BatchSendResponse(BaseModel):
    status: StatusEnum
    request_id: UUID
