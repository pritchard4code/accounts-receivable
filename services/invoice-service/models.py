import uuid
import enum
from sqlalchemy import Column, String, Boolean, DateTime, Numeric, Integer, Date, Text, ForeignKey, Enum as SAEnum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base


class InvoiceStatus(str, enum.Enum):
    draft = "draft"
    sent = "sent"
    viewed = "viewed"
    partial = "partial"
    paid = "paid"
    overdue = "overdue"
    void = "void"
    disputed = "disputed"


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    status = Column(SAEnum(InvoiceStatus, name="invoice_status"), default=InvoiceStatus.draft)
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    subtotal = Column(Numeric(15, 2), default=0.00)
    tax_amount = Column(Numeric(15, 2), default=0.00)
    discount_amount = Column(Numeric(15, 2), default=0.00)
    total_amount = Column(Numeric(15, 2), default=0.00)
    paid_amount = Column(Numeric(15, 2), default=0.00)
    balance_due = Column(Numeric(15, 2), default=0.00)
    currency = Column(String(10), default="USD")
    payment_terms = Column(Integer, default=30)
    plan_id = Column(String(16))
    po_number = Column(String(100))
    notes = Column(Text)
    internal_notes = Column(Text)
    template_id = Column(UUID(as_uuid=True))
    sent_at = Column(DateTime(timezone=True))
    viewed_at = Column(DateTime(timezone=True))
    created_by = Column(UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    line_items = relationship("InvoiceLineItem", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    line_number = Column(Integer, default=1)
    description = Column(Text, nullable=False)
    quantity = Column(Numeric(10, 3), default=1.000)
    unit_price = Column(Numeric(15, 2), default=0.00)
    total_price = Column(Numeric(15, 2), default=0.00)
    tax_rate = Column(Numeric(5, 4), default=0.0000)
    tax_amount = Column(Numeric(15, 2), default=0.00)
    discount_rate = Column(Numeric(5, 4), default=0.0000)
    discount_amount = Column(Numeric(15, 2), default=0.00)
    product_code = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    invoice = relationship("Invoice", back_populates="line_items")


class InvoiceTemplate(Base):
    __tablename__ = "invoice_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    content = Column(Text)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RecurringInvoice(Base):
    __tablename__ = "recurring_invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), nullable=False)
    template_invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"))
    frequency = Column(String(20), default="monthly")
    next_invoice_date = Column(Date)
    end_date = Column(Date)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
