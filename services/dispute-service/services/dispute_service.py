from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException, status
from typing import List, Optional, Tuple
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from models import Dispute, DisputeDocument, DisputeStatus, DisputeReason
from schemas import DisputeCreate, DisputeStatusUpdate


def generate_dispute_number(db: Session) -> str:
    year = datetime.now().year
    count = db.query(Dispute).filter(
        Dispute.dispute_number.like(f"DIS-{year}-%")
    ).count()
    return f"DIS-{year}-{str(count + 1).zfill(4)}"


def create_dispute(db: Session, dispute_data: DisputeCreate, user_id: str) -> Dispute:
    dispute_number = generate_dispute_number(db)

    # Update invoice status to disputed if invoice_id provided
    if dispute_data.invoice_id:
        db.execute(text("""
            UPDATE invoices SET status = 'disputed'::invoice_status, updated_at = NOW()
            WHERE id = :invoice_id AND status NOT IN ('void', 'paid')
        """), {"invoice_id": str(dispute_data.invoice_id)})

    dispute = Dispute(
        dispute_number=dispute_number,
        customer_id=dispute_data.customer_id,
        invoice_id=dispute_data.invoice_id,
        reason=dispute_data.reason,
        description=dispute_data.description,
        amount_disputed=dispute_data.amount_disputed,
        assigned_to=dispute_data.assigned_to,
        created_by=user_id,
    )
    db.add(dispute)
    db.commit()
    db.refresh(dispute)
    return dispute


def get_dispute(db: Session, dispute_id: UUID) -> Dispute:
    dispute = db.query(Dispute).filter(Dispute.id == dispute_id).first()
    if not dispute:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispute not found")
    return dispute


def list_disputes(
    db: Session,
    customer_id: Optional[UUID] = None,
    status_filter: Optional[str] = None,
    page: int = 1,
    size: int = 20
) -> Tuple[List[Dispute], int]:
    query = db.query(Dispute)

    if customer_id:
        query = query.filter(Dispute.customer_id == customer_id)
    if status_filter:
        query = query.filter(Dispute.status == status_filter)

    total = query.count()
    disputes = query.order_by(Dispute.created_at.desc()).offset((page - 1) * size).limit(size).all()
    return disputes, total


def update_dispute_status(
    db: Session,
    dispute_id: UUID,
    status_data: DisputeStatusUpdate,
    user_id: str
) -> Dispute:
    dispute = get_dispute(db, dispute_id)

    dispute.status = status_data.status
    if status_data.resolution:
        dispute.resolution = status_data.resolution
    if status_data.resolved_amount is not None:
        dispute.resolved_amount = status_data.resolved_amount

    if status_data.status in [DisputeStatus.resolved, DisputeStatus.rejected]:
        dispute.resolved_at = datetime.utcnow()
        # Revert invoice status from disputed if resolved
        if dispute.invoice_id:
            db.execute(text("""
                UPDATE invoices
                SET status = CASE
                    WHEN balance_due <= 0 THEN 'paid'::invoice_status
                    WHEN paid_amount > 0 THEN 'partial'::invoice_status
                    WHEN due_date < CURRENT_DATE THEN 'overdue'::invoice_status
                    ELSE 'sent'::invoice_status
                END,
                updated_at = NOW()
                WHERE id = :invoice_id AND status = 'disputed'
            """), {"invoice_id": str(dispute.invoice_id)})

    db.commit()
    db.refresh(dispute)
    return dispute


def add_document(
    db: Session,
    dispute_id: UUID,
    filename: str,
    file_path: str,
    file_size: Optional[int],
    content_type: Optional[str],
    user_id: str
) -> DisputeDocument:
    dispute = get_dispute(db, dispute_id)

    doc = DisputeDocument(
        dispute_id=dispute_id,
        filename=filename,
        file_path=file_path,
        file_size=file_size,
        content_type=content_type,
        uploaded_by=user_id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc
