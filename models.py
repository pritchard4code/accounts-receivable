from datetime import datetime, timezone, date
from decimal import Decimal
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()


def utcnow():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255))
    role = db.Column(db.String(50), nullable=False, default="ar_clerk")
    # roles: ar_clerk, collections_specialist, finance_manager, credit_manager, admin
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    last_login = db.Column(db.DateTime(timezone=True))


# ---------------------------------------------------------------------------
# Customer / Credit
# ---------------------------------------------------------------------------

class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    customer_number = db.Column(db.String(50), unique=True, nullable=False)
    company_name = db.Column(db.String(255), nullable=False)
    contact_name = db.Column(db.String(255))
    email = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    address_line1 = db.Column(db.String(255))
    address_line2 = db.Column(db.String(255))
    city = db.Column(db.String(100))
    state = db.Column(db.String(50))
    postal_code = db.Column(db.String(20))
    country = db.Column(db.String(50), default="US")
    tax_id = db.Column(db.String(50))

    # Credit profile (FR-AR-040)
    credit_limit = db.Column(db.Numeric(15, 2), default=Decimal("10000.00"))
    credit_status = db.Column(db.String(20), default="good")
    # credit_status: good, watch, hold, suspended
    risk_score = db.Column(db.Integer, default=0)   # 0-100; higher = riskier

    # Payment terms (Net-30, Net-60, etc.)
    payment_terms_days = db.Column(db.Integer, default=30)

    # Portal access
    portal_password_hash = db.Column(db.String(255))
    portal_enabled = db.Column(db.Boolean, default=False)

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    invoices = db.relationship("Invoice", back_populates="customer", lazy="dynamic")
    disputes = db.relationship("Dispute", back_populates="customer", lazy="dynamic")
    credit_events = db.relationship("CreditEvent", back_populates="customer", lazy="dynamic")

    @property
    def outstanding_balance(self):
        total = db.session.query(
            db.func.coalesce(db.func.sum(Invoice.balance_due), 0)
        ).filter(
            Invoice.customer_id == self.id,
            Invoice.status.in_(["sent", "partial", "overdue"])
        ).scalar()
        return Decimal(str(total))

    @property
    def available_credit(self):
        return self.credit_limit - self.outstanding_balance


# ---------------------------------------------------------------------------
# Invoice
# ---------------------------------------------------------------------------

class Invoice(db.Model):
    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)

    # Lifecycle: draft → sent → partial → paid | overdue | disputed | void
    status = db.Column(db.String(20), nullable=False, default="draft")

    invoice_type = db.Column(db.String(20), default="one_time")
    # invoice_type: one_time, recurring, consolidated

    issue_date = db.Column(db.Date, nullable=False, default=date.today)
    due_date = db.Column(db.Date, nullable=False)

    # Recurring fields
    recurring_interval = db.Column(db.String(20))   # monthly, quarterly, annually
    next_invoice_date = db.Column(db.Date)

    subtotal = db.Column(db.Numeric(15, 2), default=Decimal("0.00"))
    tax_amount = db.Column(db.Numeric(15, 2), default=Decimal("0.00"))
    late_fee_amount = db.Column(db.Numeric(15, 2), default=Decimal("0.00"))
    total_amount = db.Column(db.Numeric(15, 2), default=Decimal("0.00"))
    amount_paid = db.Column(db.Numeric(15, 2), default=Decimal("0.00"))
    balance_due = db.Column(db.Numeric(15, 2), default=Decimal("0.00"))

    # Source reference (sales order, contract, usage)
    source_type = db.Column(db.String(50))
    source_ref = db.Column(db.String(100))

    # GL posting
    gl_posted = db.Column(db.Boolean, default=False)
    gl_posted_at = db.Column(db.DateTime(timezone=True))

    notes = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    sent_at = db.Column(db.DateTime(timezone=True))
    paid_at = db.Column(db.DateTime(timezone=True))

    customer = db.relationship("Customer", back_populates="invoices")
    created_by = db.relationship("User", foreign_keys=[created_by_id])
    line_items = db.relationship("InvoiceLineItem", back_populates="invoice",
                                 cascade="all, delete-orphan")
    payment_allocations = db.relationship("PaymentAllocation", back_populates="invoice")
    dunning_logs = db.relationship("DunningLog", back_populates="invoice", lazy="dynamic")
    dispute = db.relationship("Dispute", back_populates="invoice", uselist=False)
    gl_entries = db.relationship("GLEntry", back_populates="invoice", lazy="dynamic")

    def recalculate_totals(self):
        self.subtotal = sum(li.line_total for li in self.line_items) or Decimal("0.00")
        self.total_amount = self.subtotal + self.tax_amount + self.late_fee_amount
        self.balance_due = self.total_amount - self.amount_paid

    @property
    def is_overdue(self):
        return self.due_date < date.today() and self.status in ("sent", "partial")

    @property
    def days_overdue(self):
        if self.is_overdue:
            return (date.today() - self.due_date).days
        return 0

    @property
    def aging_bucket(self):
        days = self.days_overdue
        if days == 0:
            return "current"
        elif days <= 30:
            return "1-30"
        elif days <= 60:
            return "31-60"
        elif days <= 90:
            return "61-90"
        else:
            return "90+"


