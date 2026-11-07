from __future__ import annotations

import uuid
from datetime import datetime
from typing import List
from pydantic import BaseModel


class OrganizationResponse(BaseModel):
    id: uuid.UUID
    name: str
    org_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MembershipResponse(BaseModel):
    organization: OrganizationResponse
    role: str
    is_active: bool


class UserOrganizationsResponse(BaseModel):
    memberships: List[MembershipResponse]
