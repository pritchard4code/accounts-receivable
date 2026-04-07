import uuid
import enum
from sqlalchemy import Column, String, Boolean, DateTime, Numeric, Date, Text, ForeignKey, Enum as SAEnum, func, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from database import Base


class PaymentMethod(str, enum.Enum):
    credit_card = "credit_card"
    ach = "ach"
    wire = "wire"
    check = "check"
    cash = "cash"
    other = "other"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    applied = "applied"
    partially_applied = "partially_applied"
    refunded = "refunded"
    voided = "voided"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_number = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    payment_date = Column(Date, nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    unapplied_amount = Column(Numeric(15, 2), default=0.00)
    payment_method = Column(SAEnum(PaymentMethod, name="payment_method"), nullable=False)
    status = Column(SAEnum(PaymentStatus, name="payment_status"), default=PaymentStatus.pending)
    reference = Column(String(255))
    gateway_transaction_id = Column(String(255))
    gateway_response = Column(JSONB)
    notes = Column(Text)
    recorded_by = Column(UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    allocations = relationship("PaymentAllocation", back_populates="payment", cascade="all, delete-orphan")


class PaymentAllocation(Base):
    __tablename__ = "payment_allocations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id", ondelete="CASCADE"), nullable=False, index=True)
    invoice_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    allocated_amount = Column(Numeric(15, 2), nullable=False)
    allocated_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    payment = relationship("Payment", back_populates="allocations")
