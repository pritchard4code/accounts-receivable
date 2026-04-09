"""Invoice Management (FR-AR-001 – FR-AR-004)."""
from datetime import date, timedelta
from decimal import Decimal
import io, os
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, jsonify, current_app, send_file)
from flask_login import login_required, current_user
from models import db, Invoice, InvoiceLineItem, Customer, GLEntry, AuditLog
from ar.utils import role_required, log_action, next_sequence

invoices_bp = Blueprint("invoices", __name__)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _build_invoice_number():
    return next_sequence("INV")


def _post_to_gl(invoice):
    """Create AR debit + revenue credit GL entries (FR-AR-032)."""
    entries = [
        GLEntry(invoice_id=invoice.id, entry_type="ar_debit",
                account_code="1200",
                debit_amount=invoice.total_amount, credit_amount=Decimal("0.00"),
                description=f"AR {invoice.invoice_number}"),
        GLEntry(invoice_id=invoice.id, entry_type="revenue_credit",
                account_code="4000",
                debit_amount=Decimal("0.00"), credit_amount=invoice.subtotal,
                description=f"Revenue {invoice.invoice_number}"),
    ]
    if invoice.tax_amount:
        entries.append(GLEntry(
            invoice_id=invoice.id, entry_type="tax_credit",
            account_code="2200",
            debit_amount=Decimal("0.00"), credit_amount=invoice.tax_amount,
            description=f"Tax {invoice.invoice_number}"))
    db.session.add_all(entries)
    invoice.gl_posted = True
    from datetime import datetime, timezone
    invoice.gl_posted_at = datetime.now(timezone.utc)


# ── Routes ───────────────────────────────────────────────────────────────────

@invoices_bp.route("/")
@login_required
def list_invoices():
    status_filter = request.args.get("status", "")
    customer_id = request.args.get("customer_id", type=int)
    q = Invoice.query.order_by(Invoice.due_date.asc())
    if status_filter:
        q = q.filter(Invoice.status == status_filter)
    if customer_id:
        q = q.filter(Invoice.customer_id == customer_id)
    invoices = q.all()
    customers = Customer.query.filter_by(is_active=True).order_by(Customer.company_name).all()
    return render_template("invoices/list.html", invoices=invoices,
                           customers=customers, status_filter=status_filter)


@invoices_bp.route("/new", methods=["GET", "POST"])
@login_required
@role_required("ar_clerk", "finance_manager", "admin")
def new_invoice():
    customers = Customer.query.filter_by(is_active=True).order_by(Customer.company_name).all()

    if request.method == "POST":
        customer_id = request.form.get("customer_id", type=int)
        customer = db.session.get(Customer, customer_id)
        if not customer:
            flash("Customer not found.", "danger")
            return redirect(url_for("invoices.new_invoice"))

        # Check credit limit (FR-AR-042)
        requested = Decimal(request.form.get("subtotal", "0"))
        if customer.credit_status == "hold":
            flash(f"{customer.company_name} is on credit hold. Invoice blocked.", "danger")
            return redirect(url_for("invoices.new_invoice"))
        if customer.outstanding_balance + requested > customer.credit_limit:
            flash(f"Warning: this invoice would exceed {customer.company_name}'s credit limit "
                  f"(${customer.credit_limit:,.2f}).", "warning")

        issue_date = date.fromisoformat(request.form["issue_date"])
        terms = customer.payment_terms_days
        due_date = issue_date + timedelta(days=terms)

        invoice = Invoice(
            invoice_number=_build_invoice_number(),
            customer_id=customer_id,
            invoice_type=request.form.get("invoice_type", "one_time"),
            issue_date=issue_date,
            due_date=due_date,
            source_type=request.form.get("source_type"),
            source_ref=request.form.get("source_ref"),
            notes=request.form.get("notes"),
            created_by_id=current_user.id,
        )
        db.session.add(invoice)
        db.session.flush()   # get invoice.id

        # Line items
        descriptions = request.form.getlist("description[]")
        quantities = request.form.getlist("quantity[]")
        unit_prices = request.form.getlist("unit_price[]")
        tax_rates = request.form.getlist("tax_rate[]")

        for desc, qty, price, tax in zip(descriptions, quantities, unit_prices, tax_rates):
            if not desc.strip():
                continue
            q = Decimal(qty or "1")
            p = Decimal(price or "0")
            t = Decimal(tax or "0") / 100
            total = q * p
            li = InvoiceLineItem(invoice_id=invoice.id, description=desc,
                                 quantity=q, unit_price=p, tax_rate=t, line_total=total)
            db.session.add(li)

        db.session.flush()
        invoice.recalculate_totals()

        # Apply tax
        tax_pct = Decimal(request.form.get("invoice_tax_pct", "0")) / 100
        invoice.tax_amount = invoice.subtotal * tax_pct
        invoice.total_amount = invoice.subtotal + invoice.tax_amount
        invoice.balance_due = invoice.total_amount

        _post_to_gl(invoice)
        log_action("invoice_created", "Invoice", invoice.id,
                   new_data={"number": invoice.invoice_number, "total": str(invoice.total_amount)})
        db.session.commit()

        flash(f"Invoice {invoice.invoice_number} created.", "success")
        return redirect(url_for("invoices.invoice_detail", invoice_id=invoice.id))

    return render_template("invoices/new.html", customers=customers, today=date.today())


