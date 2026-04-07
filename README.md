# AR Manager — Accounts Receivable Management System

A full-stack Accounts Receivable application built with Python FastAPI microservices and Angular 17.

## Architecture

```
api-gateway (8000)     ← Angular frontend communicates here
  ├── auth-service (8001)
  ├── invoice-service (8002)
  ├── payment-service (8003)
  ├── collections-service (8004)
  ├── credit-service (8005)
  ├── dispute-service (8006)
  ├── reporting-service (8007)
  └── customer-service (8008)
PostgreSQL (5432)
Angular Frontend (4200)
```

## Prerequisites

- Docker & Docker Compose
- Node.js 20+ (for local Angular dev)
- Python 3.11+ (for local service dev)
- PostgreSQL (provided via Docker)

## Quick Start (Docker)

```bash
cd "C:\My Programs\claude\accounts-receivable"
docker-compose up --build
```

Access the app at **http://localhost:4200**

API docs at **http://localhost:8000/docs**

## Local Development

### Backend Services

```bash
# Create venv and install deps for each service
cd services/auth-service
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

Repeat for each service on their respective ports.

### Frontend (Angular)

```bash
cd frontend/ar-app
npm install --legacy-peer-deps
npm start
# Opens at http://localhost:4200
```

## Demo Login Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@armanager.com | admin123 |
| AR Clerk | clerk@armanager.com | clerk123 |
| Finance Manager | finance@armanager.com | finance123 |
| Collections | collections@armanager.com | coll123 |
| Credit Manager | credit@armanager.com | credit123 |

## Features

- **Invoice Management** — Create, send, track invoices with PDF generation
- **Digital Payments** — Record and auto-apply payments to invoices
- **Collections & Dunning** — Automated dunning workflows and reminder emails
- **Cash Application** — Auto-match payments to open invoices
- **Credit Management** — Credit profiles, risk scoring, limit management
- **Dispute Management** — Track and resolve invoice disputes
- **Reporting & Analytics** — AR Aging, DSO, cash flow trends, KPI dashboard
- **Customer Management** — Full customer master data management

## Database

The PostgreSQL schema is in `database/init.sql`. It includes:
- Seed data (demo users, customers, sample invoices)
- All tables with proper indexes and foreign keys
- Audit trail tables

## Environment Variables

Copy `.env.example` to `.env` and configure:
- Database credentials
- JWT secret key
- SMTP settings (for email notifications)
- Stripe API keys (for payment gateway integration)
