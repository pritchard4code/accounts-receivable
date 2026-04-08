# Database Setup

## Prerequisites
- PostgreSQL 16

## Recreate from scratch

### Step 1 — Create user and database (run as superuser)
```bash
psql -U postgres -f setup.sql
```

### Step 2 — Load schema and data
```bash
psql -U aruser -d accounts_receivable -f schema_and_data.sql
```

### Windows example (full path to psql)
```cmd
"C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -f setup.sql
"C:\Program Files\PostgreSQL\16\bin\psql.exe" -U aruser -d accounts_receivable -f schema_and_data.sql
```

## Connection details
| Setting  | Value               |
|----------|---------------------|
| Host     | localhost           |
| Port     | 5432                |
| Database | accounts_receivable |
| User     | aruser              |
| Password | arpassword          |

## Tables
| Table                 | Description                          |
|-----------------------|--------------------------------------|
| users                 | Application users and roles          |
| customers             | Customer accounts                    |
| invoices              | Invoice headers                      |
| invoice_line_items    | Invoice line items                   |
| invoice_templates     | Invoice templates                    |
| payments              | Payment records                      |
| payment_allocations   | Payment-to-invoice allocations       |
| disputes              | Dispute cases                        |
| dispute_documents     | Dispute supporting documents         |
| collections_workflows | Collections workflow definitions     |
| collection_actions    | Collection actions taken             |
| credit_profiles       | Customer credit assessments          |
| dunning_rules         | Automated dunning escalation rules   |
| aging_snapshots       | Historical AR aging snapshots        |
| gl_postings           | General ledger posting entries       |
| notifications         | System notifications                 |
| audit_logs            | Audit trail                          |
| recurring_invoices    | Recurring invoice schedules          |
| ref_status            | Reference data — invoice statuses    |