@invoices_bp.route("/<int:invoice_id>")
@login_required
def invoice_detail(invoice_id):
    invoice = db.get_or_404(Invoice, invoice_id)
    return render_template("invoices/detail.html", invoice=invoice,
                           company_name=current_app.config["COMPANY_NAME"],
                           company_logo=current_app.config["COMPANY_LOGO_URL"],
                           company_address=current_app.config["COMPANY_ADDRESS"])


@invoices_bp.route("/<int:invoice_id>/send", methods=["POST"])
@login_required
@role_required("ar_clerk", "finance_manager", "admin")
def send_invoice(invoice_id):
    invoice = db.get_or_404(Invoice, invoice_id)
    if invoice.status != "draft":
        flash("Only draft invoices can be sent.", "warning")
        return redirect(url_for("invoices.invoice_detail", invoice_id=invoice_id))

    from ar.utils import send_invoice_email
    send_invoice_email(invoice)

    invoice.status = "sent"
    from datetime import datetime, timezone
    invoice.sent_at = datetime.now(timezone.utc)
    log_action("invoice_sent", "Invoice", invoice.id)
    db.session.commit()
    flash(f"Invoice {invoice.invoice_number} sent to {invoice.customer.email}.", "success")
    return redirect(url_for("invoices.invoice_detail", invoice_id=invoice_id))


@invoices_bp.route("/<int:invoice_id>/void", methods=["POST"])
@login_required
@role_required("finance_manager", "admin")
def void_invoice(invoice_id):
    invoice = db.get_or_404(Invoice, invoice_id)
    if invoice.status == "paid":
        flash("Cannot void a paid invoice.", "danger")
        return redirect(url_for("invoices.invoice_detail", invoice_id=invoice_id))

    invoice.status = "void"
    log_action("invoice_voided", "Invoice", invoice.id)
    db.session.commit()
    flash(f"Invoice {invoice.invoice_number} voided.", "info")
    return redirect(url_for("invoices.list_invoices"))


@invoices_bp.route("/<int:invoice_id>/pdf")
@login_required
def invoice_pdf(invoice_id):
    """Generate and return a PDF of the invoice (FR-AR-004)."""
    invoice = db.get_or_404(Invoice, invoice_id)
    pdf_bytes = _generate_invoice_pdf(invoice)
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{invoice.invoice_number}.pdf",
    )


