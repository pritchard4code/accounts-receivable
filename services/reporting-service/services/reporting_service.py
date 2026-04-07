from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import date, datetime, timedelta
from decimal import Decimal


def get_ar_aging_report(db: Session, as_of_date: Optional[date] = None) -> dict:
    if not as_of_date:
        as_of_date = date.today()

    result = db.execute(text("""
        SELECT
            i.customer_id::text,
            c.name as customer_name,
            SUM(CASE WHEN i.due_date >= :today THEN i.balance_due ELSE 0 END) as current_amount,
            SUM(CASE WHEN i.due_date < :today AND i.due_date >= :day30 THEN i.balance_due ELSE 0 END) as days_1_30,
            SUM(CASE WHEN i.due_date < :day30 AND i.due_date >= :day60 THEN i.balance_due ELSE 0 END) as days_31_60,
            SUM(CASE WHEN i.due_date < :day60 AND i.due_date >= :day90 THEN i.balance_due ELSE 0 END) as days_61_90,
            SUM(CASE WHEN i.due_date < :day90 THEN i.balance_due ELSE 0 END) as days_over_90,
            SUM(i.balance_due) as total
        FROM invoices i
        JOIN customers c ON c.id = i.customer_id
        WHERE i.status NOT IN ('void', 'paid', 'draft')
          AND i.balance_due > 0
        GROUP BY i.customer_id, c.name
        ORDER BY total DESC
    """), {
        "today": as_of_date,
        "day30": as_of_date - timedelta(days=30),
        "day60": as_of_date - timedelta(days=60),
        "day90": as_of_date - timedelta(days=90),
    })

    buckets = []
    totals = {"customer_id": "TOTAL", "customer_name": "Grand Total",
              "current": 0, "days_1_30": 0, "days_31_60": 0, "days_61_90": 0, "days_over_90": 0, "total": 0}

    for row in result:
        bucket = {
            "customer_id": row.customer_id,
            "customer_name": row.customer_name,
            "current": float(row.current_amount or 0),
            "days_1_30": float(row.days_1_30 or 0),
            "days_31_60": float(row.days_31_60 or 0),
            "days_61_90": float(row.days_61_90 or 0),
            "days_over_90": float(row.days_over_90 or 0),
            "total": float(row.total or 0),
        }
        buckets.append(bucket)
        for k in ["current", "days_1_30", "days_31_60", "days_61_90", "days_over_90", "total"]:
            totals[k] += bucket[k]

    return {"as_of_date": str(as_of_date), "buckets": buckets, "totals": totals}


def get_dso_metric(db: Session, days: int = 30) -> dict:
    result = db.execute(text("""
        WITH recent_revenue AS (
            SELECT COALESCE(SUM(total_amount), 0) as total_rev
            FROM invoices
            WHERE invoice_date >= CURRENT_DATE - INTERVAL ':days days'
              AND status != 'void'
        ),
        outstanding_ar AS (
            SELECT COALESCE(SUM(balance_due), 0) as total_ar
            FROM invoices
            WHERE status NOT IN ('void', 'paid', 'draft')
        )
        SELECT
            o.total_ar,
            r.total_rev,
            CASE WHEN r.total_rev > 0 THEN (o.total_ar / r.total_rev) * :days ELSE 0 END as dso
        FROM outstanding_ar o, recent_revenue r
    """.replace(":days days", f"{days} days")), {"days": days})

    row = result.fetchone()
    if row:
        return {
            "dso": round(float(row.dso or 0), 1),
            "total_ar": float(row.total_ar or 0),
            "total_revenue": float(row.total_rev or 0),
            "period_days": days,
        }
    return {"dso": 0, "total_ar": 0, "total_revenue": 0, "period_days": days}


def get_cash_collection_trend(db: Session, months: int = 6) -> list:
    result = db.execute(text("""
        SELECT
            DATE_TRUNC('month', payment_date) as month,
            SUM(amount) as collected,
            COUNT(*) as payment_count
        FROM payments
        WHERE payment_date >= CURRENT_DATE - INTERVAL ':months months'
          AND status != 'voided'
        GROUP BY DATE_TRUNC('month', payment_date)
        ORDER BY month ASC
    """.replace(":months months", f"{months} months")))

    trend = []
    for row in result:
        trend.append({
            "month": row.month.strftime("%Y-%m") if row.month else None,
            "collected": float(row.collected or 0),
            "payment_count": row.payment_count,
        })
    return trend


def get_customer_payment_history(db: Session, customer_id: str) -> dict:
    invoices_result = db.execute(text("""
        SELECT
            invoice_number, invoice_date, due_date, total_amount,
            paid_amount, balance_due, status
        FROM invoices
        WHERE customer_id = :cid
        ORDER BY invoice_date DESC
        LIMIT 50
    """), {"cid": customer_id})

    payments_result = db.execute(text("""
        SELECT
            payment_number, payment_date, amount, payment_method, status, reference
        FROM payments
        WHERE customer_id = :cid
        ORDER BY payment_date DESC
        LIMIT 50
    """), {"cid": customer_id})

    invoices = [dict(row._mapping) for row in invoices_result]
    payments = [dict(row._mapping) for row in payments_result]

    # Serialize dates
    for inv in invoices:
        for k, v in inv.items():
            if hasattr(v, 'isoformat'):
                inv[k] = v.isoformat()
    for pmt in payments:
        for k, v in pmt.items():
            if hasattr(v, 'isoformat'):
                pmt[k] = v.isoformat()

    return {
        "customer_id": customer_id,
        "invoices": invoices,
        "payments": payments,
    }


