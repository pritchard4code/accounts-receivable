import uuid
import enum
from sqlalchemy import Column, String, DateTime, Numeric, Integer, Text, Enum as SAEnum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base


class DisputeStatus(str, enum.Enum):
    open = "open"
    under_review = "under_review"
    resolved = "resolved"
    rejected = "rejected"
    withdrawn = "withdrawn"


class DisputeReason(str, enum.Enum):
    billing_error = "billing_error"
    goods_not_received = "goods_not_received"
    service_not_rendered = "service_not_rendered"
    quality_issue = "quality_issue"
    duplicate_charge = "duplicate_charge"
    price_discrepancy = "price_discrepancy"
    other = "other"


class Dispute(Base):
    __tablename__ = "disputes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dispute_number = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    invoice_id = Column(UUID(as_uuid=True), index=True)
    status = Column(SAEnum(DisputeStatus, name="dispute_status"), default=DisputeStatus.open)
    reason = Column(SAEnum(DisputeReason, name="dispute_reason"), nullable=False)
    description = Column(Text)
    amount_disputed = Column(Numeric(15, 2), default=0.00)
    resolution = Column(Text)
    resolved_amount = Column(Numeric(15, 2))
    assigned_to = Column(UUID(as_uuid=True))
    created_by = Column(UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True))

    documents = relationship("DisputeDocument", back_populates="dispute", cascade="all, delete-orphan")


class DisputeDocument(Base):
    __tablename__ = "dispute_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dispute_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500))
    file_size = Column(Integer)
    content_type = Column(String(100))
    uploaded_by = Column(UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    dispute = relationship("Dispute", back_populates="documents")
