"""
Seed script — creates all tables and populates realistic AR demo data.
Run once: py seed.py
"""
import os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date, timedelta, datetime, timezone
from decimal import Decimal
from werkzeug.security import generate_password_hash

from app import create_app
from models import (db, User, Customer, Invoice, InvoiceLineItem,
                    Payment, PaymentAllocation, DunningRule, DunningLog,
                    CreditEvent, Dispute, GLEntry, AuditLog)

app = create_app("development")

def seed():
    with app.app_context():
        # Create sequence + tables
        from ar.utils import _ensure_sequence
        db.create_all()
        _ensure_sequence()

        # ── Users ─────────────────────────────────────────────────────────
        if User.query.count() == 0:
            users = [
                User(email="admin@lfg.com",
                     password_hash=generate_password_hash("admin123"),
                     full_name="System Admin", role="admin"),
                User(email="arclerk@lfg.com",
                     password_hash=generate_password_hash("clerk123"),
                     full_name="Sarah Chen", role="ar_clerk"),
                User(email="collector@lfg.com",
                     password_hash=generate_password_hash("coll123"),
                     full_name="Mike Torres", role="collections_specialist"),
                User(email="finance@lfg.com",
                     password_hash=generate_password_hash("fin123"),
                     full_name="Priya Patel", role="finance_manager"),
                User(email="credit@lfg.com",
                     password_hash=generate_password_hash("cred123"),
                     full_name="James Wright", role="credit_manager"),
            ]
            db.session.add_all(users)
            db.session.flush()
            admin = users[0]
            print(f"  Created {len(users)} users.")
        else:
            admin = User.query.filter_by(role="admin").first()

        # ── Dunning Rules ─────────────────────────────────────────────────
        if DunningRule.query.count() == 0:
            rules = [
                DunningRule(name="Friendly Reminder",    days_past_due=3,
                            template_name="dunning_reminder",      sort_order=1),
                DunningRule(name="First Notice",         days_past_due=10,
                            template_name="dunning_first_notice",  sort_order=2),
                DunningRule(name="Second Notice + Fee",  days_past_due=20,
                            template_name="dunning_second_notice", apply_late_fee=True, sort_order=3),
                DunningRule(name="Final Demand",         days_past_due=45,
                            template_name="dunning_final_demand",  sort_order=4),
            ]
            db.session.add_all(rules)
            print(f"  Created {len(rules)} dunning rules.")

        # ── Customers ─────────────────────────────────────────────────────
        if Customer.query.count() == 0:
            customers_data = [
                dict(customer_number="CUST-001", company_name="Acme Corporation",
                     contact_name="John Smith",    email="john.smith@acme.com",
                     phone="215-555-0101", city="Philadelphia", state="PA",
                     credit_limit=Decimal("50000"), payment_terms_days=30, risk_score=10),
                dict(customer_number="CUST-002", company_name="Globex Industries",
                     contact_name="Jane Doe",      email="jane.doe@globex.com",
                     phone="212-555-0202", city="New York",    state="NY",
                     credit_limit=Decimal("100000"), payment_terms_days=45, risk_score=25),
                dict(customer_number="CUST-003", company_name="Initech LLC",
                     contact_name="Bob Johnson",   email="bob.j@initech.com",
                     phone="312-555-0303", city="Chicago",     state="IL",
                     credit_limit=Decimal("25000"), payment_terms_days=30, risk_score=60,
                     credit_status="watch"),
                dict(customer_number="CUST-004", company_name="Umbrella Corp",
                     contact_name="Alice Cooper",  email="acooper@umbrella.com",
                     phone="404-555-0404", city="Atlanta",     state="GA",
                     credit_limit=Decimal("75000"), payment_terms_days=60, risk_score=15),
                dict(customer_number="CUST-005", company_name="Vandelay Industries",
                     contact_name="Art Vandelay",  email="art@vandelay.com",
                     phone="617-555-0505", city="Boston",      state="MA",
                     credit_limit=Decimal("15000"), payment_terms_days=30, risk_score=80,
                     credit_status="hold"),
                dict(customer_number="CUST-006", company_name="Prestige Worldwide",
                     contact_name="Cal Naughton",  email="cal@prestige.com",
                     phone="704-555-0606", city="Charlotte",   state="NC",
                     credit_limit=Decimal("40000"), payment_terms_days=30, risk_score=35),
            ]
            customers = [Customer(**d) for d in customers_data]
            db.session.add_all(customers)
            db.session.flush()
            print(f"  Created {len(customers)} customers.")
        else:
            customers = Customer.query.order_by(Customer.id).all()

        db.session.commit()

        # ── Helper: next sequence ─────────────────────────────────────────
        def next_seq(prefix):
            from sqlalchemy import text
            n = db.session.execute(text("SELECT nextval('doc_sequence')")).scalar()
            return f"{prefix}-{n:06d}"

        # ── Invoices ──────────────────────────────────────────────────────
        today = date.today()
        if Invoice.query.count() == 0:
            inv_data = [
                # Acme — paid
                dict(customer=customers[0], issue_date=today - timedelta(days=45),
                     days_terms=30, status="paid",
                     lines=[("Professional Services Q1", 40, Decimal("150"), Decimal("0.08")),
                            ("Software License - Annual", 1, Decimal("2500"), Decimal("0.00"))]),
                # Acme — current
                dict(customer=customers[0], issue_date=today - timedelta(days=10),
                     days_terms=30, status="sent",
                     lines=[("Consulting Hours - March", 25, Decimal("175"), Decimal("0.08")),
                            ("Travel Expenses", 1, Decimal("450"), Decimal("0.00"))]),
                # Globex — partial
                dict(customer=customers[1], issue_date=today - timedelta(days=50),
                     days_terms=45, status="partial",
                     lines=[("Enterprise Support Contract", 1, Decimal("8500"), Decimal("0.00")),
                            ("Implementation Services", 20, Decimal("200"), Decimal("0.08"))]),
                # Globex — overdue 15 days
                dict(customer=customers[1], issue_date=today - timedelta(days=60),
                     days_terms=45, status="sent",
                     lines=[("Data Analytics Platform", 1, Decimal("12000"), Decimal("0.00")),
                            ("Training Sessions", 3, Decimal("1200"), Decimal("0.08"))]),
                # Initech — overdue 35 days
                dict(customer=customers[2], issue_date=today - timedelta(days=65),
                     days_terms=30, status="sent",
                     lines=[("IT Managed Services", 1, Decimal("3200"), Decimal("0.08")),
                            ("Hardware Maintenance", 1, Decimal("750"), Decimal("0.00"))]),
                # Initech — overdue 65 days (high risk)
                dict(customer=customers[2], issue_date=today - timedelta(days=95),
                     days_terms=30, status="sent",
                     lines=[("Network Infrastructure", 1, Decimal("5500"), Decimal("0.08"))]),
                # Umbrella — current
                dict(customer=customers[3], issue_date=today - timedelta(days=20),
                     days_terms=60, status="sent",
                     lines=[("Insurance Analytics Suite", 1, Decimal("18500"), Decimal("0.00")),
                            ("API Integration", 10, Decimal("500"), Decimal("0.08"))]),
                # Umbrella — paid
                dict(customer=customers[3], issue_date=today - timedelta(days=90),
                     days_terms=60, status="paid",
                     lines=[("Quarterly Service Fee", 1, Decimal("9000"), Decimal("0.00"))]),
                # Vandelay — overdue 90+ days (hold)
                dict(customer=customers[4], issue_date=today - timedelta(days=130),
                     days_terms=30, status="sent",
                     lines=[("Export Services", 1, Decimal("4200"), Decimal("0.08")),
                            ("Compliance Consulting", 8, Decimal("175"), Decimal("0.00"))]),
                # Prestige — disputed
                dict(customer=customers[5], issue_date=today - timedelta(days=40),
                     days_terms=30, status="disputed",
                     lines=[("Marketing Campaign Management", 1, Decimal("6800"), Decimal("0.00")),
                            ("Creative Assets", 5, Decimal("400"), Decimal("0.08"))]),
                # Prestige — draft
                dict(customer=customers[5], issue_date=today,
                     days_terms=30, status="draft",
                     lines=[("Brand Strategy Consulting", 15, Decimal("220"), Decimal("0.08"))]),
            ]

            invoices = []
            for d in inv_data:
                cust = d["customer"]
                iss = d["issue_date"]
                due = iss + timedelta(days=d["days_terms"])
                inv = Invoice(
                    invoice_number=next_seq("INV"),
                    customer_id=cust.id,
                    issue_date=iss, due_date=due,
                    status=d["status"],
                    created_by_id=admin.id,
                    gl_posted=True,
                    gl_posted_at=datetime.now(timezone.utc),
                )
                db.session.add(inv)
                db.session.flush()

                sub = Decimal("0")
                tax_total = Decimal("0")
                for desc, qty, price, tax_pct in d["lines"]:
                    lt = Decimal(str(qty)) * price
                    sub += lt
                    tax_total += lt * tax_pct
                    li = InvoiceLineItem(invoice_id=inv.id, description=desc,
                                        quantity=Decimal(str(qty)), unit_price=price,
                                        tax_rate=tax_pct, line_total=lt)
                    db.session.add(li)

                inv.subtotal = sub
                inv.tax_amount = tax_total.quantize(Decimal("0.01"))
                inv.total_amount = sub + inv.tax_amount
                inv.balance_due = inv.total_amount
                inv.amount_paid = Decimal("0")

                if d["status"] in ("sent", "partial", "paid", "disputed"):
                    inv.sent_at = datetime.now(timezone.utc)

                invoices.append(inv)

            db.session.flush()
            print(f"  Created {len(invoices)} invoices.")

            # ── Payments ──────────────────────────────────────────────────
            # Acme inv[0] — fully paid
            _make_payment(next_seq, admin, invoices[0], invoices[0].total_amount,
                          "ach", invoices[0].due_date - timedelta(days=3), full=True)

            # Globex inv[2] — partial payment $5000
            _make_payment(next_seq, admin, invoices[2], Decimal("5000"),
                          "wire", invoices[2].due_date + timedelta(days=5), full=False)

            # Umbrella inv[7] — fully paid
            _make_payment(next_seq, admin, invoices[7], invoices[7].total_amount,
                          "ach", invoices[7].due_date - timedelta(days=10), full=True)

            # Unapplied exception payment
            exc_pmt = Payment(
                payment_number=next_seq("PAY"),
                customer_id=customers[0].id,
                amount=Decimal("1000.00"),
                amount_applied=Decimal("0"),
                amount_unapplied=Decimal("1000.00"),
                payment_method="check",
                payment_date=today - timedelta(days=5),
                reference_number="CHK-99912",
                status="exception",
                posted_by_id=admin.id,
            )
            db.session.add(exc_pmt)

            # ── Dunning logs ──────────────────────────────────────────────
            rule1 = DunningRule.query.filter_by(sort_order=1).first()
            rule2 = DunningRule.query.filter_by(sort_order=2).first()
            dunning_targets = [
                (invoices[3], rule1, today - timedelta(days=14)),
                (invoices[3], rule2, today - timedelta(days=7)),
                (invoices[4], rule1, today - timedelta(days=33)),
                (invoices[4], rule2, today - timedelta(days=25)),
                (invoices[5], rule1, today - timedelta(days=63)),
                (invoices[5], rule2, today - timedelta(days=55)),
                (invoices[8], rule1, today - timedelta(days=98)),
                (invoices[8], rule2, today - timedelta(days=90)),
            ]
            for inv, rule, sent_at in dunning_targets:
                dl = DunningLog(
                    invoice_id=inv.id, rule_id=rule.id,
                    channel="email",
                    recipient=inv.customer.email,
                    subject=f"Invoice {inv.invoice_number} - Payment Reminder",
                    body_preview="Dear customer, your invoice is past due...",
                    sent_at=datetime.combine(sent_at, datetime.min.time()).replace(tzinfo=timezone.utc),
                    status="sent",
                )
                db.session.add(dl)

            # ── Dispute for Prestige inv[9] ────────────────────────────────
            dispute_inv = invoices[9]
            disp = Dispute(
                dispute_number=next_seq("DIS"),
                invoice_id=dispute_inv.id,
                customer_id=dispute_inv.customer_id,
                reason_code="pricing_error",
                description="The rate charged ($6,800) does not match the contracted rate of $5,500 per the MSA signed 2025-01-15. Requesting credit of $1,300.",
                disputed_amount=dispute_inv.balance_due,
                status="under_review",
                assigned_to_id=admin.id,
            )
            db.session.add(disp)

            # ── Credit events ──────────────────────────────────────────────
            credit_events = [
                CreditEvent(customer_id=customers[2].id, event_type="flag_raised",
                            old_value="good", new_value="watch",
                            reason="Multiple late payments in Q1",
                            created_by_id=admin.id,
                            created_at=datetime.now(timezone.utc) - timedelta(days=20)),
                CreditEvent(customer_id=customers[4].id, event_type="status_change",
                            old_value="watch", new_value="hold",
                            reason="90+ day balance unresolved",
                            created_by_id=admin.id,
                            created_at=datetime.now(timezone.utc) - timedelta(days=10)),
                CreditEvent(customer_id=customers[4].id, event_type="limit_change",
                            old_value="25000", new_value="15000",
                            reason="Reduced due to credit hold",
                            created_by_id=admin.id,
                            created_at=datetime.now(timezone.utc) - timedelta(days=10)),
            ]
            db.session.add_all(credit_events)

            db.session.commit()
            print("  Created payments, dunning logs, dispute, and credit events.")


