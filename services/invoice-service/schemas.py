from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID
from decimal import Decimal
from models import InvoiceStatus


class LineItemCreate(BaseModel):
    description: str
    quantity: Decimal = Decimal("1.000")
    unit_price: Decimal
    tax_rate: Decimal = Decimal("0.0000")
    discount_rate: Decimal = Decimal("0.0000")
    product_code: Optional[str] = None
    line_number: int = 1


class LineItemResponse(BaseModel):
    id: UUID
    invoice_id: UUID
    line_number: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    total_price: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    discount_rate: Decimal
    discount_amount: Decimal
    product_code: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class InvoiceCreate(BaseModel):
    customer_id: UUID
    invoice_date: date
    due_date: date
    currency: str = "USD"
    payment_terms: int = 30
    plan_id: Optional[str] = None
    po_number: Optional[str] = None
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    template_id: Optional[UUID] = None
    line_items: List[LineItemCreate]


class InvoiceUpdate(BaseModel):
    status: Optional[InvoiceStatus] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    currency: Optional[str] = None
    payment_terms: Optional[int] = None
    plan_id: Optional[str] = None
    po_number: Optional[str] = None
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    line_items: Optional[List[LineItemCreate]] = None


class InvoiceResponse(BaseModel):
    id: UUID
    invoice_number: str
    customer_id: UUID
    status: InvoiceStatus
    invoice_date: date
    due_date: date
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    balance_due: Decimal
    currency: str
    payment_terms: int
    plan_id: Optional[str] = None
    po_number: Optional[str] = None
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    sent_at: Optional[datetime] = None
    viewed_at: Optional[datetime] = None
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    line_items: List[LineItemResponse] = []

    class Config:
        from_attributes = True


class InvoiceListResponse(BaseModel):
    items: List[InvoiceResponse]
    total: int
    page: int
    size: int
    pages: int


class AgingBucket(BaseModel):
    customer_id: str
    customer_name: str
    current: Decimal = Decimal("0.00")
    days_1_30: Decimal = Decimal("0.00")
    days_31_60: Decimal = Decimal("0.00")
    days_61_90: Decimal = Decimal("0.00")
    days_over_90: Decimal = Decimal("0.00")
    total: Decimal = Decimal("0.00")


class AgingReport(BaseModel):
    as_of_date: date
    buckets: List[AgingBucket]
    totals: AgingBucket
