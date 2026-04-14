# Architecture Summary
## Lincoln Financial Group — Accounts Receivable Application

**Document Date:** 2026-04-14  
**Repository:** https://github.com/pritchard4code/accounts-receivable  
**Author:** Pritchard Mapeka

---

## 1. Overview

The Lincoln Financial Group Accounts Receivable (AR) application is a full-stack web application built on the Python/Flask ecosystem. It manages the complete AR lifecycle: invoice creation and delivery, cash application and payment processing, collections and dunning automation, credit risk management, dispute resolution, and financial reporting. The system produces SOX-compliant audit trails and GL journal entries, and integrates with Stripe for online customer payments.

---

## 2. Application Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          Browser Client                          │
│              Bootstrap 5.3.2  ·  Chart.js 4.4.0                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │  HTTP / HTTPS
┌──────────────────────────▼──────────────────────────────────────┐
│                     Flask Application                            │
│                    Python 3.12.10  ·  Flask 3.1.3               │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ invoices │ │ payments │ │collections│ │ cash_app │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │  credit  │ │ disputes │ │  reports │ │   auth   │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│                                                                  │
│  Flask-Login 0.6.3 (RBAC)  ·  Flask-WTF 1.2.2 (CSRF)          │
│  Flask-Mail 0.10.0          ·  APScheduler 3.11.2               │
└──────────────┬──────────────────────────┬───────────────────────┘
               │  SQLAlchemy ORM           │  Stripe SDK
