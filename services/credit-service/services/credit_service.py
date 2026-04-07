from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException, status
from typing import List, Optional
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from models import CreditProfile, RiskLevel
from schemas import CreditProfileUpdate, CreditAvailabilityResponse, RiskAssessmentResponse


def get_credit_profile(db: Session, customer_id: UUID) -> CreditProfile:
    profile = db.query(CreditProfile).filter(CreditProfile.customer_id == customer_id).first()
    if not profile:
        # Auto-create from customer data
        result = db.execute(text("""
            SELECT id, credit_limit, credit_status FROM customers WHERE id = :cid
        """), {"cid": str(customer_id)})
        customer = result.fetchone()
        if not customer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

        profile = CreditProfile(
            customer_id=customer_id,
            credit_limit=customer.credit_limit or 0,
            current_balance=0,
            available_credit=customer.credit_limit or 0,
            last_review_date=date.today(),
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def update_credit_limit(db: Session, customer_id: UUID, new_limit: Decimal, user_id: str) -> CreditProfile:
    profile = get_credit_profile(db, customer_id)
    old_limit = profile.credit_limit
    profile.credit_limit = new_limit
    profile.available_credit = new_limit - profile.current_balance
    profile.last_review_date = date.today()
    profile.reviewed_by = user_id

    # Also update the customers table
    db.execute(text("""
        UPDATE customers SET credit_limit = :limit, updated_at = NOW() WHERE id = :cid
    """), {"limit": float(new_limit), "cid": str(customer_id)})

    db.commit()
    db.refresh(profile)
    return profile


def check_credit_availability(
    db: Session,
    customer_id: UUID,
    requested_amount: Decimal
) -> CreditAvailabilityResponse:
    profile = get_credit_profile(db, customer_id)
    is_available = profile.available_credit >= requested_amount

    if is_available:
        msg = f"Credit available. {profile.available_credit} of {profile.credit_limit} available."
    else:
        shortfall = requested_amount - profile.available_credit
        msg = f"Insufficient credit. Need {shortfall} more to approve. Available: {profile.available_credit}"

    return CreditAvailabilityResponse(
        customer_id=str(customer_id),
        requested_amount=requested_amount,
        available_credit=profile.available_credit,
        credit_limit=profile.credit_limit,
        current_balance=profile.current_balance,
        is_available=is_available,
        message=msg,
    )


def calculate_risk_score(db: Session, customer_id: UUID) -> CreditProfile:
    profile = get_credit_profile(db, customer_id)

    # Fetch payment history metrics
    result = db.execute(text("""
        SELECT
            COUNT(CASE WHEN i.status = 'overdue' THEN 1 END) as overdue_count,
            COUNT(CASE WHEN i.status IN ('paid', 'partial') THEN 1 END) as paid_count,
            COUNT(*) as total_invoices,
            COALESCE(AVG(CASE WHEN i.status = 'paid'
                THEN EXTRACT(DAY FROM (i.updated_at - i.due_date))
                ELSE NULL END), 0) as avg_days_late,
            COALESCE(SUM(CASE WHEN i.status NOT IN ('void', 'paid', 'draft')
                AND i.due_date < CURRENT_DATE THEN i.balance_due ELSE 0 END), 0) as overdue_balance
        FROM invoices i
        WHERE i.customer_id = :cid
    """), {"cid": str(customer_id)})

    metrics = result.fetchone()
    if not metrics or metrics.total_invoices == 0:
        return profile

    total = metrics.total_invoices or 1
    overdue_rate = (metrics.overdue_count or 0) / total
    avg_days_late = float(metrics.avg_days_late or 0)
    overdue_balance = Decimal(str(metrics.overdue_balance or 0))

    # Calculate risk score (0-100, higher = more risky)
    risk_score = (overdue_rate * 40) + (min(avg_days_late / 90, 1) * 30) + (
        min(float(overdue_balance) / max(float(profile.credit_limit), 1), 1) * 30
    )
    risk_score = min(100, max(0, risk_score * 100))

    # Payment score (0-100, higher = better)
    on_time_rate = ((total - (metrics.overdue_count or 0)) / total) * 100
    payment_score = max(0, min(100, on_time_rate - (avg_days_late * 0.5)))

    # Determine risk level
    if risk_score < 25:
        risk_level = RiskLevel.low
    elif risk_score < 50:
        risk_level = RiskLevel.medium
    elif risk_score < 75:
        risk_level = RiskLevel.high
    else:
        risk_level = RiskLevel.critical

    profile.risk_score = Decimal(str(round(risk_score, 2)))
    profile.risk_level = risk_level
    profile.payment_score = Decimal(str(round(payment_score, 2)))
    profile.on_time_payment_rate = Decimal(str(round(on_time_rate, 2)))
    profile.last_review_date = date.today()

    db.commit()
    db.refresh(profile)
    return profile


def flag_high_risk_customers(db: Session) -> List[RiskAssessmentResponse]:
    result = db.execute(text("""
        SELECT
            cp.customer_id::text,
            c.name as customer_name,
            cp.risk_score,
            cp.risk_level,
            cp.payment_score,
            cp.current_balance,
            cp.credit_limit,
            COALESCE(MAX(CURRENT_DATE - i.due_date), 0) as days_past_due
        FROM credit_profiles cp
        JOIN customers c ON c.id = cp.customer_id
        LEFT JOIN invoices i ON i.customer_id = cp.customer_id
            AND i.status NOT IN ('void', 'paid', 'draft')
            AND i.due_date < CURRENT_DATE
        WHERE cp.risk_level IN ('high', 'critical')
        GROUP BY cp.customer_id, c.name, cp.risk_score, cp.risk_level,
                 cp.payment_score, cp.current_balance, cp.credit_limit
        ORDER BY cp.risk_score DESC
    """))

    assessments = []
    for row in result:
        assessments.append(RiskAssessmentResponse(
            customer_id=row.customer_id,
            customer_name=row.customer_name,
            risk_score=Decimal(str(row.risk_score)),
            risk_level=row.risk_level,
            payment_score=Decimal(str(row.payment_score)),
            current_balance=Decimal(str(row.current_balance)),
            credit_limit=Decimal(str(row.credit_limit)),
            days_past_due=row.days_past_due or 0,
        ))
    return assessments


def get_all_credit_profiles(db: Session) -> list:
    return db.query(CreditProfile).order_by(CreditProfile.risk_level.desc()).all()