class InvoiceLineItem(db.Model):
    __tablename__ = "invoice_line_items"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    quantity = db.Column(db.Numeric(10, 4), default=Decimal("1.0000"))
    unit_price = db.Column(db.Numeric(15, 2), nullable=False)
    tax_rate = db.Column(db.Numeric(5, 4), default=Decimal("0.0000"))
    line_total = db.Column(db.Numeric(15, 2), nullable=False)

    invoice = db.relationship("Invoice", back_populates="line_items")


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------

class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    payment_number = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)

    amount = db.Column(db.Numeric(15, 2), nullable=False)
    amount_applied = db.Column(db.Numeric(15, 2), default=Decimal("0.00"))
    amount_unapplied = db.Column(db.Numeric(15, 2), default=Decimal("0.00"))

    payment_method = db.Column(db.String(30))
    # payment_method: credit_card, ach, wire, check, digital_wallet

    status = db.Column(db.String(20), default="pending")
    # status: pending, posted, applied, exception, refunded

    payment_date = db.Column(db.Date, nullable=False, default=date.today)
    reference_number = db.Column(db.String(100))   # bank ref / gateway ref
    gateway_transaction_id = db.Column(db.String(255))

    # Overpayment / prepayment
    is_prepayment = db.Column(db.Boolean, default=False)

    notes = db.Column(db.Text)
    posted_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    customer = db.relationship("Customer")
    posted_by = db.relationship("User", foreign_keys=[posted_by_id])
    allocations = db.relationship("PaymentAllocation", back_populates="payment",
                                  cascade="all, delete-orphan")


class PaymentAllocation(db.Model):
    """Links a payment to one or more invoices (supports partial/split payments)."""
    __tablename__ = "payment_allocations"

    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.Integer, db.ForeignKey("payments.id"), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False)
    amount_allocated = db.Column(db.Numeric(15, 2), nullable=False)
    allocated_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    allocated_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    is_manual = db.Column(db.Boolean, default=False)   # True = manual override

    payment = db.relationship("Payment", back_populates="allocations")
    invoice = db.relationship("Invoice", back_populates="payment_allocations")
    allocated_by = db.relationship("User", foreign_keys=[allocated_by_id])


# ---------------------------------------------------------------------------
# Collections / Dunning
# ---------------------------------------------------------------------------

class DunningRule(db.Model):
    """Configurable dunning schedule (FR-AR-020)."""
    __tablename__ = "dunning_rules"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    days_past_due = db.Column(db.Integer, nullable=False)   # trigger at N days past due
    risk_profile = db.Column(db.String(20), default="all")  # all, low, medium, high
    channel = db.Column(db.String(20), default="email")     # email, sms, portal
    template_name = db.Column(db.String(100))               # email template key
    apply_late_fee = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)


