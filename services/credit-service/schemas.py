from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID
from decimal import Decimal
from models import RiskLevel


class CreditProfileUpdate(BaseModel):
    credit_limit: Optional[Decimal] = None
    risk_level: Optional[RiskLevel] = None
    notes: Optional[str] = None
    next_review_date: Optional[date] = None


class CreditProfileResponse(BaseModel):
    id: UUID
    customer_id: UUID
    credit_limit: Decimal
    current_balance: Decimal
    available_credit: Decimal
    risk_score: Decimal
    risk_level: RiskLevel
    payment_score: Decimal
    avg_days_to_pay: Decimal
    on_time_payment_rate: Decimal
    late_payment_count: int
    nsf_count: int
    last_review_date: Optional[date] = None
    next_review_date: Optional[date] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CreditAvailabilityRequest(BaseModel):
    customer_id: UUID
    requested_amount: Decimal


class CreditAvailabilityResponse(BaseModel):
    customer_id: str
    requested_amount: Decimal
    available_credit: Decimal
    credit_limit: Decimal
    current_balance: Decimal
    is_available: bool
    message: str


class RiskAssessmentResponse(BaseModel):
    customer_id: str
    customer_name: str
    risk_score: Decimal
    risk_level: RiskLevel
    payment_score: Decimal
    current_balance: Decimal
    credit_limit: Decimal
    days_past_due: int
