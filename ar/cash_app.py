"""Cash Application & Reconciliation (FR-AR-030 – FR-AR-033)."""
from decimal import Decimal
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, jsonify)
from flask_login import login_required, current_user
from models import db, Payment, Invoice, PaymentAllocation, GLEntry, AuditLog
from ar.utils import role_required, log_action

cash_bp = Blueprint("cash", __name__)

TOLERANCE_PCT = Decimal("0.01")   # 1% — overridden by config at runtime


# ── Auto-match engine (FR-AR-030) ────────────────────────────────────────────

def auto_match_payment(payment):
    """
    Attempt to automatically match a payment to open invoices using:
      1. Invoice number in reference_number
      2. Exact amount match
      3. Customer + amount within tolerance
    Returns list of (invoice, amount) tuples that were matched.
    """
    from flask import current_app
    tol_pct = Decimal(str(current_app.config.get("PAYMENT_TOLERANCE_PCT", "0.01")))
    customer_invoices = Invoice.query.filter(
        Invoice.customer_id == payment.customer_id,
        Invoice.status.in_(["sent", "partial"]),
    ).order_by(Invoice.due_date.asc()).all()

    matched = []
    remaining = payment.amount

    # Pass 1: exact invoice-number match in reference
    if payment.reference_number:
        ref = payment.reference_number.strip().upper()
        for inv in customer_invoices:
            if inv.invoice_number.upper() in ref and inv.balance_due <= remaining:
                matched.append((inv, inv.balance_due))
                remaining -= inv.balance_due

    # Pass 2: amount match (with tolerance)
    if not matched:
        for inv in customer_invoices:
            diff = abs(inv.balance_due - remaining) / inv.balance_due if inv.balance_due else Decimal("1")
            if diff <= tol_pct:
                matched.append((inv, min(inv.balance_due, remaining)))
                remaining -= matched[-1][1]
                break

    # Pass 3: oldest-first fill
    if not matched:
        for inv in customer_invoices:
            if remaining <= 0:
                break
            alloc_amt = min(inv.balance_due, remaining)
            matched.append((inv, alloc_amt))
            remaining -= alloc_amt

    return matched, remaining


def apply_allocations(payment, matches, manual=False):
    """Persist allocation records and update invoice balances."""
    from datetime import datetime, timezone
    for inv, amt in matches:
        alloc = PaymentAllocation(
            payment_id=payment.id,
            invoice_id=inv.id,
            amount_allocated=amt,
            allocated_by_id=current_user.id if manual else None,
            is_manual=manual,
        )
        db.session.add(alloc)

        inv.amount_paid = (inv.amount_paid or Decimal("0.00")) + amt
        inv.balance_due = inv.total_amount - inv.amount_paid
        if inv.balance_due <= Decimal("0.00"):
            inv.status = "paid"
            inv.paid_at = datetime.now(timezone.utc)
        else:
            inv.status = "partial"

        payment.amount_applied = (payment.amount_applied or Decimal("0.00")) + amt

    payment.amount_unapplied = payment.amount - payment.amount_applied
    payment.status = "applied" if payment.amount_unapplied <= 0 else "posted"

    log_action("payment_applied", "Payment", payment.id,
               new_data={"applied": str(payment.amount_applied),
                         "unapplied": str(payment.amount_unapplied)})


# ── Routes ────────────────────────────────────────────────────────────────────

@cash_bp.route("/apply/<int:payment_id>", methods=["GET", "POST"])
@login_required
@role_required("ar_clerk", "finance_manager", "admin")
def apply_payment(payment_id):
    payment = db.get_or_404(Payment, payment_id)

    open_invoices = Invoice.query.filter(
        Invoice.customer_id == payment.customer_id,
        Invoice.status.in_(["sent", "partial"]),
    ).order_by(Invoice.due_date.asc()).all()

    if request.method == "POST":
        action = request.form.get("action")

        if action == "auto":
            matches, unapplied = auto_match_payment(payment)
            if matches:
                apply_allocations(payment, matches, manual=False)
                db.session.commit()
                flash(f"Auto-matched {len(matches)} invoice(s). "
                      f"Unapplied: ${unapplied:,.2f}", "success")
            else:
                flash("No automatic match found. Please apply manually.", "warning")
            return redirect(url_for("cash.apply_payment", payment_id=payment_id))

        if action == "manual":
            invoice_ids = request.form.getlist("invoice_id[]", type=int)
            amounts = request.form.getlist("alloc_amount[]")
            matches = []
            for inv_id, amt_str in zip(invoice_ids, amounts):
                try:
                    amt = Decimal(amt_str)
                except Exception:
                    continue
                inv = db.session.get(Invoice, inv_id)
                if inv and amt > 0:
                    matches.append((inv, amt))
            if matches:
                apply_allocations(payment, matches, manual=True)
                db.session.commit()
                flash("Manual allocation saved.", "success")
            return redirect(url_for("cash.apply_payment", payment_id=payment_id))

        if action == "exception":
            payment.status = "exception"
            db.session.commit()
            flash("Payment routed to exception queue.", "warning")
            return redirect(url_for("cash.exceptions"))

    # Auto-suggest on GET
    suggested_matches, _ = auto_match_payment(payment)
    return render_template("cash/apply.html", payment=payment,
                           open_invoices=open_invoices,
                           suggested=suggested_matches)


@cash_bp.route("/exceptions")
@login_required
@role_required("ar_clerk", "finance_manager", "admin")
def exceptions():
    """Unapplied / exception payment queue (FR-AR-031)."""
    ex_payments = Payment.query.filter(
        Payment.status.in_(["exception", "pending"])
    ).order_by(Payment.created_at.asc()).all()
    return render_template("cash/exceptions.html", payments=ex_payments)


@cash_bp.route("/reconciliation")
@login_required
@role_required("finance_manager", "admin")
def reconciliation():
    """GL reconciliation summary (FR-AR-032)."""
    unsynced = GLEntry.query.filter_by(erp_sync_status="pending").count()
    failed = GLEntry.query.filter_by(erp_sync_status="failed").count()
    return render_template("cash/reconciliation.html",
                           unsynced=unsynced, failed=failed)


@cash_bp.route("/api/sync-gl", methods=["POST"])
@login_required
@role_required("finance_manager", "admin")
def sync_gl():
    """Trigger ERP sync for pending GL entries (FR-AR-070)."""
    from ar.utils import push_gl_to_erp
    synced, errors = push_gl_to_erp()
    return jsonify({"synced": synced, "errors": errors})
