from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException, status
from typing import List, Optional
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from models import CollectionAction, CollectionWorkflow, DunningRule, CollectionActionType, CollectionStatus
from schemas import CollectionQueueItem, OverdueInvoice


def get_overdue_invoices(db: Session) -> List[OverdueInvoice]:
    today = date.today()
    result = db.execute(text("""
        SELECT
            i.id::text as invoice_id,
            i.invoice_number,
            i.customer_id::text,
            c.name as customer_name,
            i.due_date,
            (CURRENT_DATE - i.due_date) as days_overdue,
            i.balance_due,
            i.total_amount
        FROM invoices i
        JOIN customers c ON c.id = i.customer_id
        WHERE i.status NOT IN ('void', 'paid', 'draft')
          AND i.due_date < CURRENT_DATE
          AND i.balance_due > 0
        ORDER BY i.due_date ASC
    """))

    overdue = []
    for row in result:
        overdue.append(OverdueInvoice(
            invoice_id=row.invoice_id,
            invoice_number=row.invoice_number,
            customer_id=row.customer_id,
            customer_name=row.customer_name,
            due_date=row.due_date,
            days_overdue=row.days_overdue or 0,
            balance_due=Decimal(str(row.balance_due)),
            total_amount=Decimal(str(row.total_amount)),
        ))
    return overdue


def get_collection_queue(db: Session) -> List[CollectionQueueItem]:
    result = db.execute(text("""
        SELECT
            i.customer_id::text,
            c.name as customer_name,
            SUM(i.balance_due) as total_overdue,
            MAX(CURRENT_DATE - i.due_date) as max_days_overdue,
            COUNT(i.id) as open_invoices,
            cp.risk_level,
            (SELECT MAX(ca.executed_date::date)
             FROM collection_actions ca
             WHERE ca.customer_id = i.customer_id
               AND ca.status = 'executed') as last_contact
        FROM invoices i
        JOIN customers c ON c.id = i.customer_id
        LEFT JOIN credit_profiles cp ON cp.customer_id = i.customer_id
        WHERE i.status NOT IN ('void', 'paid', 'draft')
          AND i.due_date < CURRENT_DATE
          AND i.balance_due > 0
        GROUP BY i.customer_id, c.name, cp.risk_level
        ORDER BY total_overdue DESC
    """))

    queue = []
    for row in result:
        item = CollectionQueueItem(
            customer_id=row.customer_id,
            customer_name=row.customer_name,
            total_overdue=Decimal(str(row.total_overdue)),
            days_overdue=row.max_days_overdue or 0,
            last_contact=row.last_contact,
            risk_level=row.risk_level or "low",
            open_invoices=row.open_invoices,
        )
        queue.append(item)
    return queue


def run_dunning_workflow(db: Session, customer_id: Optional[UUID] = None, user_id: Optional[str] = None) -> dict:
    today = date.today()
    dunning_rules = db.query(DunningRule).filter(DunningRule.is_active == True).order_by(
        DunningRule.days_overdue_min.asc()
    ).all()

    query = text("""
        SELECT
            i.id::text as invoice_id,
            i.invoice_number,
            i.customer_id::text,
            c.name as customer_name,
            c.email as customer_email,
            (CURRENT_DATE - i.due_date) as days_overdue,
            i.balance_due,
            i.total_amount
        FROM invoices i
        JOIN customers c ON c.id = i.customer_id
        WHERE i.status NOT IN ('void', 'paid', 'draft')
          AND i.due_date < CURRENT_DATE
          AND i.balance_due > 0
          {}
        ORDER BY i.due_date ASC
    """.format("AND i.customer_id = :customer_id" if customer_id else ""))

    params = {}
    if customer_id:
        params["customer_id"] = str(customer_id)

    result = db.execute(query, params)
    invoices = result.fetchall()
    actions_created = 0

    for invoice in invoices:
        days_overdue = invoice.days_overdue or 0
        applicable_rule = None
        for rule in dunning_rules:
            if days_overdue >= rule.days_overdue_min:
                if rule.days_overdue_max is None or days_overdue <= rule.days_overdue_max:
                    applicable_rule = rule
                    break

        if applicable_rule:
            # Check if action already executed today
            existing = db.execute(text("""
                SELECT id FROM collection_actions
                WHERE invoice_id = :invoice_id
                  AND action_type = :action_type
                  AND status = 'executed'
                  AND executed_date::date = CURRENT_DATE
            """), {"invoice_id": invoice.invoice_id, "action_type": applicable_rule.action_type.value})

            if not existing.fetchone():
                action = CollectionAction(
                    customer_id=invoice.customer_id,
                    invoice_id=invoice.invoice_id,
                    action_type=applicable_rule.action_type,
                    status=CollectionStatus.executed,
                    scheduled_date=datetime.utcnow(),
                    executed_date=datetime.utcnow(),
                    notes=f"Dunning rule: {applicable_rule.name} - Day {days_overdue} overdue",
                    created_by=user_id,
                )
                db.add(action)
                actions_created += 1

    db.commit()
    return {"actions_created": actions_created, "invoices_processed": len(invoices)}


def send_dunning_notification(db: Session, invoice_id: UUID, template: str) -> dict:
    result = db.execute(text("""
        SELECT i.invoice_number, c.name, c.email, i.balance_due, i.due_date
        FROM invoices i
        JOIN customers c ON c.id = i.customer_id
        WHERE i.id = :invoice_id
    """), {"invoice_id": str(invoice_id)})
    invoice = result.fetchone()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    return {
        "sent": True,
        "recipient": invoice.email,
        "invoice_number": invoice.invoice_number,
        "message": f"Notification queued for {invoice.name}"
    }


def calculate_late_fee(db: Session, invoice_id: UUID, fee_rate: float = 0.015) -> dict:
    result = db.execute(text("""
        SELECT id, balance_due, due_date, (CURRENT_DATE - due_date) as days_overdue
        FROM invoices
        WHERE id = :invoice_id AND status NOT IN ('void', 'paid')
    """), {"invoice_id": str(invoice_id)})
    invoice = result.fetchone()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    days_overdue = invoice.days_overdue or 0
    balance = Decimal(str(invoice.balance_due))
    months_overdue = max(1, days_overdue // 30)
    late_fee = balance * Decimal(str(fee_rate)) * months_overdue

    return {
        "invoice_id": str(invoice_id),
        "balance_due": float(balance),
        "days_overdue": days_overdue,
        "late_fee_rate": fee_rate,
        "calculated_fee": float(late_fee),
    }
