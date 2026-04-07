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
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable

    invoice = get_invoice(db, invoice_id)
    buffer = io.BytesIO()

    navy = colors.HexColor('#003087')
    orange = colors.HexColor('#E87722')
    light_bg = colors.HexColor('#f5f7fa')
    border_color = colors.HexColor('#dce3ef')

    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=0.5*inch, bottomMargin=0.5*inch,
        leftMargin=0.65*inch, rightMargin=0.65*inch
    )
    styles = getSampleStyleSheet()
    W = 7.2 * inch  # usable width

    title_style = ParagraphStyle('InvTitle', parent=styles['Normal'],
        textColor=navy, fontSize=26, fontName='Helvetica-Bold', spaceAfter=2)
    label_style = ParagraphStyle('Label', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor('#555555'))
    value_style = ParagraphStyle('Value', parent=styles['Normal'],
        fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#1a1a2e'))
    note_style = ParagraphStyle('Note', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor('#1a1a2e'), leading=13)
    bold_note_style = ParagraphStyle('BoldNote', parent=note_style,
        fontName='Helvetica-Bold')
    section_title_style = ParagraphStyle('SectionTitle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=8, textColor=navy,
        textTransform='uppercase', spaceBefore=4, spaceAfter=4)

    story = []

    # ── Logo + INVOICE title block ───────────────────────────────────────────
    import os as _os
    logo_path = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), 'assets', 'logo.svg')
    logo_element = None
    if _os.path.exists(logo_path):
        try:
            from svglib.svglib import svg2rlg
            drawing = svg2rlg(logo_path)
            if drawing:
                from reportlab.graphics import renderPDF
                # Scale logo to fit ~2.4 inch wide, proportional height
                target_w = 2.4 * inch
                scale = target_w / drawing.width
                drawing.width = target_w
                drawing.height = drawing.height * scale
                drawing.transform = (scale, 0, 0, scale, 0, 0)
                logo_element = drawing
        except Exception:
            pass

    # Build meta rows for invoice details
    meta_rows = [
        [Paragraph("Invoice #", label_style), Paragraph(invoice.invoice_number, value_style)],
    ]
    if invoice.plan_id:
        meta_rows.append([Paragraph("Plan ID", label_style), Paragraph(str(invoice.plan_id), value_style)])
    meta_rows += [
        [Paragraph("Invoice Date", label_style), Paragraph(str(invoice.invoice_date), value_style)],
        [Paragraph("Due Date", label_style), Paragraph(str(invoice.due_date), value_style)],
        [Paragraph("Status", label_style), Paragraph(invoice.status.value.upper(), value_style)],
    ]

    meta_table = Table(meta_rows, colWidths=[0.9*inch, 1.5*inch],
        style=TableStyle([
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('TOPPADDING', (0,0), (-1,-1), 3),
        ]))

    left_col = logo_element if logo_element else Paragraph("", styles['Normal'])
    header_data = [[left_col, Paragraph("INVOICE", title_style), meta_table]]
    header_table = Table(header_data, colWidths=[2.5*inch, W - 2.5*inch - 2.6*inch, 2.6*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (-1,-1), light_bg),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING', (0,0), (0,-1), 10),
        ('RIGHTPADDING', (-1,0), (-1,-1), 14),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.2*inch))

    # ── Line items ──────────────────────────────────────────────────────────
    line_headers = ["#", "Description", "Qty", "Unit Price", "Tax %", "Total"]
    line_data = [line_headers]
    for i, item in enumerate(invoice.line_items, 1):
        line_data.append([
            str(i),
            item.description,
            str(item.quantity),
            f"${float(item.unit_price):,.2f}",
            f"{float(item.tax_rate) * 100:.1f}%",
            f"${float(item.total_price):,.2f}",
        ])

    col_w = [0.3*inch, 3.1*inch, 0.65*inch, 0.95*inch, 0.65*inch, 0.95*inch]
    line_table = Table(line_data, colWidths=col_w, repeatRows=1)
    line_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), navy),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, light_bg]),
        ('GRID', (0, 0), (-1, -1), 0.4, border_color),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(line_table)
    story.append(Spacer(1, 0.15*inch))

    # ── Totals ───────────────────────────────────────────────────────────────
    totals_data = [
        ["Subtotal:", f"${float(invoice.subtotal):,.2f}"],
        ["Tax:", f"${float(invoice.tax_amount):,.2f}"],
        ["Discount:", f"-${float(invoice.discount_amount):,.2f}"],
        ["Total:", f"${float(invoice.total_amount):,.2f}"],
        ["Amount Paid:", f"${float(invoice.paid_amount):,.2f}"],
        ["Balance Due:", f"${float(invoice.balance_due):,.2f}"],
    ]
    totals_table = Table(totals_data, colWidths=[1.4*inch, 1.2*inch],
                         hAlign='RIGHT')
    totals_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('BACKGROUND', (0, -1), (-1, -1), navy),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
        ('LINEABOVE', (0, -1), (-1, -1), 1, navy),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 0.25*inch))

    # ── Payment instructions ─────────────────────────────────────────────────
    story.append(HRFlowable(width=W, thickness=1.5, color=navy))
    story.append(Spacer(1, 0.1*inch))

    story.append(Paragraph(
        "<b>Please Note:</b> If you have any questions with regards to this invoice, "
        "please contact John Jones III @ (260) 455 7708",
        note_style
    ))
    story.append(Spacer(1, 0.1*inch))

    story.append(Paragraph("For accurate payment processing:", bold_note_style))
    instructions = [
        "Use ACH/Wire Information provided below, or if paying by check, "
        "make the Check payable to <b>Lincoln Financial Group</b>",
        "Include Invoice Number on the Payment",
        "Provide detailed documentation of payment",
    ]
    for n, text in enumerate(instructions, 1):
        story.append(Paragraph(f"{n}.  {text}", note_style))

    story.append(Spacer(1, 0.15*inch))

    # Three-column payment methods table
    def payment_block(title, rows):
        block = [[Paragraph(title, section_title_style)]]
        block += [[Paragraph(f"<b>{k}</b>", note_style), Paragraph(v, note_style)] for k, v in rows]
        t = Table(block, colWidths=[1.2*inch, 1.1*inch])
        t.setStyle(TableStyle([
            ('SPAN', (0, 0), (1, 0)),
            ('BACKGROUND', (0, 0), (1, 0), light_bg),
            ('LINEBELOW', (0, 0), (1, 0), 0.5, navy),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOX', (0, 0), (-1, -1), 0.5, border_color),
        ]))
        return t

    ach_wire_rows = [
        ("Bank Account:", "0086411258"),
        ("Routing #:", "074900225"),
        ("Bank Acct. Name:", "Lincoln Ret etc.."),
        ("Bank Name:", "Wells Fargo Bank"),
        ("ATTN:", f"(Reference {invoice.invoice_number})"),
    ]

    check_rows = [
        ("", "Lincoln Retirement Services"),
        ("", "Financial Controls 1H-41"),
        ("", "PO BOX 2212"),
        ("", "Fort Wayne, IN 46801-2212"),
        ("ATTN:", f"(Reference {invoice.invoice_number})"),
    ]

    ach_block = payment_block("ACH Information", ach_wire_rows)
    wire_block = payment_block("Wire Information", ach_wire_rows)
    check_block = payment_block("Send Checks to:", check_rows)

    payment_table = Table([[ach_block, wire_block, check_block]],
                          colWidths=[W/3, W/3, W/3])
    payment_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(payment_table)

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
