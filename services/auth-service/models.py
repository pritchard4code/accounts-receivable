import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SAEnum, func
from sqlalchemy.dialects.postgresql import UUID
from database import Base
import enum


class UserRole(str, enum.Enum):
    admin = "admin"
    ar_clerk = "ar_clerk"
    collections_specialist = "collections_specialist"
    finance_manager = "finance_manager"
    credit_manager = "credit_manager"
    customer = "customer"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole, name="user_role"), nullable=False, default=UserRole.ar_clerk)
    first_name = Column(String(100))
    last_name = Column(String(100))
    phone = Column(String(30))
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