def _make_payment(next_seq, admin, invoice, amount, method, pmt_date, full=False):
    pmt = Payment(
        payment_number=next_seq("PAY"),
        customer_id=invoice.customer_id,
        amount=amount,
        amount_applied=amount,
        amount_unapplied=Decimal("0"),
        payment_method=method,
        payment_date=pmt_date,
        status="applied",
        posted_by_id=admin.id,
    )
    db.session.add(pmt)
    db.session.flush()

    alloc = PaymentAllocation(
        payment_id=pmt.id,
        invoice_id=invoice.id,
        amount_allocated=amount,
        allocated_by_id=admin.id,
        is_manual=False,
    )
    db.session.add(alloc)

    invoice.amount_paid = amount
    invoice.balance_due = invoice.total_amount - amount
    if full or invoice.balance_due <= Decimal("0"):
        invoice.status = "paid"
        invoice.paid_at = datetime.now(timezone.utc)
    else:
        invoice.status = "partial"

    # GL entries
    entries = [
        GLEntry(payment_id=pmt.id, invoice_id=invoice.id,
                entry_type="cash_debit", account_code="1000",
                debit_amount=amount, credit_amount=Decimal("0"),
                description=f"Cash {pmt.payment_number}", erp_sync_status="synced"),
        GLEntry(payment_id=pmt.id, invoice_id=invoice.id,
                entry_type="ar_credit", account_code="1200",
                debit_amount=Decimal("0"), credit_amount=amount,
                description=f"AR cleared {pmt.payment_number}", erp_sync_status="synced"),
    ]
    db.session.add_all(entries)


if __name__ == "__main__":
    print("Seeding database...")
    seed()
    print("Done.")
