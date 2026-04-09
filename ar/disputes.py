"""Dispute & Case Management (FR-AR-050 – FR-AR-052)."""
import os
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, current_app)
from flask_login import login_required, current_user
from models import db, Dispute, DisputeDocument, Invoice, Customer
from ar.utils import role_required, log_action, next_sequence
from datetime import datetime, timezone

disputes_bp = Blueprint("disputes", __name__)

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "docx", "xlsx"}


def _allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ── Routes ────────────────────────────────────────────────────────────────────

@disputes_bp.route("/")
@login_required
def list_disputes():
    status_filter = request.args.get("status", "open")
    q = Dispute.query
    if status_filter:
        q = q.filter(Dispute.status == status_filter)
    disputes = q.order_by(Dispute.opened_at.desc()).all()
    return render_template("disputes/list.html", disputes=disputes,
                           status_filter=status_filter)


@disputes_bp.route("/open/<int:invoice_id>", methods=["GET", "POST"])
def open_dispute(invoice_id):
    """Customers or staff can open a dispute on an invoice (FR-AR-050)."""
    invoice = db.get_or_404(Invoice, invoice_id)

    if invoice.dispute and invoice.dispute.status not in ("resolved_accept",
                                                          "resolved_reject", "withdrawn"):
        flash("An open dispute already exists for this invoice.", "warning")
        return redirect(url_for("disputes.dispute_detail",
                                dispute_id=invoice.dispute.id))

    if request.method == "POST":
        dispute = Dispute(
            dispute_number=next_sequence("DIS"),
            invoice_id=invoice.id,
            customer_id=invoice.customer_id,
            reason_code=request.form.get("reason_code", "other"),
            description=request.form.get("description", ""),
            disputed_amount=invoice.balance_due,
            status="open",
        )
        db.session.add(dispute)
        db.session.flush()

        # Mark invoice as disputed to pause dunning (FR-AR-052)
        invoice.status = "disputed"

        # Handle document upload
        file = request.files.get("document")
        if file and file.filename and _allowed_file(file.filename):
            upload_dir = os.path.join(current_app.root_path, "uploads", "disputes")
            os.makedirs(upload_dir, exist_ok=True)
            safe_name = f"DIS-{dispute.id}-{file.filename}"
            file_path = os.path.join(upload_dir, safe_name)
            file.save(file_path)
            doc = DisputeDocument(dispute_id=dispute.id, filename=file.filename,
                                  file_path=file_path,
                                  uploaded_by_id=current_user.id
                                  if current_user.is_authenticated else None)
            db.session.add(doc)

        log_action("dispute_opened", "Dispute", dispute.id,
                   new_data={"invoice": invoice.invoice_number,
                             "reason": dispute.reason_code})
        db.session.commit()
        flash("Dispute submitted. Our team will review it within 5 business days.", "success")
        return redirect(url_for("disputes.dispute_detail", dispute_id=dispute.id))

    return render_template("disputes/open.html", invoice=invoice)


@disputes_bp.route("/<int:dispute_id>")
@login_required
def dispute_detail(dispute_id):
    dispute = db.get_or_404(Dispute, dispute_id)
    return render_template("disputes/detail.html", dispute=dispute)


@disputes_bp.route("/<int:dispute_id>/assign", methods=["POST"])
@login_required
@role_required("collections_specialist", "finance_manager", "admin")
def assign_dispute(dispute_id):
    dispute = db.get_or_404(Dispute, dispute_id)
    from models import User
    assignee_id = request.form.get("assignee_id", type=int)
    user = db.session.get(User, assignee_id)
    if user:
        dispute.assigned_to_id = user.id
        db.session.commit()
        flash(f"Dispute assigned to {user.full_name}.", "success")
    return redirect(url_for("disputes.dispute_detail", dispute_id=dispute_id))


@disputes_bp.route("/<int:dispute_id>/resolve", methods=["POST"])
@login_required
@role_required("collections_specialist", "finance_manager", "admin")
def resolve_dispute(dispute_id):
    dispute = db.get_or_404(Dispute, dispute_id)
    resolution = request.form.get("resolution")   # accept or reject
    notes = request.form.get("resolution_notes", "")

    if resolution not in ("accept", "reject"):
        flash("Invalid resolution.", "danger")
        return redirect(url_for("disputes.dispute_detail", dispute_id=dispute_id))

    dispute.status = f"resolved_{resolution}"
    dispute.resolution_notes = notes
    dispute.resolved_at = datetime.now(timezone.utc)

    invoice = dispute.invoice
    if resolution == "accept":
        # Credit memo — reduce invoice balance
        invoice.balance_due = max(Decimal("0.00"), invoice.balance_due - dispute.disputed_amount)
        if invoice.balance_due <= 0:
            invoice.status = "paid"
        else:
            invoice.status = "partial"
        flash("Dispute accepted — invoice adjusted.", "success")
    else:
        # Reinstate dunning
        invoice.status = "overdue" if invoice.is_overdue else "sent"
        flash("Dispute rejected — invoice reinstated for collections.", "info")

    log_action("dispute_resolved", "Dispute", dispute.id,
               new_data={"resolution": resolution})
    db.session.commit()
    return redirect(url_for("disputes.dispute_detail", dispute_id=dispute_id))


from decimal import Decimal
