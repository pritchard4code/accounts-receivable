from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import Optional
from uuid import UUID
import math

from database import get_db, engine, Base
from models import Customer
from schemas import CustomerCreate, CustomerUpdate, CustomerResponse, PaginatedCustomers
from auth_middleware import get_current_user_from_token

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AR Customer Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def generate_customer_number(db: Session) -> str:
    count = db.query(func.count(Customer.id)).scalar()
    return f"CUST-{str(count + 1).zfill(6)}"


@app.get("/health")
def health():
    return {"status": "healthy", "service": "customer-service"}


@app.get("/api/v1/customers", response_model=PaginatedCustomers)
def list_customers(
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_from_token)
):
    query = db.query(Customer)
    if search:
        like = f"%{search}%"
        query = query.filter(or_(Customer.name.ilike(like), Customer.email.ilike(like), Customer.customer_number.ilike(like)))
    total = query.count()
    customers = query.offset((page - 1) * size).limit(size).all()
    return PaginatedCustomers(
        items=customers,
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if total else 0
    )


@app.post("/api/v1/customers", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(
    data: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_from_token)
):
    customer = Customer(**data.model_dump(), customer_number=generate_customer_number(db))
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@app.get("/api/v1/customers/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_from_token)
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@app.put("/api/v1/customers/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: UUID,
    data: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_from_token)
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)
    db.commit()
    db.refresh(customer)
    return customer