class DunningLog(db.Model):
    """Record of every dunning communication sent (FR-AR-021)."""
    __tablename__ = "dunning_logs"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False)
    rule_id = db.Column(db.Integer, db.ForeignKey("dunning_rules.id"))
    channel = db.Column(db.String(20))
    recipient = db.Column(db.String(255))
    subject = db.Column(db.String(500))
    body_preview = db.Column(db.Text)
    sent_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    status = db.Column(db.String(20), default="sent")   # sent, failed, bounced

    invoice = db.relationship("Invoice", back_populates="dunning_logs")
    rule = db.relationship("DunningRule")


# ---------------------------------------------------------------------------
# Credit & Risk
# ---------------------------------------------------------------------------

class CreditEvent(db.Model):
    """Audit trail of credit limit changes, holds, flags (FR-AR-041)."""
    __tablename__ = "credit_events"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    event_type = db.Column(db.String(50))
    # event_type: limit_change, status_change, hold_placed, hold_released, flag_raised
    old_value = db.Column(db.String(100))
    new_value = db.Column(db.String(100))
    reason = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    customer = db.relationship("Customer", back_populates="credit_events")
    created_by = db.relationship("User", foreign_keys=[created_by_id])


# ---------------------------------------------------------------------------
# Disputes
# ---------------------------------------------------------------------------

class Dispute(db.Model):
    __tablename__ = "disputes"

    id = db.Column(db.Integer, primary_key=True)
    dispute_number = db.Column(db.String(50), unique=True, nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)

    reason_code = db.Column(db.String(50))
    # reason codes: pricing_error, duplicate, not_received, quality, other
    description = db.Column(db.Text)
    disputed_amount = db.Column(db.Numeric(15, 2))

    status = db.Column(db.String(20), default="open")
    # status: open, under_review, resolved_accept, resolved_reject, withdrawn

    opened_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    resolved_at = db.Column(db.DateTime(timezone=True))
    resolution_notes = db.Column(db.Text)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    invoice = db.relationship("Invoice", back_populates="dispute")
    customer = db.relationship("Customer", back_populates="disputes")
    assigned_to = db.relationship("User", foreign_keys=[assigned_to_id])
    documents = db.relationship("DisputeDocument", back_populates="dispute",
                                cascade="all, delete-orphan")


class DisputeDocument(db.Model):
    __tablename__ = "dispute_documents"

    id = db.Column(db.Integer, primary_key=True)
    dispute_id = db.Column(db.Integer, db.ForeignKey("disputes.id"), nullable=False)
    filename = db.Column(db.String(255))
    file_path = db.Column(db.String(500))
    uploaded_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    dispute = db.relationship("Dispute", back_populates="documents")
    uploaded_by = db.relationship("User", foreign_keys=[uploaded_by_id])


# ---------------------------------------------------------------------------
# General Ledger
# ---------------------------------------------------------------------------

class GLEntry(db.Model):
    """Near-real-time GL postings (FR-AR-032)."""
    __tablename__ = "gl_entries"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"))
    payment_id = db.Column(db.Integer, db.ForeignKey("payments.id"))
    entry_type = db.Column(db.String(30))
    # entry_type: ar_debit, revenue_credit, cash_debit, ar_credit, late_fee
    account_code = db.Column(db.String(20))
    debit_amount = db.Column(db.Numeric(15, 2), default=Decimal("0.00"))
    credit_amount = db.Column(db.Numeric(15, 2), default=Decimal("0.00"))
    description = db.Column(db.String(500))
    posted_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    erp_sync_status = db.Column(db.String(20), default="pending")
    # erp_sync_status: pending, synced, failed

    invoice = db.relationship("Invoice", back_populates="gl_entries")
    payment = db.relationship("Payment")


# ---------------------------------------------------------------------------
# Audit Trail
# ---------------------------------------------------------------------------

class AuditLog(db.Model):
    """SOX-compliant audit trail (FR-NFR security)."""
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50))
    entity_id = db.Column(db.Integer)
    old_data = db.Column(db.JSON)
    new_data = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    user = db.relationship("User", foreign_keys=[user_id])
