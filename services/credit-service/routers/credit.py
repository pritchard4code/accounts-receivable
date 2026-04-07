from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from decimal import Decimal

from database import get_db
from schemas import CreditProfileResponse, CreditProfileUpdate, CreditAvailabilityRequest, CreditAvailabilityResponse, RiskAssessmentResponse
from services.credit_service import (
    get_credit_profile, update_credit_limit, check_credit_availability,
    calculate_risk_score, flag_high_risk_customers, get_all_credit_profiles
)
from auth_middleware import get_current_user

router = APIRouter(prefix="/credit", tags=["Credit Management"])


@router.get("/profiles", response_model=List[CreditProfileResponse])
def list_credit_profiles(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return get_all_credit_profiles(db)


@router.get("/profiles/{customer_id}", response_model=CreditProfileResponse)
def get_profile(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return get_credit_profile(db, customer_id)


@router.put("/profiles/{customer_id}", response_model=CreditProfileResponse)
def update_profile(
    customer_id: UUID,
    profile_data: CreditProfileUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    profile = get_credit_profile(db, customer_id)
    if profile_data.credit_limit is not None:
        update_credit_limit(db, customer_id, profile_data.credit_limit, current_user["id"])
    update_data = profile_data.model_dump(exclude_unset=True, exclude={"credit_limit"})
    for key, value in update_data.items():
        setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/risk-assessment", response_model=List[RiskAssessmentResponse])
def get_risk_assessment(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return flag_high_risk_customers(db)


@router.post("/check-availability", response_model=CreditAvailabilityResponse)
def check_availability(
    request: CreditAvailabilityRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return check_credit_availability(db, request.customer_id, request.requested_amount)


@router.post("/recalculate/{customer_id}", response_model=CreditProfileResponse)
def recalculate_risk(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return calculate_risk_score(db, customer_id)
