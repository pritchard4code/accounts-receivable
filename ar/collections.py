"""Automated Collections & Dunning (FR-AR-020 – FR-AR-022)."""
from datetime import date
from decimal import Decimal
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, jsonify, current_app)
from flask_login import login_required, current_user
from models import db, Invoice, DunningRule, DunningLog, Customer
from ar.utils import role_required, log_action

collections_bp = Blueprint("collections", __name__)


# ── Dunning engine ────────────────────────────────────────────────────────────

def run_dunning_cycle(app=None):
    """
    Core dunning engine — called nightly via APScheduler or manually.
    For each overdue invoice not in dispute, find matching DunningRules
    that haven't been executed yet and fire them.
    (FR-AR-020, FR-AR-021, FR-AR-022)
    """
    ctx = app.app_context() if app else current_app._get_current_object().app_context()
    with ctx:
        today = date.today()
        overdue = Invoice.query.filter(
            Invoice.due_date < today,
            Invoice.status.in_(["sent", "partial"]),
        ).all()

        fired = 0
        for invoice in overdue:
            # Skip disputed invoices (FR-AR-052)
            if invoice.dispute and invoice.dispute.status == "open":
                continue

            days_late = (today - invoice.due_date).days
            risk = _risk_profile(invoice.customer)

            rules = DunningRule.query.filter(
                DunningRule.is_active == True,
                DunningRule.days_past_due <= days_late,
                DunningRule.risk_profile.in_(["all", risk]),
            ).order_by(DunningRule.days_past_due.asc()).all()

            for rule in rules:
                already_sent = DunningLog.query.filter_by(
                    invoice_id=invoice.id, rule_id=rule.id
                ).first()
                if already_sent:
                    continue

                _fire_dunning(invoice, rule)
                fired += 1

        db.session.commit()
        return fired


def _risk_profile(customer):
    if customer.risk_score >= 70:
        return "high"
    elif customer.risk_score >= 40:
        return "medium"
    return "low"


def _fire_dunning(invoice, rule):
    from ar.utils import render_dunning_email, send_dunning_email

    subject, body = render_dunning_email(rule.template_name, invoice)
    recipient = invoice.customer.email

    success = True
    if rule.channel == "email" and recipient:
        success = send_dunning_email(recipient, subject, body)

    log_entry = DunningLog(
        invoice_id=invoice.id,
        rule_id=rule.id,
        channel=rule.channel,
        recipient=recipient,
        subject=subject,
        body_preview=body[:500] if body else "",
        status="sent" if success else "failed",
    )
    db.session.add(log_entry)

    # Apply late fee if configured (FR-AR-022)
    if rule.apply_late_fee:
        _apply_late_fee(invoice)


def _apply_late_fee(invoice):
    from flask import current_app
    rate = Decimal(str(current_app.config.get("LATE_FEE_RATE", "0.015")))
    fee = (invoice.balance_due * rate).quantize(Decimal("0.01"))
    if fee > 0:
        invoice.late_fee_amount = (invoice.late_fee_amount or Decimal("0.00")) + fee
        invoice.total_amount += fee
        invoice.balance_due += fee


# ── Web routes ────────────────────────────────────────────────────────────────

@collections_bp.route("/")
@login_required
def queue():
    """Collections queue — overdue invoices grouped by aging bucket."""
    today = date.today()
    overdue = Invoice.query.filter(
        Invoice.due_date < today,
        Invoice.status.in_(["sent", "partial"]),
    ).order_by(Invoice.due_date.asc()).all()

    buckets = {"1-30": [], "31-60": [], "61-90": [], "90+": []}
    for inv in overdue:
        b = inv.aging_bucket
        if b in buckets:
            buckets[b].append(inv)

    return render_template("collections/queue.html", buckets=buckets, today=today)


@collections_bp.route("/run-dunning", methods=["POST"])
@login_required
@role_required("collections_specialist", "finance_manager", "admin")
def trigger_dunning():
    fired = run_dunning_cycle()
    flash(f"Dunning cycle complete — {fired} notice(s) sent.", "success")
    return redirect(url_for("collections.queue"))


@collections_bp.route("/rules")
@login_required
@role_required("finance_manager", "admin")
def dunning_rules():
    rules = DunningRule.query.order_by(DunningRule.sort_order).all()
    return render_template("collections/rules.html", rules=rules)


@collections_bp.route("/rules/new", methods=["GET", "POST"])
@login_required
@role_required("finance_manager", "admin")
def new_rule():
    if request.method == "POST":
        rule = DunningRule(
            name=request.form["name"],
            days_past_due=int(request.form["days_past_due"]),
            risk_profile=request.form.get("risk_profile", "all"),
            channel=request.form.get("channel", "email"),
            template_name=request.form.get("template_name", "dunning_reminder"),
            apply_late_fee=bool(request.form.get("apply_late_fee")),
            sort_order=int(request.form.get("sort_order", 0)),
        )
        db.session.add(rule)
        db.session.commit()
        flash("Dunning rule created.", "success")
        return redirect(url_for("collections.dunning_rules"))
    return render_template("collections/new_rule.html")


@collections_bp.route("/rules/<int:rule_id>/toggle", methods=["POST"])
@login_required
@role_required("finance_manager", "admin")
def toggle_rule(rule_id):
    rule = db.get_or_404(DunningRule, rule_id)
    rule.is_active = not rule.is_active
    db.session.commit()
    flash(f"Rule {'activated' if rule.is_active else 'deactivated'}.", "info")
    return redirect(url_for("collections.dunning_rules"))