def _generate_invoice_pdf(invoice):
    """Build a branded PDF invoice with payment instructions using ReportLab."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle, HRFlowable, Image)
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

    LFG_MAROON = colors.HexColor("#650030")
    LFG_ORANGE = colors.HexColor("#FF4F17")
    LIGHT_GRAY = colors.HexColor("#f4f6f9")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            leftMargin=0.65*inch, rightMargin=0.65*inch,
                            topMargin=0.5*inch, bottomMargin=0.65*inch)

    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    normal.fontName = "Helvetica"
    normal.fontSize = 9

    def style(name, **kw):
        s = ParagraphStyle(name, parent=normal, **kw)
        return s

    h1     = style("h1", fontSize=16, textColor=LFG_MAROON, fontName="Helvetica-Bold", spaceAfter=2)
    h2     = style("h2", fontSize=11, textColor=LFG_MAROON, fontName="Helvetica-Bold", spaceAfter=4)
    h3     = style("h3", fontSize=9,  textColor=LFG_MAROON, fontName="Helvetica-Bold", spaceAfter=2)
    small  = style("sm", fontSize=8,  textColor=colors.HexColor("#6c757d"))
    bold9  = style("b9", fontSize=9,  fontName="Helvetica-Bold")
    right9 = style("r9", fontSize=9,  alignment=TA_RIGHT)
    rbold  = style("rb", fontSize=9,  fontName="Helvetica-Bold", alignment=TA_RIGHT)
    note   = style("nt", fontSize=8,  textColor=colors.HexColor("#333333"), leading=12)

    story = []

    # ── Header: logo + invoice title ────────────────────────────────────────
    logo_path = os.path.join(current_app.root_path, "static", "img", "lfg-logo.svg")
    try:
        from svglib.svglib import svg2rlg
        from reportlab.graphics import renderPDF
        rl_drawing = svg2rlg(logo_path)
        # Scale to fit ~2.2 inch wide while preserving aspect ratio
        target_w = 2.2 * inch
        scale = target_w / rl_drawing.width
        rl_drawing.width  = target_w
        rl_drawing.height = rl_drawing.height * scale
        rl_drawing.transform = (scale, 0, 0, scale, 0, 0)
        logo_cell = rl_drawing
    except Exception:
        logo_cell = Paragraph(
            "<b><font color='#650030' size=14>Lincoln Financial Group</font></b>", normal
        )

    inv_title = Paragraph(f"<b><font color='#650030' size=18>INVOICE</font></b>", normal)
    inv_meta  = Paragraph(
        f"<b>Invoice #:</b> {invoice.invoice_number}<br/>"
        f"<b>Issue Date:</b> {invoice.issue_date}<br/>"
        f"<b>Due Date:</b>  {invoice.due_date}",
        style("im", fontSize=9, alignment=TA_RIGHT)
    )

    header_table = Table([[logo_cell, inv_title]], colWidths=[4*inch, 3.2*inch])
    header_table.setStyle(TableStyle([
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN",       (1,0), (1,0),  "RIGHT"),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=3, color=LFG_ORANGE, spaceAfter=6))

    # ── Bill From / Bill To ──────────────────────────────────────────────────
    from_text = Paragraph(
        "<b>From:</b><br/>"
        "Lincoln Financial Group<br/>"
        "Lincoln Retirement Services<br/>"
        "PO Box 2212, Fort Wayne, IN 46801",
        note
    )
    to_text = Paragraph(
        f"<b>Bill To:</b><br/>"
        f"{invoice.customer.company_name}<br/>"
        f"{invoice.customer.contact_name or ''}<br/>"
        f"{invoice.customer.email or ''}",
        note
    )
    meta_text = Paragraph(
        f"<b>Invoice #:</b> {invoice.invoice_number}<br/>"
        f"<b>Issue Date:</b> {invoice.issue_date}<br/>"
        f"<b>Due Date:</b> {invoice.due_date}",
        style("mt", fontSize=9, alignment=TA_RIGHT)
    )

    addr_table = Table([[from_text, to_text, meta_text]],
                       colWidths=[2.4*inch, 2.4*inch, 2.4*inch])
    addr_table.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
    ]))
    story.append(addr_table)

    # ── Line items table ─────────────────────────────────────────────────────
    li_data = [[
        Paragraph("<b>Description</b>", bold9),
        Paragraph("<b>Qty</b>", rbold),
        Paragraph("<b>Unit Price</b>", rbold),
        Paragraph("<b>Total</b>", rbold),
    ]]
    for li in invoice.line_items:
        li_data.append([
            Paragraph(li.description, normal),
            Paragraph(str(li.quantity), right9),
            Paragraph(f"${li.unit_price:,.2f}", right9),
            Paragraph(f"${li.line_total:,.2f}", right9),
        ])

    # Totals rows
    li_data += [
        ["", "", Paragraph("Subtotal", right9),   Paragraph(f"${invoice.subtotal:,.2f}", right9)],
        ["", "", Paragraph("Tax",      right9),   Paragraph(f"${invoice.tax_amount:,.2f}", right9)],
    ]
    if invoice.late_fee_amount:
        li_data.append(["", "", Paragraph("<font color='red'>Late Fee</font>", right9),
                        Paragraph(f"<font color='red'>${invoice.late_fee_amount:,.2f}</font>", right9)])
    li_data.append(["", "", Paragraph("<b>Total Due</b>", rbold),
                    Paragraph(f"<b>${invoice.balance_due:,.2f}</b>", rbold)])

    col_w = [3.5*inch, 0.7*inch, 1.2*inch, 1.3*inch]
    items_table = Table(li_data, colWidths=col_w, repeatRows=1)
    items_table.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,0), LFG_MAROON),
        ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
        ("ROWBACKGROUNDS",(0,1),(-1,-5), [colors.white, LIGHT_GRAY]),
        ("GRID",         (0,0), (-1,-5), 0.25, colors.HexColor("#dee2e6")),
        ("LINEABOVE",    (0,-4),(-1,-4), 0.5, colors.HexColor("#adb5bd")),
        ("LINEABOVE",    (0,-1),(-1,-1), 1,   LFG_MAROON),
        ("FONTNAME",     (0,-1),(-1,-1), "Helvetica-Bold"),
        ("FONTSIZE",     (0,-1),(-1,-1), 10),
        ("TOPPADDING",   (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0), (-1,-1), 4),
        ("LEFTPADDING",  (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(items_table)

    if invoice.notes:
        story.append(Spacer(1, 8))
        story.append(Paragraph(f"<b>Notes:</b> {invoice.notes}", small))

    # ── Payment instructions note ────────────────────────────────────────────
    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=1, color=LFG_ORANGE, spaceAfter=8))
    story.append(Paragraph("<b>Please Note:</b>", h3))
    story.append(Paragraph(
        "If you have any questions with regards to this invoice, please contact "
        "<b>Andrew Elliot @ (260) 334-4456</b>",
        note
    ))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "For accurate payment processing:",
        bold9
    ))
    story.append(Paragraph(
        "1. Use ACH/Wire information provided below or, if paying by check, "
        "make the check payable to <b>\"Lincoln Financial Group\"</b><br/>"
        "2. Include <b>\"Invoice Number\"</b> on payment<br/>"
        "3. Provide detailed documentation of payment",
        note
    ))
    story.append(Spacer(1, 10))

    inv_ref = invoice.invoice_number

    def pay_block(title, rows):
        data = [[Paragraph(f"<b>{title}</b>", style("pt", fontSize=9, textColor=colors.white))]]
        for label, val in rows:
            data.append([Paragraph(f"<b>{label}</b>  {val}", note)])
        t = Table(data, colWidths=[2.2*inch])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(0,0),  LFG_MAROON),
            ("TEXTCOLOR",     (0,0),(0,0),  colors.white),
            ("BACKGROUND",    (0,1),(0,-1), LIGHT_GRAY),
            ("BOX",           (0,0),(0,-1), 0.5, LFG_MAROON),
            ("TOPPADDING",    (0,0),(0,-1), 4),
            ("BOTTOMPADDING", (0,0),(0,-1), 4),
            ("LEFTPADDING",   (0,0),(0,-1), 6),
        ]))
        return t

    ach_block  = pay_block("ACH Information", [
        ("Bank Account:", "0086433344"),
        ("Routing #:",    "074977334"),
        ("Acct. Name:",   "Linc Ret SVCS Corp"),
        ("Bank:",         "Wells Fargo Bank, NA."),
        ("ATTN:",         f"(Ref: {inv_ref})"),
    ])
    wire_block = pay_block("Wire Information", [
        ("Bank Account:", "0086433344"),
        ("Routing #:",    "121977334"),
        ("Acct. Name:",   "Linc Ret SVCS Corp"),
        ("Bank:",         "Wells Fargo Bank, NA."),
        ("ATTN:",         f"(Ref: {inv_ref})"),
    ])
    check_block = pay_block("Send Checks To", [
        ("Payable To:",  "Lincoln Financial Group"),
        ("",             "Lincoln Retirement Services"),
        ("",             "Financial Controls 1H-41"),
        ("",             "PO Box 2212"),
        ("",             "Fort Wayne, IN 46801-2212"),
        ("ATTN:",        f"(Ref: {inv_ref})"),
    ])

    pay_row = Table([[ach_block, wire_block, check_block]],
                    colWidths=[2.35*inch, 2.35*inch, 2.35*inch],
                    hAlign="LEFT")
    pay_row.setStyle(TableStyle([
        ("VALIGN",       (0,0),(-1,-1), "TOP"),
        ("LEFTPADDING",  (0,0),(-1,-1), 0),
        ("RIGHTPADDING", (0,0),(-1,-1), 6),
    ]))
    story.append(pay_row)

    doc.build(story)
    return buf.getvalue()


@invoices_bp.route("/api/overdue")
@login_required
def api_overdue():
    """JSON list of overdue invoices — used by dashboard."""
    from sqlalchemy import func
    overdue = Invoice.query.filter(
        Invoice.due_date < date.today(),
        Invoice.status.in_(["sent", "partial"])
    ).all()
    return jsonify([{
        "id": inv.id,
        "invoice_number": inv.invoice_number,
        "customer": inv.customer.company_name,
        "balance_due": float(inv.balance_due),
        "days_overdue": inv.days_overdue,
        "aging_bucket": inv.aging_bucket,
    } for inv in overdue])
