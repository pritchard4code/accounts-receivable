from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case
from fastapi import HTTPException, status
from typing import List, Optional, Tuple
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID
import io

from models import Invoice, InvoiceLineItem, InvoiceStatus
from schemas import InvoiceCreate, InvoiceUpdate, AgingBucket, AgingReport


def generate_invoice_number(db: Session) -> str:
    year = datetime.now().year
    count = db.query(func.count(Invoice.id)).filter(
        func.extract('year', Invoice.created_at) == year
    ).scalar() or 0
    return f"INV-{year}-{str(count + 1).zfill(4)}"


def calculate_line_totals(line_item_data: dict) -> dict:
    quantity = Decimal(str(line_item_data.get("quantity", 1)))
    unit_price = Decimal(str(line_item_data.get("unit_price", 0)))
    tax_rate = Decimal(str(line_item_data.get("tax_rate", 0)))
    discount_rate = Decimal(str(line_item_data.get("discount_rate", 0)))

    subtotal = quantity * unit_price
    discount_amount = subtotal * discount_rate
    taxable_amount = subtotal - discount_amount
    tax_amount = taxable_amount * tax_rate
    total_price = taxable_amount + tax_amount

    return {
        **line_item_data,
        "total_price": total_price,
        "tax_amount": tax_amount,
        "discount_amount": discount_amount,
    }


def create_invoice(db: Session, invoice_data: InvoiceCreate, user_id: UUID) -> Invoice:
    invoice_number = generate_invoice_number(db)

    # Calculate totals
    subtotal = Decimal("0.00")
    total_tax = Decimal("0.00")
    total_discount = Decimal("0.00")

    line_items_data = []
    for i, li in enumerate(invoice_data.line_items):
        li_dict = li.model_dump()
        li_dict["line_number"] = i + 1
        calc = calculate_line_totals(li_dict)
        line_items_data.append(calc)
        subtotal += Decimal(str(li.quantity)) * Decimal(str(li.unit_price))
        total_tax += calc["tax_amount"]
        total_discount += calc["discount_amount"]

    total_amount = subtotal - total_discount + total_tax

    invoice = Invoice(
        invoice_number=invoice_number,
        customer_id=invoice_data.customer_id,
        invoice_date=invoice_data.invoice_date,
        due_date=invoice_data.due_date,
        currency=invoice_data.currency,
        payment_terms=invoice_data.payment_terms,
        po_number=invoice_data.po_number,
        notes=invoice_data.notes,
        internal_notes=invoice_data.internal_notes,
        template_id=invoice_data.template_id,
        subtotal=subtotal,
        tax_amount=total_tax,
        discount_amount=total_discount,
        total_amount=total_amount,
        balance_due=total_amount,
        created_by=user_id,
    )
    db.add(invoice)
    db.flush()

    for li_data in line_items_data:
        line_item = InvoiceLineItem(invoice_id=invoice.id, **li_data)
        db.add(line_item)

    db.commit()
    db.refresh(invoice)
    return invoice


def get_invoice(db: Session, invoice_id: UUID) -> Invoice:
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


def list_invoices(
    db: Session,
    customer_id: Optional[UUID] = None,
    status_filter: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = 1,
    size: int = 20
) -> Tuple[List[Invoice], int]:
    query = db.query(Invoice)

    if customer_id:
        query = query.filter(Invoice.customer_id == customer_id)
    if status_filter:
        query = query.filter(Invoice.status == status_filter)
    if date_from:
        query = query.filter(Invoice.invoice_date >= date_from)
    if date_to:
        query = query.filter(Invoice.invoice_date <= date_to)

    total = query.count()
    invoices = query.order_by(Invoice.created_at.desc()).offset((page - 1) * size).limit(size).all()
    return invoices, total


def update_invoice(db: Session, invoice_id: UUID, invoice_data: InvoiceUpdate) -> Invoice:
    invoice = get_invoice(db, invoice_id)
    if invoice.status == InvoiceStatus.void:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot update a voided invoice")

    update_data = invoice_data.model_dump(exclude_unset=True, exclude={"line_items"})
    for key, value in update_data.items():
        setattr(invoice, key, value)

    if invoice_data.line_items is not None:
        db.query(InvoiceLineItem).filter(InvoiceLineItem.invoice_id == invoice_id).delete()
        subtotal = Decimal("0.00")
        total_tax = Decimal("0.00")
        total_discount = Decimal("0.00")

        for i, li in enumerate(invoice_data.line_items):
            li_dict = li.model_dump()
            li_dict["line_number"] = i + 1
            calc = calculate_line_totals(li_dict)
            line_item = InvoiceLineItem(invoice_id=invoice.id, **calc)
            db.add(line_item)
            subtotal += Decimal(str(li.quantity)) * Decimal(str(li.unit_price))
            total_tax += calc["tax_amount"]
            total_discount += calc["discount_amount"]

        total_amount = subtotal - total_discount + total_tax
        invoice.subtotal = subtotal
        invoice.tax_amount = total_tax
        invoice.discount_amount = total_discount
        invoice.total_amount = total_amount
        invoice.balance_due = total_amount - invoice.paid_amount

    db.commit()
    db.refresh(invoice)
    return invoice


def void_invoice(db: Session, invoice_id: UUID) -> Invoice:
    invoice = get_invoice(db, invoice_id)
    if invoice.status == InvoiceStatus.paid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot void a paid invoice")
    invoice.status = InvoiceStatus.void
    db.commit()
    db.refresh(invoice)
    return invoice


def send_invoice(db: Session, invoice_id: UUID) -> Invoice:
    invoice = get_invoice(db, invoice_id)
    if invoice.status not in [InvoiceStatus.draft, InvoiceStatus.sent]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice cannot be sent in its current status"
        )
    invoice.status = InvoiceStatus.sent
    invoice.sent_at = datetime.utcnow()
    db.commit()
    db.refresh(invoice)
    return invoice


def generate_pdf(db: Session, invoice_id: UUID) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

    invoice = get_invoice(db, invoice_id)
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []

    # Header
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], textColor=colors.HexColor('#003087'), fontSize=24)
    story.append(Paragraph("INVOICE", title_style))
    story.append(Spacer(1, 0.2*inch))

    # Invoice info table
    info_data = [
        ["Invoice Number:", invoice.invoice_number, "Invoice Date:", str(invoice.invoice_date)],
        ["Status:", invoice.status.value.upper(), "Due Date:", str(invoice.due_date)],
        ["Currency:", invoice.currency, "Payment Terms:", f"Net {invoice.payment_terms}"],
    ]
    info_table = Table(info_data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 2*inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.3*inch))

    # Line items
    line_headers = ["#", "Description", "Qty", "Unit Price", "Tax Rate", "Total"]
    line_data = [line_headers]
    for i, item in enumerate(invoice.line_items, 1):
        line_data.append([
            str(i),
            item.description,
            str(item.quantity),
            f"${item.unit_price:,.2f}",
            f"{float(item.tax_rate)*100:.1f}%",
            f"${item.total_price:,.2f}",
        ])

    line_table = Table(line_data, colWidths=[0.4*inch, 3.0*inch, 0.8*inch, 1.0*inch, 0.8*inch, 1.0*inch])
    line_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003087')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f7fa')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(line_table)
    story.append(Spacer(1, 0.2*inch))

    # Totals
    totals_data = [
        ["", "Subtotal:", f"${invoice.subtotal:,.2f}"],
        ["", "Tax:", f"${invoice.tax_amount:,.2f}"],
        ["", "Discount:", f"-${invoice.discount_amount:,.2f}"],
        ["", "Total:", f"${invoice.total_amount:,.2f}"],
        ["", "Amount Paid:", f"${invoice.paid_amount:,.2f}"],
        ["", "Balance Due:", f"${invoice.balance_due:,.2f}"],
    ]
    totals_table = Table(totals_data, colWidths=[4*inch, 1.5*inch, 1.5*inch])
    totals_table.setStyle(TableStyle([
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('BACKGROUND', (1, -1), (-1, -1), colors.HexColor('#003087')),
        ('TEXTCOLOR', (1, -1), (-1, -1), colors.white),
        ('LINEABOVE', (1, -1), (-1, -1), 1, colors.HexColor('#003087')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(totals_table)

    if invoice.notes:
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph(f"<b>Notes:</b> {invoice.notes}", styles['Normal']))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def calculate_aging(db: Session) -> AgingReport:
    from sqlalchemy import text
    today = date.today()

    result = db.execute(text("""
        SELECT
            i.customer_id::text,
            c.name as customer_name,
            SUM(CASE WHEN i.due_date >= :today THEN i.balance_due ELSE 0 END) as current_amount,
            SUM(CASE WHEN i.due_date < :today AND i.due_date >= :day30 THEN i.balance_due ELSE 0 END) as days_1_30,
            SUM(CASE WHEN i.due_date < :day30 AND i.due_date >= :day60 THEN i.balance_due ELSE 0 END) as days_31_60,
            SUM(CASE WHEN i.due_date < :day60 AND i.due_date >= :day90 THEN i.balance_due ELSE 0 END) as days_61_90,
            SUM(CASE WHEN i.due_date < :day90 THEN i.balance_due ELSE 0 END) as days_over_90,
            SUM(i.balance_due) as total
        FROM invoices i
        JOIN customers c ON c.id = i.customer_id
        WHERE i.status NOT IN ('void', 'paid', 'draft')
          AND i.balance_due > 0
        GROUP BY i.customer_id, c.name
        ORDER BY total DESC
    """), {
        "today": today,
        "day30": today - timedelta(days=30),
        "day60": today - timedelta(days=60),
        "day90": today - timedelta(days=90),
    })

    buckets = []
    totals = AgingBucket(customer_id="TOTAL", customer_name="Grand Total")

    for row in result:
        bucket = AgingBucket(
            customer_id=row.customer_id,
            customer_name=row.customer_name,
            current=Decimal(str(row.current_amount or 0)),
            days_1_30=Decimal(str(row.days_1_30 or 0)),
            days_31_60=Decimal(str(row.days_31_60 or 0)),
            days_61_90=Decimal(str(row.days_61_90 or 0)),
            days_over_90=Decimal(str(row.days_over_90 or 0)),
            total=Decimal(str(row.total or 0)),
        )
        buckets.append(bucket)
        totals.current += bucket.current
        totals.days_1_30 += bucket.days_1_30
        totals.days_31_60 += bucket.days_31_60
        totals.days_61_90 += bucket.days_61_90
        totals.days_over_90 += bucket.days_over_90
        totals.total += bucket.total

    return AgingReport(as_of_date=today, buckets=buckets, totals=totals)
