"""Credit & Risk Management (FR-AR-040 – FR-AR-042)."""
from decimal import Decimal
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, jsonify)
from flask_login import login_required, current_user
from models import db, Customer, CreditEvent, Invoice
from ar.utils import role_required, log_action

credit_bp = Blueprint("credit", __name__)


def _recalculate_risk_score(customer):
    """
    Simple scoring model:
      - Days average overdue in last 12 months  → up to 50 pts
      - # of invoices sent to collections       → up to 30 pts
      - Outstanding / credit limit ratio        → up to 20 pts
    """
    from datetime import date, timedelta
    cutoff = date.today() - timedelta(days=365)
    paid_invoices = Invoice.query.filter(
        Invoice.customer_id == customer.id,
        Invoice.status == "paid",
        Invoice.paid_at >= cutoff,
    ).all()

    avg_days_late = 0.0
    if paid_invoices:
        late_days = [(i.paid_at.date() - i.due_date).days for i in paid_invoices
                     if i.paid_at and i.paid_at.date() > i.due_date]
        avg_days_late = sum(late_days) / len(paid_invoices) if late_days else 0.0

    collections_count = Invoice.query.filter(
        Invoice.customer_id == customer.id,
        Invoice.status == "overdue",
    ).count()

    utilisation = float(customer.outstanding_balance / customer.credit_limit) \
        if customer.credit_limit else 0.0

    score = min(50, int(avg_days_late * 1.5))
    score += min(30, collections_count * 5)
    score += min(20, int(utilisation * 20))
    return max(0, min(100, score))


# ── Routes ────────────────────────────────────────────────────────────────────

@credit_bp.route("/")
@login_required
@role_required("credit_manager", "finance_manager", "admin")
def customer_list():
    customers = Customer.query.filter_by(is_active=True).order_by(
        Customer.risk_score.desc()).all()
    return render_template("credit/list.html", customers=customers)


@credit_bp.route("/<int:customer_id>")
@login_required
def customer_profile(customer_id):
    customer = db.get_or_404(Customer, customer_id)
    events = CreditEvent.query.filter_by(customer_id=customer_id)\
        .order_by(CreditEvent.created_at.desc()).limit(50).all()
    return render_template("credit/profile.html", customer=customer, events=events)


@credit_bp.route("/<int:customer_id>/update-limit", methods=["POST"])
@login_required
@role_required("credit_manager", "finance_manager", "admin")
def update_limit(customer_id):
    customer = db.get_or_404(Customer, customer_id)
    new_limit = Decimal(request.form.get("credit_limit", str(customer.credit_limit)))
    reason = request.form.get("reason", "")

    event = CreditEvent(
        customer_id=customer_id,
        event_type="limit_change",
        old_value=str(customer.credit_limit),
        new_value=str(new_limit),
        reason=reason,
        created_by_id=current_user.id,
    )
    customer.credit_limit = new_limit
    db.session.add(event)
    db.session.commit()
    flash(f"Credit limit updated to ${new_limit:,.2f}.", "success")
    return redirect(url_for("credit.customer_profile", customer_id=customer_id))


@credit_bp.route("/<int:customer_id>/set-status", methods=["POST"])
@login_required
@role_required("credit_manager", "finance_manager", "admin")
def set_status(customer_id):
    customer = db.get_or_404(Customer, customer_id)
    new_status = request.form.get("credit_status")
    reason = request.form.get("reason", "")

    valid = {"good", "watch", "hold", "suspended"}
    if new_status not in valid:
        flash("Invalid status.", "danger")
        return redirect(url_for("credit.customer_profile", customer_id=customer_id))

    event = CreditEvent(
        customer_id=customer_id,
        event_type="status_change",
        old_value=customer.credit_status,
        new_value=new_status,
        reason=reason,
        created_by_id=current_user.id,
    )
    customer.credit_status = new_status
    db.session.add(event)
    db.session.commit()
    flash(f"Credit status set to '{new_status}'.", "info")
    return redirect(url_for("credit.customer_profile", customer_id=customer_id))


@credit_bp.route("/<int:customer_id>/refresh-score", methods=["POST"])
@login_required
@role_required("credit_manager", "finance_manager", "admin")
def refresh_score(customer_id):
    customer = db.get_or_404(Customer, customer_id)
    old_score = customer.risk_score
    customer.risk_score = _recalculate_risk_score(customer)

    # Auto-flag high-risk (FR-AR-041)
    if customer.risk_score >= 70 and customer.credit_status == "good":
        customer.credit_status = "watch"
        event = CreditEvent(
            customer_id=customer_id, event_type="flag_raised",
            old_value="good", new_value="watch",
            reason=f"Automated: risk score rose to {customer.risk_score}",
            created_by_id=current_user.id,
        )
        db.session.add(event)
        flash(f"Risk score is {customer.risk_score} — customer auto-flagged to 'watch'.", "warning")

    db.session.commit()
    flash(f"Risk score updated: {old_score} → {customer.risk_score}.", "info")
    return redirect(url_for("credit.customer_profile", customer_id=customer_id))


@credit_bp.route("/api/check", methods=["POST"])
@login_required
def check_credit():
    """JSON endpoint for real-time credit check before new sales order (FR-AR-042)."""
    data = request.get_json()
    customer_id = data.get("customer_id")
    requested_amount = Decimal(str(data.get("amount", "0")))

    customer = db.session.get(Customer, customer_id)
    if not customer:
        return jsonify({"approved": False, "reason": "Customer not found"}), 404

    if customer.credit_status in ("hold", "suspended"):
        return jsonify({"approved": False, "reason": f"Account on {customer.credit_status}",
                        "credit_status": customer.credit_status})

    if customer.outstanding_balance + requested_amount > customer.credit_limit:
        return jsonify({
            "approved": False,
            "reason": "Would exceed credit limit",
            "available_credit": float(customer.available_credit),
            "requested": float(requested_amount),
        })

    return jsonify({"approved": True, "available_credit": float(customer.available_credit)})
