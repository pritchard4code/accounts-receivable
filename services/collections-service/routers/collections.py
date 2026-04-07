from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from database import get_db
from models import DunningRule
from schemas import (
    CollectionQueueItem, OverdueInvoice, DunningRuleCreate,
    DunningRuleUpdate, DunningRuleResponse, WorkflowCreate, WorkflowResponse
)
from services.collections_service import (
    get_collection_queue, get_overdue_invoices, run_dunning_workflow,
    send_dunning_notification, calculate_late_fee
)
from auth_middleware import get_current_user

router = APIRouter(prefix="/collections", tags=["Collections"])


@router.get("/queue", response_model=List[CollectionQueueItem])
def get_queue(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return get_collection_queue(db)


@router.get("/overdue", response_model=List[OverdueInvoice])
def get_overdue(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return get_overdue_invoices(db)


@router.post("/dunning/run")
def run_dunning(
    customer_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return run_dunning_workflow(db, customer_id, current_user["id"])


@router.post("/dunning/send/{invoice_id}")
def send_notification(
    invoice_id: UUID,
    template: str = "default",
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return send_dunning_notification(db, invoice_id, template)


@router.get("/dunning-rules", response_model=List[DunningRuleResponse])
def list_dunning_rules(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return db.query(DunningRule).order_by(DunningRule.days_overdue_min).all()


@router.post("/dunning-rules", response_model=DunningRuleResponse, status_code=status.HTTP_201_CREATED)
def create_dunning_rule(
    rule_data: DunningRuleCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    rule = DunningRule(**rule_data.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.put("/dunning-rules/{rule_id}", response_model=DunningRuleResponse)
def update_dunning_rule(
    rule_id: UUID,
    rule_data: DunningRuleUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    rule = db.query(DunningRule).filter(DunningRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    for key, value in rule_data.model_dump(exclude_unset=True).items():
        setattr(rule, key, value)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/late-fee/{invoice_id}")
def get_late_fee(
    invoice_id: UUID,
    fee_rate: float = Query(0.015, ge=0.0, le=1.0),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return calculate_late_fee(db, invoice_id, fee_rate)
