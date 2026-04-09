"""Reporting, Dashboards & Analytics (FR-AR-060 – FR-AR-063)."""
import csv
import io
import os
from datetime import date, timedelta
from decimal import Decimal
from flask import (Blueprint, render_template, request, jsonify,
                   Response, current_app, send_file)
from flask_login import login_required
from sqlalchemy import func
from models import db, Invoice, Payment, Customer, DunningLog

reports_bp = Blueprint("reports", __name__)


# ── KPI helpers ───────────────────────────────────────────────────────────────

def _aging_summary():
    today = date.today()
    buckets = {"current": Decimal("0"), "1-30": Decimal("0"),
               "31-60": Decimal("0"), "61-90": Decimal("0"), "90+": Decimal("0")}
    open_invoices = Invoice.query.filter(
        Invoice.status.in_(["sent", "partial", "overdue"])
    ).all()
    for inv in open_invoices:
        b = inv.aging_bucket
        buckets[b] = buckets.get(b, Decimal("0")) + (inv.balance_due or Decimal("0"))
    return buckets


def _dso():
    """Days Sales Outstanding — rolling 90 days."""
    cutoff = date.today() - timedelta(days=90)
    total_ar = db.session.query(
        func.coalesce(func.sum(Invoice.balance_due), 0)
    ).filter(Invoice.status.in_(["sent", "partial", "overdue"])).scalar()

    total_revenue = db.session.query(
        func.coalesce(func.sum(Invoice.total_amount), 0)
    ).filter(Invoice.issue_date >= cutoff).scalar()

    if not total_revenue:
        return 0
    return round(float(total_ar) / (float(total_revenue) / 90), 1)


def _collection_trend(days=30):
    """Daily cash collected over the past N days."""
    cutoff = date.today() - timedelta(days=days)
    rows = db.session.query(
        Payment.payment_date,
        func.sum(Payment.amount_applied)
    ).filter(
        Payment.payment_date >= cutoff,
        Payment.status.in_(["posted", "applied"]),
    ).group_by(Payment.payment_date).order_by(Payment.payment_date).all()
    return [{"date": str(r[0]), "amount": float(r[1] or 0)} for r in rows]


# ── Dashboard (FR-AR-060) ─────────────────────────────────────────────────────

@reports_bp.route("/dashboard")
@login_required
def dashboard():
    aging = _aging_summary()
    dso = _dso()
    trend = _collection_trend()

    total_open = sum(aging.values())
    overdue_count = Invoice.query.filter(
        Invoice.due_date < date.today(),
        Invoice.status.in_(["sent", "partial"])
    ).count()

    exception_payments = Payment.query.filter_by(status="exception").count()

    return render_template("reports/dashboard.html",
                           aging=aging,
                           dso=dso,
                           trend=trend,
                           total_open=total_open,
                           overdue_count=overdue_count,
                           exception_payments=exception_payments,
                           today=date.today())


# ── Standard reports (FR-AR-061) ─────────────────────────────────────────────

@reports_bp.route("/aging")
@login_required
def aging_report():
    today = date.today()
    open_invoices = Invoice.query.filter(
        Invoice.status.in_(["sent", "partial", "overdue"])
    ).order_by(Invoice.due_date.asc()).all()

    by_customer = {}
    for inv in open_invoices:
        cname = inv.customer.company_name
        if cname not in by_customer:
            by_customer[cname] = {"invoices": [], "total": Decimal("0")}
        by_customer[cname]["invoices"].append(inv)
        by_customer[cname]["total"] += inv.balance_due or Decimal("0")

    return render_template("reports/aging.html",
                           by_customer=by_customer, today=today)


@reports_bp.route("/payment-history")
@login_required
def payment_history():
    customer_id = request.args.get("customer_id", type=int)
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    q = Payment.query.order_by(Payment.payment_date.desc())
    if customer_id:
        q = q.filter(Payment.customer_id == customer_id)
    if date_from:
        q = q.filter(Payment.payment_date >= date.fromisoformat(date_from))
    if date_to:
        q = q.filter(Payment.payment_date <= date.fromisoformat(date_to))

    payments = q.limit(500).all()
    customers = Customer.query.filter_by(is_active=True).order_by(Customer.company_name).all()
    return render_template("reports/payment_history.html",
                           payments=payments, customers=customers,
                           customer_id=customer_id)


