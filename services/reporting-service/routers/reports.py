from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from database import get_db
from services.reporting_service import (
    get_ar_aging_report, get_dso_metric, get_cash_collection_trend,
    get_customer_payment_history, get_collector_performance,
    get_cash_flow_forecast, get_dashboard_kpis
)
from auth_middleware import get_current_user

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/aging")
def get_aging(
    as_of_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return get_ar_aging_report(db, as_of_date)


@router.get("/dso")
def get_dso(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return get_dso_metric(db, days)


@router.get("/cash-trend")
def get_cash_trend(
    months: int = Query(6, ge=1, le=24),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return get_cash_collection_trend(db, months)


@router.get("/dashboard-kpis")
def get_kpis(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return get_dashboard_kpis(db)


@router.get("/customer/{customer_id}/payment-history")
def get_payment_history(
    customer_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return get_customer_payment_history(db, customer_id)


@router.get("/collector-performance")
def get_collector_perf(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return get_collector_performance(db)


@router.get("/cash-flow-forecast")
def get_forecast(
    days: int = Query(90, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return get_cash_flow_forecast(db, days)
