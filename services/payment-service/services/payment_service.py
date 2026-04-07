from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException, status
from typing import List, Optional, Tuple
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from models import Payment, PaymentAllocation, PaymentMethod, PaymentStatus
from schemas import PaymentCreate, PaymentUpdate


def generate_payment_number(db: Session) -> str:
    year = datetime.now().year
    count = db.query(Payment).filter(
        Payment.payment_number.like(f"PMT-{year}-%")
    ).count()
    return f"PMT-{year}-{str(count + 1).zfill(4)}"


def create_payment(db: Session, payment_data: PaymentCreate, user_id: str) -> Payment:
    payment_number = generate_payment_number(db)

    payment = Payment(
        payment_number=payment_number,
        customer_id=payment_data.customer_id,
        payment_date=payment_data.payment_date,
        amount=payment_data.amount,
        unapplied_amount=payment_data.amount,
        payment_method=payment_data.payment_method,
        status=PaymentStatus.pending,
        reference=payment_data.reference,
        notes=payment_data.notes,
        recorded_by=user_id,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    if payment_data.auto_apply:
        auto_apply_payment(db, payment.id)
        db.refresh(payment)

    return payment


def apply_payment_to_invoice(db: Session, payment_id: UUID, invoice_id: UUID, amount: Decimal) -> Payment:
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    if payment.unapplied_amount < amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient unapplied amount. Available: {payment.unapplied_amount}"
        )

    # Get invoice and update balance
    result = db.execute(text("""
        UPDATE invoices
        SET paid_amount = paid_amount + :amount,
            balance_due = balance_due - :amount,
            status = CASE
                WHEN balance_due - :amount <= 0 THEN 'paid'::invoice_status
                WHEN paid_amount + :amount > 0 THEN 'partial'::invoice_status
                ELSE status
            END,
            updated_at = NOW()
        WHERE id = :invoice_id AND status NOT IN ('void', 'paid')
        RETURNING id, balance_due
    """), {"amount": float(amount), "invoice_id": str(invoice_id)})

    row = result.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice not found or cannot be applied to"
        )

    allocation = PaymentAllocation(
        payment_id=payment_id,
        invoice_id=invoice_id,
        allocated_amount=amount,
    )
    db.add(allocation)

    payment.unapplied_amount -= amount
    if payment.unapplied_amount <= 0:
        payment.status = PaymentStatus.applied
    else:
        payment.status = PaymentStatus.partially_applied

    db.commit()
    db.refresh(payment)
    return payment


def auto_apply_payment(db: Session, payment_id: UUID) -> Payment:
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    if payment.unapplied_amount <= 0:
        return payment

    # Get oldest open invoices for the customer
    result = db.execute(text("""
        SELECT id, balance_due, invoice_number
        FROM invoices
        WHERE customer_id = :customer_id
          AND status NOT IN ('void', 'paid', 'draft')
          AND balance_due > 0
        ORDER BY due_date ASC, invoice_date ASC
    """), {"customer_id": str(payment.customer_id)})

    invoices = result.fetchall()
    remaining = Decimal(str(payment.unapplied_amount))

    for invoice in invoices:
        if remaining <= 0:
            break
        invoice_balance = Decimal(str(invoice.balance_due))
        apply_amount = min(remaining, invoice_balance)
        apply_payment_to_invoice(db, payment_id, invoice.id, apply_amount)
        remaining -= apply_amount

    db.refresh(payment)
    return payment


def get_payment(db: Session, payment_id: UUID) -> Payment:
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return payment


def list_payments(
    db: Session,
    customer_id: Optional[UUID] = None,
    status_filter: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = 1,
    size: int = 20
) -> Tuple[List[Payment], int]:
    query = db.query(Payment)

    if customer_id:
        query = query.filter(Payment.customer_id == customer_id)
    if status_filter:
        query = query.filter(Payment.status == status_filter)
    if date_from:
        query = query.filter(Payment.payment_date >= date_from)
    if date_to:
        query = query.filter(Payment.payment_date <= date_to)

    total = query.count()
    payments = query.order_by(Payment.created_at.desc()).offset((page - 1) * size).limit(size).all()
    return payments, total


def process_refund(db: Session, payment_id: UUID, amount: Decimal, reason: Optional[str] = None) -> Payment:
    payment = get_payment(db, payment_id)
    if payment.status == PaymentStatus.refunded:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment already refunded")
    if amount > payment.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Refund amount cannot exceed payment amount of {payment.amount}"
        )

    # Reverse invoice applications
    allocations = db.query(PaymentAllocation).filter(PaymentAllocation.payment_id == payment_id).all()
    for alloc in allocations:
        db.execute(text("""
            UPDATE invoices
            SET paid_amount = GREATEST(0, paid_amount - :amount),
                balance_due = balance_due + :amount,
                status = CASE
                    WHEN status = 'paid' THEN 'sent'::invoice_status
                    WHEN balance_due + :amount >= total_amount THEN 'overdue'::invoice_status
                    ELSE status
                END,
                updated_at = NOW()
            WHERE id = :invoice_id
        """), {"amount": float(alloc.allocated_amount), "invoice_id": str(alloc.invoice_id)})

    payment.status = PaymentStatus.refunded
    payment.notes = f"{payment.notes or ''} | REFUNDED: {reason or 'No reason given'}"
    db.commit()
    db.refresh(payment)
    return payment
