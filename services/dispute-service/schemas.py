from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from models import DisputeStatus, DisputeReason


class DisputeCreate(BaseModel):
    customer_id: UUID
    invoice_id: Optional[UUID] = None
    reason: DisputeReason
    description: Optional[str] = None
    amount_disputed: Decimal = Decimal("0.00")
    assigned_to: Optional[UUID] = None


class DisputeStatusUpdate(BaseModel):
    status: DisputeStatus
    resolution: Optional[str] = None
    resolved_amount: Optional[Decimal] = None


class DisputeDocumentResponse(BaseModel):
    id: UUID
    dispute_id: UUID
    filename: str
    file_size: Optional[int] = None
    content_type: Optional[str] = None
    uploaded_by: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DisputeResponse(BaseModel):
    id: UUID
    dispute_number: str
    customer_id: UUID
    invoice_id: Optional[UUID] = None
    status: DisputeStatus
    reason: DisputeReason
    description: Optional[str] = None
    amount_disputed: Decimal
    resolution: Optional[str] = None
    resolved_amount: Optional[Decimal] = None
    assigned_to: Optional[UUID] = None
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    documents: List[DisputeDocumentResponse] = []

    class Config:
        from_attributes = True


class DisputeListResponse(BaseModel):
    items: List[DisputeResponse]
    total: int
    page: int
    size: int
