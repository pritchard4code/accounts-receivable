from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID
from decimal import Decimal
from models import PaymentMethod, PaymentStatus


class AllocationCreate(BaseModel):
    invoice_id: UUID
    allocated_amount: Decimal


class AllocationResponse(BaseModel):
    id: UUID
    payment_id: UUID
    invoice_id: UUID
    allocated_amount: Decimal
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentCreate(BaseModel):
    customer_id: UUID
    payment_date: date
    amount: Decimal
    payment_method: PaymentMethod
    reference: Optional[str] = None
    notes: Optional[str] = None
    auto_apply: bool = False


class PaymentUpdate(BaseModel):
    payment_date: Optional[date] = None
    reference: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[PaymentStatus] = None


class PaymentResponse(BaseModel):
    id: UUID
    payment_number: str
    customer_id: UUID
    payment_date: date
    amount: Decimal
    unapplied_amount: Decimal
    payment_method: PaymentMethod
    status: PaymentStatus
    reference: Optional[str] = None
    gateway_transaction_id: Optional[str] = None
    notes: Optional[str] = None
    recorded_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    allocations: List[AllocationResponse] = []

    class Config:
        from_attributes = True


class PaymentListResponse(BaseModel):
    items: List[PaymentResponse]
    total: int
    page: int
    size: int


class RefundRequest(BaseModel):
    amount: Decimal
    reason: Optional[str] = None