def get_collector_performance(db: Session) -> list:
    result = db.execute(text("""
        SELECT
            u.id::text as user_id,
            u.username,
            u.first_name,
            u.last_name,
            COUNT(DISTINCT ca.customer_id) as customers_worked,
            COUNT(ca.id) as actions_taken,
            SUM(CASE WHEN ca.action_type = 'email' THEN 1 ELSE 0 END) as emails_sent,
            SUM(CASE WHEN ca.action_type = 'phone' THEN 1 ELSE 0 END) as calls_made
        FROM users u
        LEFT JOIN collection_actions ca ON ca.created_by = u.id
            AND ca.created_at >= CURRENT_DATE - INTERVAL '30 days'
        WHERE u.role IN ('collections_specialist', 'ar_clerk')
          AND u.is_active = TRUE
        GROUP BY u.id, u.username, u.first_name, u.last_name
        ORDER BY actions_taken DESC
    """))

    performance = []
    for row in result:
        performance.append({
            "user_id": row.user_id,
            "username": row.username,
            "name": f"{row.first_name or ''} {row.last_name or ''}".strip(),
            "customers_worked": row.customers_worked,
            "actions_taken": row.actions_taken,
            "emails_sent": row.emails_sent,
            "calls_made": row.calls_made,
        })
    return performance


def get_cash_flow_forecast(db: Session, days: int = 90) -> list:
    result = db.execute(text("""
        SELECT
            due_date,
            SUM(balance_due) as expected_amount,
            COUNT(*) as invoice_count
        FROM invoices
        WHERE status NOT IN ('void', 'paid', 'draft')
          AND due_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL ':days days'
          AND balance_due > 0
        GROUP BY due_date
        ORDER BY due_date ASC
    """.replace(":days days", f"{days} days")))

    forecast = []
    cumulative = 0.0
    for row in result:
        amount = float(row.expected_amount or 0)
        cumulative += amount
        forecast.append({
            "date": row.due_date.isoformat() if row.due_date else None,
            "expected_amount": amount,
            "invoice_count": row.invoice_count,
            "cumulative": cumulative,
        })
    return forecast


def get_dashboard_kpis(db: Session) -> dict:
    result = db.execute(text("""
        SELECT
            COALESCE(SUM(CASE WHEN status NOT IN ('void', 'paid', 'draft') THEN balance_due END), 0) as total_receivables,
            COALESCE(SUM(CASE WHEN status NOT IN ('void', 'paid', 'draft')
                AND due_date < CURRENT_DATE THEN balance_due END), 0) as overdue_amount,
            COUNT(CASE WHEN status NOT IN ('void', 'paid', 'draft')
                AND due_date < CURRENT_DATE THEN 1 END) as overdue_count,
            COALESCE(SUM(CASE WHEN EXTRACT(MONTH FROM invoice_date) = EXTRACT(MONTH FROM CURRENT_DATE)
                AND EXTRACT(YEAR FROM invoice_date) = EXTRACT(YEAR FROM CURRENT_DATE)
                AND status != 'void' THEN total_amount END), 0) as monthly_billed
        FROM invoices
    """))

    inv_row = result.fetchone()

    payments_result = db.execute(text("""
        SELECT
            COALESCE(SUM(CASE WHEN EXTRACT(MONTH FROM payment_date) = EXTRACT(MONTH FROM CURRENT_DATE)
                AND EXTRACT(YEAR FROM payment_date) = EXTRACT(YEAR FROM CURRENT_DATE)
                AND status != 'voided' THEN amount END), 0) as current_month_collections,
            COALESCE(SUM(CASE WHEN status != 'voided' THEN amount END), 0) as total_collected_90d
        FROM payments
        WHERE payment_date >= CURRENT_DATE - INTERVAL '90 days'
    """))

    pmt_row = payments_result.fetchone()

    total_receivables = float(inv_row.total_receivables or 0)
    overdue_amount = float(inv_row.overdue_amount or 0)
    monthly_billed = float(inv_row.monthly_billed or 0)
    total_collected = float(pmt_row.total_collected_90d or 0)
    current_month_collections = float(pmt_row.current_month_collections or 0)

    collection_rate = (total_collected / max(monthly_billed * 3, 1)) * 100 if monthly_billed > 0 else 0

    # DSO approximation
    dso_result = db.execute(text("""
        SELECT
            CASE WHEN SUM(total_amount) > 0
            THEN (SUM(CASE WHEN status NOT IN ('void', 'paid', 'draft') THEN balance_due ELSE 0 END) /
                  SUM(CASE WHEN invoice_date >= CURRENT_DATE - INTERVAL '30 days' AND status != 'void'
                      THEN total_amount ELSE 0 END) * 30)
            ELSE 0 END as dso
        FROM invoices
        WHERE invoice_date >= CURRENT_DATE - INTERVAL '90 days'
    """))
    dso_row = dso_result.fetchone()
    dso = round(float(dso_row.dso or 0), 1)

    return {
        "total_receivables": total_receivables,
        "dso": dso,
        "overdue_amount": overdue_amount,
        "overdue_count": inv_row.overdue_count or 0,
        "collection_rate": round(min(collection_rate, 100), 1),
        "current_month_collections": current_month_collections,
        "monthly_billed": monthly_billed,
    }
