import uuid
import enum
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, ForeignKey, Enum as SAEnum, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from database import Base


class CollectionActionType(str, enum.Enum):
    email = "email"
    sms = "sms"
    phone = "phone"
    letter = "letter"
    escalate = "escalate"
    hold = "hold"
    write_off = "write_off"


class CollectionStatus(str, enum.Enum):
    scheduled = "scheduled"
    executed = "executed"
    failed = "failed"
    cancelled = "cancelled"


class CollectionWorkflow(Base):
    __tablename__ = "collections_workflows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    stages = Column(JSONB, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CollectionAction(Base):
    __tablename__ = "collection_actions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    invoice_id = Column(UUID(as_uuid=True), index=True)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("collections_workflows.id"))
    stage = Column(String(100))
    action_type = Column(SAEnum(CollectionActionType, name="collection_action_type"), nullable=False)
    status = Column(SAEnum(CollectionStatus, name="collection_status"), default=CollectionStatus.scheduled)
    scheduled_date = Column(DateTime(timezone=True), index=True)
    executed_date = Column(DateTime(timezone=True))
    notes = Column(Text)
    result = Column(Text)
    created_by = Column(UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DunningRule(Base):
    __tablename__ = "dunning_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    days_overdue_min = Column(Integer, nullable=False, default=0)
    days_overdue_max = Column(Integer)
    action_type = Column(SAEnum(CollectionActionType, name="collection_action_type"), nullable=False)
    template = Column(Text)
    subject = Column(String(500))
    priority = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
