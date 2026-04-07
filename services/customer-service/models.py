from sqlalchemy import Column, Integer, String, Numeric, DateTime, Enum as SAEnum
from sqlalchemy.sql import func
from database import Base
import enum

class CreditStatus(str, enum.Enum):
    active = "active"
    on_hold = "on_hold"
    suspended = "suspended"
    closed = "closed"

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    customer_number = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(50))
    address = Column(String(500))
    city = Column(String(100))
    state = Column(String(100))
    zip = Column(String(20))
    country = Column(String(100), default="US")
    currency = Column(String(10), default="USD")
    language = Column(String(20), default="en")
    credit_limit = Column(Numeric(15, 2), default=0)
    credit_status = Column(SAEnum(CreditStatus), default=CreditStatus.active)
    payment_terms = Column(String(50), default="NET_30")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