@reports_bp.route("/cash-forecast")
@login_required
def cash_forecast():
    """Expected cash inflows by due date (next 60 days)."""
    today = date.today()
    horizon = today + timedelta(days=60)
    upcoming = Invoice.query.filter(
        Invoice.due_date.between(today, horizon),
        Invoice.status.in_(["sent", "partial"]),
    ).order_by(Invoice.due_date.asc()).all()

    by_week = {}
    for inv in upcoming:
        week_start = inv.due_date - timedelta(days=inv.due_date.weekday())
        key = str(week_start)
        by_week.setdefault(key, Decimal("0"))
        by_week[key] += inv.balance_due or Decimal("0")

    return render_template("reports/cash_forecast.html",
                           upcoming=upcoming, by_week=by_week, today=today)


# ── Ad-hoc export (FR-AR-062) ─────────────────────────────────────────────────

@reports_bp.route("/export/aging.csv")
@login_required
def export_aging_csv():
    open_invoices = Invoice.query.filter(
        Invoice.status.in_(["sent", "partial", "overdue"])
    ).order_by(Invoice.due_date.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Invoice #", "Customer", "Issue Date", "Due Date",
                     "Total", "Balance Due", "Days Overdue", "Aging Bucket"])
    for inv in open_invoices:
        writer.writerow([inv.invoice_number, inv.customer.company_name,
                         inv.issue_date, inv.due_date,
                         float(inv.total_amount), float(inv.balance_due),
                         inv.days_overdue, inv.aging_bucket])

    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=ar_aging.csv"})


# ── PDF helpers ───────────────────────────────────────────────────────────────

