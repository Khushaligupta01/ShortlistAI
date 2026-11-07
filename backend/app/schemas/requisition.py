from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class RequisitionResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    created_by: uuid.UUID
    title: str
    job_description: str
    status: str
    created_at: datetime
    updated_at: datetime
    version: int

    model_config = {"from_attributes": True}


class RequisitionListResponse(BaseModel):
    items: List[RequisitionResponse]
    total: int
    page: int
    page_size: int
