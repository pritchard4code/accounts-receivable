from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID
import math

from database import get_db
from schemas import DisputeCreate, DisputeResponse, DisputeStatusUpdate, DisputeListResponse
from services.dispute_service import (
    create_dispute, get_dispute, list_disputes, update_dispute_status, add_document
)
from auth_middleware import get_current_user

router = APIRouter(prefix="/disputes", tags=["Disputes"])


@router.get("/", response_model=DisputeListResponse)
def list_disputes_endpoint(
    customer_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    disputes, total = list_disputes(db, customer_id, status, page, size)
    return DisputeListResponse(items=disputes, total=total, page=page, size=size)


@router.post("/", response_model=DisputeResponse, status_code=status.HTTP_201_CREATED)
def create_dispute_endpoint(
    dispute_data: DisputeCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return create_dispute(db, dispute_data, current_user["id"])


@router.get("/{dispute_id}", response_model=DisputeResponse)
def get_dispute_endpoint(
    dispute_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return get_dispute(db, dispute_id)


@router.put("/{dispute_id}/status", response_model=DisputeResponse)
def update_status_endpoint(
    dispute_id: UUID,
    status_data: DisputeStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return update_dispute_status(db, dispute_id, status_data, current_user["id"])


@router.post("/{dispute_id}/documents")
def add_document_endpoint(
    dispute_id: UUID,
    filename: str,
    file_path: str = "",
    file_size: Optional[int] = None,
    content_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    doc = add_document(db, dispute_id, filename, file_path, file_size, content_type, current_user["id"])
    return {"id": str(doc.id), "filename": doc.filename, "created_at": doc.created_at}