┌──────────────▼──────────────┐ ┌─────────▼───────────────────────┐
│   PostgreSQL 17.9 (port 5433)│ │    Stripe API  v15.0.1          │
│   Database: accounts_        │ │    Payment processing           │
│   receivable                 │ │    Customer portal              │
└─────────────────────────────┘ └─────────────────────────────────┘
```

---

## 3. Language & Runtime

| Component | Technology | Version |
|---|---|---|
| Primary language | Python | 3.12.10 |
| Runtime environment | CPython | 3.12.10 |
| Operating system (dev) | Windows 11 Pro | 10.0.26200 |
| Package manager | pip | (bundled with Python 3.12) |

---

## 4. Web Framework & Extensions

| Package | Purpose | Version |
|---|---|---|
| Flask | Core web framework, routing, blueprints | 3.1.3 |
| Flask-SQLAlchemy | SQLAlchemy ORM integration with Flask | 3.1.1 |
| Flask-Login | Session management, RBAC authentication | 0.6.3 |
| Flask-Mail | SMTP email for invoices, receipts, dunning | 0.10.0 |
| Flask-WTF | CSRF protection, form validation | 1.2.2 |
| WTForms | Form field definitions and validation | 3.2.1 |

### Blueprint Modules

| Blueprint | Prefix | Responsibility |
|---|---|---|
| `auth` | `/` | Login, logout, profile, password management |
| `invoices` | `/invoices` | Invoice CRUD, GL posting, PDF generation, send/void |
| `payments` | `/payments` | Payment recording, Stripe portal, webhooks |
| `collections` | `/collections` | Dunning queue, rule management, manual trigger |
| `cash_app` | `/cash` | Auto-match, manual allocation, exception queue, GL reconciliation |
| `credit` | `/credit` | Risk scoring, credit limit management, hold/suspend |
| `disputes` | `/disputes` | Open, upload evidence, resolve disputes |
| `reports` | `/reports` | Dashboard KPIs, aging, payment history, cash forecast, PDF/CSV export |

---

## 5. Database

| Component | Technology | Version |
|---|---|---|
| Database engine | PostgreSQL | 17.9 |
| Database port | 5433 | — |
| Database name | `accounts_receivable` | — |
| ORM | SQLAlchemy | 2.0.49 |
| DB driver | psycopg2-binary | 2.9.11 |
| Migration tool | Alembic | 1.18.4 |

### Core Data Models

| Model | Description |
|---|---|
| `User` | Staff accounts with role-based access (admin, ar_clerk, collections_specialist, finance_manager, credit_manager) |
| `Customer` | Customer master with credit limit, risk score, payment terms |
| `Invoice` | Invoice header with lifecycle status (draft → sent → partial/paid/overdue/disputed/void) |
| `InvoiceLineItem` | Line-level description, quantity, unit price, tax rate |
| `Payment` | Payment header with auto-match state |
| `PaymentAllocation` | Many-to-many allocation of payments to invoices |
| `DunningRule` | Configurable rules: days past due, risk profile, action, late fee flag |
| `DunningLog` | Audit record of every dunning communication sent |
| `CreditEvent` | Credit history events for risk score recalculation |
| `Dispute` | Dispute record linked to invoice; pauses dunning cycle |
| `DisputeDocument` | Uploaded evidence files |
| `GLEntry` | Double-entry GL journal records (AR debit / revenue credit / tax credit) |
| `AuditLog` | SOX-compliant immutable audit trail for all state changes |

---

## 6. Background Processing

| Package | Purpose | Version |
|---|---|---|
| APScheduler | Nightly dunning cycle scheduler, job persistence | 3.11.2 |

The dunning engine (`run_dunning_cycle`) runs as a scheduled background job. It queries overdue invoices, matches applicable dunning rules by days-past-due and customer risk profile, dispatches emails, and optionally applies late fees.

---

## 7. Payment Gateway

| Component | Technology | Version |
|---|---|---|
| Payment SDK | Stripe Python | 15.0.1 |
| Integration type | Stripe Customer Portal (hosted), Stripe Webhooks | — |
| Webhook events handled | `checkout.session.completed`, `payment_intent.succeeded` | — |

---

## 8. PDF Generation

| Package | Purpose | Version |
|---|---|---|
| ReportLab | PDF document generation for invoices and reports | 4.4.10 |
| svglib | SVG-to-ReportLab drawing conversion (logo rendering) | 1.6.0 |
| Pillow | Image processing support for ReportLab | 12.2.0 |

PDF exports are available for:
- Individual invoices (`/invoices/<id>/pdf`)
- AR Aging Report (`/reports/export/aging.pdf`)
- Payment History Report (`/reports/export/payment-history.pdf`)
- Cash Flow Forecast (`/reports/export/cash-forecast.pdf`)

All PDFs embed the Lincoln Financial Group SVG logo in the top-left position.

---

## 9. Front-End Libraries (CDN-delivered)

| Library | Purpose | Version |
|---|---|---|
| Bootstrap | Responsive UI framework, layout, components | 5.3.2 |
| Bootstrap Icons | Icon font set used throughout the UI | 1.11.3 |
| Chart.js | Dashboard KPI charts (aging donut, collection trend line) | 4.4.0 |

---

## 10. Email / Messaging

| Component | Configuration | Notes |
|---|---|---|
| SMTP provider | Gmail (configurable) | `smtp.gmail.com:587` with STARTTLS |
| Flask-Mail | `0.10.0` | Sends invoice PDFs, payment receipts, dunning notices |
| Dunning templates | 4 built-in | `dunning_reminder`, `dunning_first_notice`, `dunning_second_notice`, `dunning_final_demand` |

---

## 11. Security

| Mechanism | Implementation |
|---|---|
| Authentication | Flask-Login session-based with bcrypt password hashing |
| Authorisation | Role-based `@role_required()` decorator on all sensitive routes |
| CSRF protection | Flask-WTF on all POST forms |
| Secure cookies (prod) | `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SAMESITE=Lax` |
| Audit trail | `AuditLog` model records every state change with user, IP, timestamp, before/after data |
| Secret management | All credentials via `.env` (excluded from version control via `.gitignore`) |

---

## 12. Configuration & Environment

| Package | Purpose | Version |
|---|---|---|
| python-dotenv | Loads `.env` file into environment at startup | 1.2.2 |
| email-validator | Validates email addresses on form submission | 2.3.0 |

### Key Business Rule Configuration (`.env` / `config.py`)

| Variable | Default | Description |
|---|---|---|
| `LATE_FEE_RATE` | `0.015` | Monthly late fee rate (1.5%) |
| `PAYMENT_TOLERANCE_PCT` | `0.01` | Auto-match tolerance (1% of invoice amount) |
| `DEFAULT_CREDIT_LIMIT` | `10000.00` | Default credit limit for new customers |
| `DUNNING_GRACE_DAYS` | `3` | Grace days before dunning cycle triggers |

---

## 13. Version Control & Repository

| Component | Detail |
|---|---|
| Version control system | Git |
| Remote host | GitHub |
| Repository URL | https://github.com/pritchard4code/accounts-receivable |
| Default branch | `main` |
| Sensitive files excluded | `.env`, `uploads/`, `__pycache__/`, `*.db` |

---

## 14. Directory Structure

```
accounts_receivable/
├── app.py                  # Flask application factory, blueprint registration
├── config.py               # Dev / Production configuration classes
├── models.py               # All SQLAlchemy models
├── seed.py                 # Database seed script (demo data)
├── requirements.txt        # Python package dependencies
├── start.bat               # Windows launcher script
├── .env                    # Environment variables (git-ignored)
├── .gitignore
├── ARCHITECTURE.md         # This document
│
├── ar/                     # Application blueprints
│   ├── auth.py
│   ├── invoices.py
│   ├── payments.py
│   ├── collections.py
│   ├── cash_app.py
│   ├── credit.py
│   ├── disputes.py
│   ├── reports.py
│   └── utils.py            # Shared: RBAC, sequences, audit log, email, ERP stub
│
├── static/
│   ├── css/ar.css          # Lincoln Financial Group theme overrides
│   ├── js/ar.js
│   └── img/lfg-logo.svg    # Lincoln Financial Group brand logo
│
├── templates/
│   ├── base.html           # Shared layout with LFG navbar
│   ├── auth/
│   ├── invoices/
│   ├── payments/
│   ├── collections/
│   ├── cash/
│   ├── credit/
│   ├── disputes/
│   ├── reports/
│   ├── emails/
│   └── errors/
│
└── uploads/
    └── disputes/           # Dispute document file uploads (git-ignored)
```

---

## 15. Application Roles

| Role | Access |
|---|---|
| `admin` | Full access to all modules and configuration |
| `ar_clerk` | Create/send invoices, record payments |
| `collections_specialist` | Collections queue, dunning management |
| `finance_manager` | Void invoices, GL reconciliation, reports |
| `credit_manager` | Credit limit management, risk score overrides |

---

*This document reflects the application as of 2026-04-14.*
