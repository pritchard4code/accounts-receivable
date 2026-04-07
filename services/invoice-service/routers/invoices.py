from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date
from uuid import UUID
import math
import io

from database import get_db
from schemas import InvoiceCreate, InvoiceUpdate, InvoiceResponse, InvoiceListResponse, AgingReport
from services.invoice_service import (
    create_invoice, get_invoice, list_invoices, update_invoice,
    void_invoice, generate_pdf, send_invoice, calculate_aging
)
from auth_middleware import get_current_user

router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.get("/aging", response_model=AgingReport)
def get_aging_report(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return calculate_aging(db)


@router.get("/", response_model=InvoiceListResponse)
def list_invoices_endpoint(
    customer_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    invoices, total = list_invoices(db, customer_id, status, date_from, date_to, page, size)
    pages = math.ceil(total / size) if total > 0 else 1
    return InvoiceListResponse(items=invoices, total=total, page=page, size=size, pages=pages)


@router.post("/", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def create_invoice_endpoint(
    invoice_data: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return create_invoice(db, invoice_data, current_user["id"])


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice_endpoint(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return get_invoice(db, invoice_id)


@router.put("/{invoice_id}", response_model=InvoiceResponse)
def update_invoice_endpoint(
    invoice_id: UUID,
    invoice_data: InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return update_invoice(db, invoice_id, invoice_data)


@router.delete("/{invoice_id}", response_model=InvoiceResponse)
def void_invoice_endpoint(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return void_invoice(db, invoice_id)


@router.get("/{invoice_id}/pdf")
def download_pdf(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    invoice = get_invoice(db, invoice_id)
    pdf_bytes = generate_pdf(db, invoice_id)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=invoice-{invoice.invoice_number}.pdf"}
    )


@router.post("/{invoice_id}/send", response_model=InvoiceResponse)
def send_invoice_endpoint(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return send_invoice(db, invoice_id)
