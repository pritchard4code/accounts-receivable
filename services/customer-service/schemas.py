from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from decimal import Decimal

class CustomerBase(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    country: Optional[str] = "US"
    currency: Optional[str] = "USD"
    language: Optional[str] = "en"
    credit_limit: Optional[Decimal] = Decimal("10000.00")
    credit_status: Optional[str] = "active"
    payment_terms: Optional[str] = "NET_30"

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(CustomerBase):
    name: Optional[str] = None
    email: Optional[str] = None

class CustomerResponse(CustomerBase):
    id: int
    customer_number: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PaginatedCustomers(BaseModel):
    items: list[CustomerResponse]
    total: int
    page: int
    size: int
    pages: int
