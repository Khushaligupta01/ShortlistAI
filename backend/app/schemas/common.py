from __future__ import annotations

from typing import Generic, List, TypeVar
from pydantic import BaseModel

DataT = TypeVar("DataT")


class PaginatedResponse(BaseModel, Generic[DataT]):
    items: List[DataT]
    total: int
    page: int
    page_size: int


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    trace_id: str
