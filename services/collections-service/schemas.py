from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime, date
from uuid import UUID
from decimal import Decimal
from models import CollectionActionType, CollectionStatus


class DunningRuleCreate(BaseModel):
    name: str
    days_overdue_min: int
    days_overdue_max: Optional[int] = None
    action_type: CollectionActionType
    template: Optional[str] = None
    subject: Optional[str] = None
    priority: int = 1
    is_active: bool = True


class DunningRuleUpdate(BaseModel):
    name: Optional[str] = None
    days_overdue_min: Optional[int] = None
    days_overdue_max: Optional[int] = None
    action_type: Optional[CollectionActionType] = None
    template: Optional[str] = None
    subject: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None


class DunningRuleResponse(BaseModel):
    id: UUID
    name: str
    days_overdue_min: int
    days_overdue_max: Optional[int] = None
    action_type: CollectionActionType
    template: Optional[str] = None
    subject: Optional[str] = None
    priority: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CollectionActionResponse(BaseModel):
    id: UUID
    customer_id: UUID
    invoice_id: Optional[UUID] = None
    action_type: CollectionActionType
    status: CollectionStatus
    scheduled_date: Optional[datetime] = None
    executed_date: Optional[datetime] = None
    notes: Optional[str] = None
    result: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CollectionQueueItem(BaseModel):
    customer_id: str
    customer_name: str
    total_overdue: Decimal
    days_overdue: int
    last_contact: Optional[date] = None
    risk_level: str
    open_invoices: int
    invoices: List[dict] = []


class OverdueInvoice(BaseModel):
    invoice_id: str
    invoice_number: str
    customer_id: str
    customer_name: str
    due_date: date
    days_overdue: int
    balance_due: Decimal
    total_amount: Decimal


class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    stages: List[Any] = []
    is_active: bool = True


class WorkflowResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    is_active: bool
    stages: List[Any]
    created_at: datetime

    class Config:
        from_attributes = True
