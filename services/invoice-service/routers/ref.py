from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import RefStatus
from schemas import RefStatusResponse
from auth_middleware import get_current_user

router = APIRouter(prefix="/ref", tags=["Reference Data"])


@router.get("/statuses", response_model=List[RefStatusResponse])
def get_statuses(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return db.query(RefStatus).order_by(RefStatus.status_nm).all()
