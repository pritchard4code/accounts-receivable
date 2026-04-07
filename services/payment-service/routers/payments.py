from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date
from uuid import UUID
from decimal import Decimal
import math

from database import get_db
from schemas import PaymentCreate, PaymentResponse, PaymentListResponse, AllocationCreate, RefundRequest
from services.payment_service import (
    create_payment, get_payment, list_payments,
    apply_payment_to_invoice, auto_apply_payment, process_refund
)
from auth_middleware import get_current_user

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.get("/", response_model=PaymentListResponse)
def list_payments_endpoint(
    customer_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    payments, total = list_payments(db, customer_id, status, date_from, date_to, page, size)
    return PaymentListResponse(items=payments, total=total, page=page, size=size)


@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def create_payment_endpoint(
    payment_data: PaymentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return create_payment(db, payment_data, current_user["id"])


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment_endpoint(
    payment_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return get_payment(db, payment_id)


@router.post("/{payment_id}/apply", response_model=PaymentResponse)
def apply_payment_endpoint(
    payment_id: UUID,
    allocation: AllocationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return apply_payment_to_invoice(db, payment_id, allocation.invoice_id, allocation.allocated_amount)


@router.post("/{payment_id}/auto-apply", response_model=PaymentResponse)
def auto_apply_payment_endpoint(
    payment_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return auto_apply_payment(db, payment_id)


@router.post("/{payment_id}/refund", response_model=PaymentResponse)
def refund_payment_endpoint(
    payment_id: UUID,
    refund_data: RefundRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return process_refund(db, payment_id, refund_data.amount, refund_data.reason)
