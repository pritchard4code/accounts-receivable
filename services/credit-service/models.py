import uuid
import enum
from sqlalchemy import Column, String, DateTime, Numeric, Integer, Date, Text, Enum as SAEnum, func
from sqlalchemy.dialects.postgresql import UUID
from database import Base


class RiskLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class CreditProfile(Base):
    __tablename__ = "credit_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    credit_limit = Column(Numeric(15, 2), default=0.00)
    current_balance = Column(Numeric(15, 2), default=0.00)
    available_credit = Column(Numeric(15, 2), default=0.00)
    risk_score = Column(Numeric(5, 2), default=0.00)
    risk_level = Column(SAEnum(RiskLevel, name="risk_level"), default=RiskLevel.low)
    payment_score = Column(Numeric(5, 2), default=100.00)
    avg_days_to_pay = Column(Numeric(5, 1), default=0.0)
    on_time_payment_rate = Column(Numeric(5, 2), default=100.00)
    late_payment_count = Column(Integer, default=0)
    nsf_count = Column(Integer, default=0)
    last_review_date = Column(Date)
    next_review_date = Column(Date)
    notes = Column(Text)
    reviewed_by = Column(UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
