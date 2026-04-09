"""Shared utilities: sequences, email, audit logging, ERP sync."""
import functools
from datetime import datetime, timezone
from flask import request as flask_request, current_app
from flask_login import current_user
from models import db, AuditLog


# ── RBAC decorator ────────────────────────────────────────────────────────────

def role_required(*roles):
    """Decorator: restrict route to users with one of the specified roles."""
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                from flask import redirect, url_for
                return redirect(url_for("auth.login"))
            if current_user.role not in roles:
                from flask import abort
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ── Sequence generator ────────────────────────────────────────────────────────

_sequences = {}


def next_sequence(prefix):
    """Thread-safe incrementing sequence for document numbers."""
    from sqlalchemy import text
    result = db.session.execute(
        text("SELECT nextval('doc_sequence')")
    ).scalar()
    return f"{prefix}-{result:06d}"


def _ensure_sequence():
    """Create the PostgreSQL sequence if it doesn't exist."""
    from sqlalchemy import text
    db.session.execute(text(
        "CREATE SEQUENCE IF NOT EXISTS doc_sequence START 1000 INCREMENT 1"
    ))
    db.session.commit()


# ── Audit logging ─────────────────────────────────────────────────────────────

def log_action(action, entity_type=None, entity_id=None, old_data=None, new_data=None):
    try:
        entry = AuditLog(
            user_id=current_user.id if current_user.is_authenticated else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_data=old_data,
            new_data=new_data,
            ip_address=flask_request.remote_addr,
        )
        db.session.add(entry)
    except Exception:
        pass   # never let audit failure break main flow


# ── Email ─────────────────────────────────────────────────────────────────────

def send_invoice_email(invoice):
    """Email invoice PDF to customer (FR-AR-004)."""
    try:
        from flask_mail import Message
        from app import mail
        msg = Message(
            subject=f"Invoice {invoice.invoice_number} from "
                    f"{current_app.config['COMPANY_NAME']}",
            recipients=[invoice.customer.email],
            html=_render_template_str("emails/invoice.html", invoice=invoice),
        )
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Invoice email failed: {e}")
        return False


def send_payment_receipt(payment, invoice):
    """Email payment receipt to customer (FR-AR-013)."""
    try:
        from flask_mail import Message
        from app import mail
        msg = Message(
            subject=f"Payment Receipt – {payment.payment_number}",
            recipients=[invoice.customer.email],
            html=_render_template_str("emails/receipt.html",
                                      payment=payment, invoice=invoice),
        )
        mail.send(msg)
    except Exception as e:
        current_app.logger.error(f"Receipt email failed: {e}")


def render_dunning_email(template_name, invoice):
    """Render dunning subject + body for the given template."""
    templates = {
        "dunning_reminder": (
            f"Friendly Reminder: Invoice {invoice.invoice_number} Due",
            f"Dear {invoice.customer.company_name},\n\n"
            f"This is a friendly reminder that invoice {invoice.invoice_number} "
            f"for ${invoice.balance_due:,.2f} was due on {invoice.due_date}.\n\n"
            f"Please remit payment at your earliest convenience.\n\n"
            f"Thank you,\n{current_app.config['COMPANY_NAME']}"
        ),
        "dunning_first_notice": (
            f"PAST DUE: Invoice {invoice.invoice_number}",
            f"Dear {invoice.customer.company_name},\n\n"
            f"Invoice {invoice.invoice_number} for ${invoice.balance_due:,.2f} is now "
            f"{invoice.days_overdue} days past due.\n\n"
            f"Please pay immediately to avoid additional charges.\n\n"
            f"{current_app.config['COMPANY_NAME']}"
        ),
        "dunning_second_notice": (
            f"URGENT – Invoice {invoice.invoice_number} Severely Past Due",
            f"Dear {invoice.customer.company_name},\n\n"
            f"Invoice {invoice.invoice_number} is {invoice.days_overdue} days past due. "
            f"A late fee has been applied. Your current balance is ${invoice.balance_due:,.2f}.\n\n"
            f"Immediate payment is required.\n\n"
            f"{current_app.config['COMPANY_NAME']}"
        ),
        "dunning_final_demand": (
            f"FINAL DEMAND – Invoice {invoice.invoice_number}",
            f"Dear {invoice.customer.company_name},\n\n"
            f"This is your FINAL NOTICE. Invoice {invoice.invoice_number} "
            f"for ${invoice.balance_due:,.2f} is {invoice.days_overdue} days past due.\n\n"
            f"Failure to pay within 5 business days may result in account suspension "
            f"and referral to collections.\n\n"
            f"{current_app.config['COMPANY_NAME']}"
        ),
    }
    return templates.get(template_name,
                         (f"Invoice {invoice.invoice_number} Notice", ""))


def send_dunning_email(recipient, subject, body):
    try:
        from flask_mail import Message
        from app import mail
        msg = Message(subject=subject, recipients=[recipient], body=body)
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Dunning email failed: {e}")
        return False


def _render_template_str(template, **ctx):
    from flask import render_template
    return render_template(template, **ctx)


# ── ERP sync (FR-AR-070) ──────────────────────────────────────────────────────

def push_gl_to_erp():
    """Push pending GL entries to ERP via REST API."""
    from models import GLEntry
    import urllib.request, json

    erp_url = current_app.config.get("ERP_API_URL")
    erp_key = current_app.config.get("ERP_API_KEY")

    if not erp_url:
        return 0, 0

    pending = GLEntry.query.filter_by(erp_sync_status="pending").all()
    synced = 0
    errors = 0

    for entry in pending:
        payload = json.dumps({
            "account": entry.account_code,
            "debit": float(entry.debit_amount),
            "credit": float(entry.credit_amount),
            "description": entry.description,
            "entry_type": entry.entry_type,
        }).encode()

        try:
            req = urllib.request.Request(
                f"{erp_url}/gl/entries",
                data=payload,
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {erp_key}"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5):
                entry.erp_sync_status = "synced"
                synced += 1
        except Exception:
            entry.erp_sync_status = "failed"
            errors += 1

    db.session.commit()
    return synced, errors
