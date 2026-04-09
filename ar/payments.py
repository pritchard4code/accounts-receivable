"""Digital Payment Processing (FR-AR-010 – FR-AR-013)."""
from datetime import date
from decimal import Decimal
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, jsonify, current_app)
from flask_login import login_required, current_user
from models import db, Payment, Invoice, Customer, GLEntry, AuditLog
from ar.utils import role_required, log_action, next_sequence

payments_bp = Blueprint("payments", __name__)


def _build_payment_number():
    return next_sequence("PAY")


def _post_payment_to_gl(payment, allocations):
    """Cash debit + AR credit entries for each allocated invoice."""
    entries = []
    for alloc in allocations:
        entries += [
            GLEntry(payment_id=payment.id, invoice_id=alloc["invoice_id"],
                    entry_type="cash_debit", account_code="1000",
                    debit_amount=alloc["amount"], credit_amount=Decimal("0.00"),
                    description=f"Cash received PMT {payment.payment_number}"),
            GLEntry(payment_id=payment.id, invoice_id=alloc["invoice_id"],
                    entry_type="ar_credit", account_code="1200",
                    debit_amount=Decimal("0.00"), credit_amount=alloc["amount"],
                    description=f"AR cleared PMT {payment.payment_number}"),
        ]
    db.session.add_all(entries)


# ── Internal portal (AR staff) ───────────────────────────────────────────────

@payments_bp.route("/")
@login_required
def list_payments():
    payments = Payment.query.order_by(Payment.payment_date.desc()).all()
    return render_template("payments/list.html", payments=payments)


@payments_bp.route("/new", methods=["GET", "POST"])
@login_required
@role_required("ar_clerk", "finance_manager", "admin")
def new_payment():
    customers = Customer.query.filter_by(is_active=True).order_by(Customer.company_name).all()

    if request.method == "POST":
        customer_id = request.form.get("customer_id", type=int)
        amount = Decimal(request.form.get("amount", "0"))
        method = request.form.get("payment_method", "check")
        ref = request.form.get("reference_number", "")
        pmt_date = date.fromisoformat(request.form.get("payment_date", str(date.today())))

        payment = Payment(
            payment_number=_build_payment_number(),
            customer_id=customer_id,
            amount=amount,
            amount_applied=Decimal("0.00"),
            amount_unapplied=amount,
            payment_method=method,
            payment_date=pmt_date,
            reference_number=ref,
            status="pending",
            posted_by_id=current_user.id,
        )
        db.session.add(payment)
        db.session.commit()

        flash(f"Payment {payment.payment_number} recorded. Apply it to invoices below.", "success")
        return redirect(url_for("cash.apply_payment", payment_id=payment.id))

    return render_template("payments/new.html", customers=customers, today=date.today())


@payments_bp.route("/<int:payment_id>")
@login_required
def payment_detail(payment_id):
    payment = db.get_or_404(Payment, payment_id)
    return render_template("payments/detail.html", payment=payment)


# ── Customer payment portal (FR-AR-011) ─────────────────────────────────────

@payments_bp.route("/portal/<int:invoice_id>", methods=["GET", "POST"])
def customer_portal_pay(invoice_id):
    """Public-facing payment portal for customers (no login_required)."""
    invoice = db.get_or_404(Invoice, invoice_id)
    stripe_pub_key = current_app.config.get("STRIPE_PUBLIC_KEY", "")

    if request.method == "POST":
        token = request.form.get("stripeToken")
        amount_str = request.form.get("amount")

        if not token or not amount_str:
            flash("Payment information is missing.", "danger")
            return redirect(url_for("payments.customer_portal_pay", invoice_id=invoice_id))

        amount = Decimal(amount_str)
        if amount <= 0 or amount > invoice.balance_due:
            flash("Invalid payment amount.", "danger")
            return redirect(url_for("payments.customer_portal_pay", invoice_id=invoice_id))

        try:
            import stripe
            stripe.api_key = current_app.config["STRIPE_SECRET_KEY"]
            charge = stripe.Charge.create(
                amount=int(amount * 100),   # cents
                currency="usd",
                source=token,
                description=f"Invoice {invoice.invoice_number}",
                metadata={"invoice_id": invoice.id, "customer_id": invoice.customer_id},
            )

            payment = Payment(
                payment_number=_build_payment_number(),
                customer_id=invoice.customer_id,
                amount=amount,
                amount_applied=amount,
                amount_unapplied=Decimal("0.00"),
                payment_method="credit_card",
                payment_date=date.today(),
                reference_number=charge["id"],
                gateway_transaction_id=charge["id"],
                status="posted",
            )
            db.session.add(payment)
            db.session.flush()

            # Allocate to invoice
            from models import PaymentAllocation
            alloc = PaymentAllocation(
                payment_id=payment.id,
                invoice_id=invoice.id,
                amount_allocated=amount,
                allocated_by_id=None,
                is_manual=False,
            )
            db.session.add(alloc)

            invoice.amount_paid += amount
            invoice.balance_due -= amount
            if invoice.balance_due <= Decimal("0.00"):
                invoice.status = "paid"
                from datetime import datetime, timezone
                invoice.paid_at = datetime.now(timezone.utc)
            else:
                invoice.status = "partial"

            _post_payment_to_gl(payment, [{"invoice_id": invoice.id, "amount": amount}])
            db.session.commit()

            # Send receipt (FR-AR-013)
            from ar.utils import send_payment_receipt
            send_payment_receipt(payment, invoice)

            flash("Payment successful! A receipt has been emailed to you.", "success")
            return redirect(url_for("payments.portal_confirmation", payment_id=payment.id))

        except Exception as e:
            db.session.rollback()
            flash(f"Payment failed: {str(e)}", "danger")

    return render_template("payments/portal.html", invoice=invoice,
                           stripe_pub_key=stripe_pub_key)


@payments_bp.route("/portal/confirmation/<int:payment_id>")
def portal_confirmation(payment_id):
    payment = db.get_or_404(Payment, payment_id)
    return render_template("payments/confirmation.html", payment=payment)


# ── Stripe webhook (FR-AR-010) ───────────────────────────────────────────────

@payments_bp.route("/webhook/stripe", methods=["POST"])
def stripe_webhook():
    import stripe
    stripe.api_key = current_app.config["STRIPE_SECRET_KEY"]
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get("Stripe-Signature")
    webhook_secret = current_app.config.get("STRIPE_WEBHOOK_SECRET", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception:
        return jsonify({"error": "invalid signature"}), 400

    if event["type"] == "charge.failed":
        charge_id = event["data"]["object"]["id"]
        pmt = Payment.query.filter_by(gateway_transaction_id=charge_id).first()
        if pmt:
            pmt.status = "exception"
            db.session.commit()

    return jsonify({"received": True})