def _pdf_doc_with_logo(title, subtitle=""):
    """Return (buf, doc, story, styles_dict) with the LFG logo already appended."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle, HRFlowable)
    from reportlab.lib.enums import TA_RIGHT

    LFG_MAROON = colors.HexColor("#650030")
    LFG_ORANGE = colors.HexColor("#FF4F17")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            leftMargin=0.65*inch, rightMargin=0.65*inch,
                            topMargin=0.5*inch, bottomMargin=0.65*inch)

    base = getSampleStyleSheet()["Normal"]
    base.fontName  = "Helvetica"
    base.fontSize  = 9

    def S(name, **kw):
        return ParagraphStyle(name, parent=base, **kw)

    st = {
        "normal": base,
        "h1":     S("h1", fontSize=16, textColor=LFG_MAROON,
                    fontName="Helvetica-Bold", spaceAfter=2),
        "h2":     S("h2", fontSize=11, textColor=LFG_MAROON,
                    fontName="Helvetica-Bold", spaceAfter=4),
        "bold9":  S("b9", fontSize=9, fontName="Helvetica-Bold"),
        "right9": S("r9", fontSize=9, alignment=TA_RIGHT),
        "rbold":  S("rb", fontSize=9, fontName="Helvetica-Bold", alignment=TA_RIGHT),
        "small":  S("sm", fontSize=8, textColor=colors.HexColor("#6c757d")),
        "LFG_MAROON": LFG_MAROON,
        "LFG_ORANGE": LFG_ORANGE,
        "LIGHT_GRAY": colors.HexColor("#f4f6f9"),
    }

    story = []

    # ── Logo top-left ──────────────────────────────────────────────────────
    logo_path = os.path.join(current_app.root_path, "static", "img", "lfg-logo.svg")
    try:
        from svglib.svglib import svg2rlg
        rl_drawing = svg2rlg(logo_path)
        target_w = 2.2 * inch
        scale = target_w / rl_drawing.width
        rl_drawing.width  = target_w
        rl_drawing.height = rl_drawing.height * scale
        rl_drawing.transform = (scale, 0, 0, scale, 0, 0)
        logo_cell = rl_drawing
    except Exception:
        logo_cell = Paragraph(
            "<b><font color='#650030' size=14>Lincoln Financial Group</font></b>", base)

    title_para    = Paragraph(f"<b><font color='#650030' size=16>{title}</font></b>", base)
    meta_lines    = f"<b>Generated:</b> {date.today()}"
    if subtitle:
        meta_lines = f"{subtitle}<br/>{meta_lines}"
    meta_para = Paragraph(meta_lines, S("meta", fontSize=8, alignment=TA_RIGHT,
                                         textColor=colors.HexColor("#6c757d")))

    hdr = Table([[logo_cell, meta_para]], colWidths=[4*inch, 3.2*inch])
    hdr.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",         (1, 0), (1,  0),  "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(hdr)
    story.append(HRFlowable(width="100%", thickness=3,
                            color=LFG_ORANGE, spaceAfter=10))
    story.append(Paragraph(
        f"<b><font color='#650030' size=13>{title}</font></b>", base))
    story.append(Spacer(1, 6))

    return buf, doc, story, st


# ── PDF export routes ──────────────────────────────────────────────────────────

@reports_bp.route("/export/aging.pdf")
@login_required
def export_aging_pdf():
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

    open_invoices = Invoice.query.filter(
        Invoice.status.in_(["sent", "partial", "overdue"])
    ).order_by(Invoice.due_date.asc()).all()

    buf, doc, story, st = _pdf_doc_with_logo("AR Aging Report",
                                              f"As of {date.today()}")
    normal = st["normal"]
    bold9  = st["bold9"]
    rbold  = st["rbold"]
    right9 = st["right9"]
    MAROON = st["LFG_MAROON"]
    LGRAY  = st["LIGHT_GRAY"]

    by_customer = {}
    for inv in open_invoices:
        by_customer.setdefault(inv.customer.company_name, []).append(inv)

    for cname, invs in by_customer.items():
        story.append(Paragraph(f"<b>{cname}</b>", bold9))
        rows = [[
            Paragraph("<b>Invoice #</b>",   bold9),
            Paragraph("<b>Due Date</b>",    bold9),
            Paragraph("<b>Days Overdue</b>",bold9),
            Paragraph("<b>Bucket</b>",      bold9),
            Paragraph("<b>Balance Due</b>", rbold),
        ]]
        total = Decimal("0")
        for inv in invs:
            total += inv.balance_due or Decimal("0")
            rows.append([
                Paragraph(inv.invoice_number, normal),
                Paragraph(str(inv.due_date),  normal),
                Paragraph(str(inv.days_overdue), normal),
                Paragraph(inv.aging_bucket,   normal),
                Paragraph(f"${inv.balance_due:,.2f}", right9),
            ])
        rows.append(["", "", "", Paragraph("<b>Total</b>", rbold),
                     Paragraph(f"<b>${total:,.2f}</b>", rbold)])

        t = Table(rows, colWidths=[1.5*inch, 1.1*inch, 1.1*inch, 1.0*inch, 1.5*inch])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0),  MAROON),
            ("TEXTCOLOR",     (0,0), (-1,0),  colors.white),
            ("ROWBACKGROUNDS",(0,1),(-1,-2),  [colors.white, LGRAY]),
            ("LINEABOVE",     (0,-1),(-1,-1), 0.75, MAROON),
            ("GRID",          (0,0), (-1,-2), 0.25, colors.HexColor("#dee2e6")),
            ("TOPPADDING",    (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ("LEFTPADDING",   (0,0), (-1,-1), 5),
        ]))
        story.append(t)
        story.append(Spacer(1, 10))

    doc.build(story)
    return send_file(io.BytesIO(buf.getvalue()), mimetype="application/pdf",
                     as_attachment=True, download_name="ar_aging.pdf")


@reports_bp.route("/export/payment-history.pdf")
@login_required
def export_payment_history_pdf():
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

    customer_id = request.args.get("customer_id", type=int)
    date_from   = request.args.get("date_from")
    date_to     = request.args.get("date_to")

    q = Payment.query.order_by(Payment.payment_date.desc())
    if customer_id:
        q = q.filter(Payment.customer_id == customer_id)
    if date_from:
        q = q.filter(Payment.payment_date >= date.fromisoformat(date_from))
    if date_to:
        q = q.filter(Payment.payment_date <= date.fromisoformat(date_to))
    payments = q.limit(500).all()

    subtitle = f"{'From ' + date_from if date_from else ''}" \
               f"{'  To ' + date_to if date_to else ''}"
    buf, doc, story, st = _pdf_doc_with_logo("Payment History Report",
                                              subtitle.strip() or f"All dates · {date.today()}")
    normal = st["normal"]
    bold9  = st["bold9"]
    rbold  = st["rbold"]
    right9 = st["right9"]
    MAROON = st["LFG_MAROON"]
    LGRAY  = st["LIGHT_GRAY"]

    rows = [[
        Paragraph("<b>Payment #</b>",  bold9),
        Paragraph("<b>Date</b>",       bold9),
        Paragraph("<b>Customer</b>",   bold9),
        Paragraph("<b>Method</b>",     bold9),
        Paragraph("<b>Status</b>",     bold9),
        Paragraph("<b>Amount</b>",     rbold),
    ]]
    total = Decimal("0")
    for p in payments:
        total += p.amount_applied or Decimal("0")
        rows.append([
            Paragraph(p.payment_number, normal),
            Paragraph(str(p.payment_date), normal),
            Paragraph(p.customer.company_name, normal),
            Paragraph(p.payment_method or "", normal),
            Paragraph(p.status.title(), normal),
            Paragraph(f"${p.amount_applied:,.2f}", right9),
        ])
    rows.append(["", "", "", "", Paragraph("<b>Total</b>", rbold),
                 Paragraph(f"<b>${total:,.2f}</b>", rbold)])

    t = Table(rows, colWidths=[1.3*inch, 0.9*inch, 1.8*inch, 0.9*inch, 0.8*inch, 1.1*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  MAROON),
        ("TEXTCOLOR",     (0,0), (-1,0),  colors.white),
        ("ROWBACKGROUNDS",(0,1),(-1,-2),  [colors.white, LGRAY]),
        ("LINEABOVE",     (0,-1),(-1,-1), 0.75, MAROON),
        ("GRID",          (0,0), (-1,-2), 0.25, colors.HexColor("#dee2e6")),
        ("TOPPADDING",    (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("LEFTPADDING",   (0,0), (-1,-1), 5),
    ]))
    story.append(t)

    doc.build(story)
    return send_file(io.BytesIO(buf.getvalue()), mimetype="application/pdf",
                     as_attachment=True, download_name="payment_history.pdf")


@reports_bp.route("/export/cash-forecast.pdf")
@login_required
def export_cash_forecast_pdf():
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

    today   = date.today()
    horizon = today + timedelta(days=60)
    upcoming = Invoice.query.filter(
        Invoice.due_date.between(today, horizon),
        Invoice.status.in_(["sent", "partial"]),
    ).order_by(Invoice.due_date.asc()).all()

    buf, doc, story, st = _pdf_doc_with_logo("Cash Flow Forecast",
                                              f"Next 60 days · {today} – {horizon}")
    normal = st["normal"]
    bold9  = st["bold9"]
    rbold  = st["rbold"]
    right9 = st["right9"]
    MAROON = st["LFG_MAROON"]
    LGRAY  = st["LIGHT_GRAY"]

    rows = [[
        Paragraph("<b>Invoice #</b>",  bold9),
        Paragraph("<b>Customer</b>",   bold9),
        Paragraph("<b>Due Date</b>",   bold9),
        Paragraph("<b>Status</b>",     bold9),
        Paragraph("<b>Expected</b>",   rbold),
    ]]
    total = Decimal("0")
    for inv in upcoming:
        total += inv.balance_due or Decimal("0")
        rows.append([
            Paragraph(inv.invoice_number, normal),
            Paragraph(inv.customer.company_name, normal),
            Paragraph(str(inv.due_date), normal),
            Paragraph(inv.status.title(), normal),
            Paragraph(f"${inv.balance_due:,.2f}", right9),
        ])
    rows.append(["", "", "", Paragraph("<b>Total Expected</b>", rbold),
                 Paragraph(f"<b>${total:,.2f}</b>", rbold)])

    t = Table(rows, colWidths=[1.4*inch, 2.2*inch, 1.0*inch, 0.9*inch, 1.2*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  MAROON),
        ("TEXTCOLOR",     (0,0), (-1,0),  colors.white),
        ("ROWBACKGROUNDS",(0,1),(-1,-2),  [colors.white, LGRAY]),
        ("LINEABOVE",     (0,-1),(-1,-1), 0.75, MAROON),
        ("GRID",          (0,0), (-1,-2), 0.25, colors.HexColor("#dee2e6")),
        ("TOPPADDING",    (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("LEFTPADDING",   (0,0), (-1,-1), 5),
    ]))
    story.append(t)

    doc.build(story)
    return send_file(io.BytesIO(buf.getvalue()), mimetype="application/pdf",
                     as_attachment=True, download_name="cash_forecast.pdf")


# ── JSON API for dashboard charts ─────────────────────────────────────────────

@reports_bp.route("/api/aging-chart")
@login_required
def api_aging_chart():
    aging = _aging_summary()
    return jsonify({k: float(v) for k, v in aging.items()})


@reports_bp.route("/api/trend")
@login_required
def api_trend():
    days = request.args.get("days", 30, type=int)
    return jsonify(_collection_trend(days))


@reports_bp.route("/api/kpis")
@login_required
def api_kpis():
    aging = _aging_summary()
    return jsonify({
        "dso": _dso(),
        "total_open_ar": float(sum(aging.values())),
        "overdue_count": Invoice.query.filter(
            Invoice.due_date < date.today(),
            Invoice.status.in_(["sent", "partial"])
        ).count(),
        "on_time_rate": _on_time_payment_rate(),
    })


def _on_time_payment_rate():
    paid = Invoice.query.filter_by(status="paid").count()
    if not paid:
        return 0
    on_time = Invoice.query.filter(
        Invoice.status == "paid",
        Invoice.paid_at != None,
        func.date(Invoice.paid_at) <= Invoice.due_date,
    ).count()
    return round(on_time / paid * 100, 1)
