-- Accounts Receivable Database Schema
-- PostgreSQL 15+

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Enums
CREATE TYPE user_role AS ENUM ('admin', 'ar_clerk', 'collections_specialist', 'finance_manager', 'credit_manager', 'customer');
CREATE TYPE invoice_status AS ENUM ('draft', 'sent', 'viewed', 'partial', 'paid', 'overdue', 'void', 'disputed');
CREATE TYPE payment_method AS ENUM ('credit_card', 'ach', 'wire', 'check', 'cash', 'other');
CREATE TYPE payment_status AS ENUM ('pending', 'applied', 'partially_applied', 'refunded', 'voided');
CREATE TYPE collection_action_type AS ENUM ('email', 'sms', 'phone', 'letter', 'escalate', 'hold', 'write_off');
CREATE TYPE collection_status AS ENUM ('scheduled', 'executed', 'failed', 'cancelled');
CREATE TYPE risk_level AS ENUM ('low', 'medium', 'high', 'critical');
CREATE TYPE dispute_status AS ENUM ('open', 'under_review', 'resolved', 'rejected', 'withdrawn');
CREATE TYPE dispute_reason AS ENUM ('billing_error', 'goods_not_received', 'service_not_rendered', 'quality_issue', 'duplicate_charge', 'price_discrepancy', 'other');
CREATE TYPE credit_status AS ENUM ('good', 'fair', 'poor', 'suspended', 'on_hold');
CREATE TYPE gl_posting_status AS ENUM ('pending', 'posted', 'reversed');

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'ar_clerk',
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(30),
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);

-- Customers table
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_number VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(30),
    address VARCHAR(500),
    city VARCHAR(100),
    state VARCHAR(100),
    zip VARCHAR(20),
    country VARCHAR(100) DEFAULT 'US',
    currency VARCHAR(10) DEFAULT 'USD',
    language VARCHAR(10) DEFAULT 'en',
    credit_limit NUMERIC(15,2) DEFAULT 0.00,
    credit_status credit_status DEFAULT 'good',
    payment_terms INTEGER DEFAULT 30,
    tax_id VARCHAR(50),
    website VARCHAR(255),
    notes TEXT,
    sales_rep VARCHAR(100),
    industry VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_customers_number ON customers(customer_number);
CREATE INDEX idx_customers_name ON customers USING gin(name gin_trgm_ops);
CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_customers_credit_status ON customers(credit_status);

-- Invoice templates
CREATE TABLE invoice_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    content TEXT,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Invoices table
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    status invoice_status DEFAULT 'draft',
    invoice_date DATE NOT NULL DEFAULT CURRENT_DATE,
    due_date DATE NOT NULL,
    subtotal NUMERIC(15,2) DEFAULT 0.00,
    tax_amount NUMERIC(15,2) DEFAULT 0.00,
    discount_amount NUMERIC(15,2) DEFAULT 0.00,
    total_amount NUMERIC(15,2) DEFAULT 0.00,
    paid_amount NUMERIC(15,2) DEFAULT 0.00,
    balance_due NUMERIC(15,2) DEFAULT 0.00,
    currency VARCHAR(10) DEFAULT 'USD',
    payment_terms INTEGER DEFAULT 30,
    po_number VARCHAR(100),
    notes TEXT,
    internal_notes TEXT,
    template_id UUID REFERENCES invoice_templates(id),
    sent_at TIMESTAMPTZ,
    viewed_at TIMESTAMPTZ,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_invoices_number ON invoices(invoice_number);
CREATE INDEX idx_invoices_customer ON invoices(customer_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_due_date ON invoices(due_date);
CREATE INDEX idx_invoices_invoice_date ON invoices(invoice_date);

-- Invoice line items
CREATE TABLE invoice_line_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    line_number INTEGER NOT NULL DEFAULT 1,
    description TEXT NOT NULL,
    quantity NUMERIC(10,3) DEFAULT 1.000,
    unit_price NUMERIC(15,2) DEFAULT 0.00,
    total_price NUMERIC(15,2) DEFAULT 0.00,
    tax_rate NUMERIC(5,4) DEFAULT 0.0000,
    tax_amount NUMERIC(15,2) DEFAULT 0.00,
    discount_rate NUMERIC(5,4) DEFAULT 0.0000,
    discount_amount NUMERIC(15,2) DEFAULT 0.00,
    product_code VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_line_items_invoice ON invoice_line_items(invoice_id);

-- Recurring invoices
CREATE TABLE recurring_invoices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES customers(id),
    template_invoice_id UUID REFERENCES invoices(id),
    frequency VARCHAR(20) NOT NULL DEFAULT 'monthly',
    next_invoice_date DATE,
    end_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Payments table
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    payment_number VARCHAR(50) UNIQUE NOT NULL,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    payment_date DATE NOT NULL DEFAULT CURRENT_DATE,
    amount NUMERIC(15,2) NOT NULL,
    unapplied_amount NUMERIC(15,2) DEFAULT 0.00,
    payment_method payment_method NOT NULL,
    status payment_status DEFAULT 'pending',
    reference VARCHAR(255),
    gateway_transaction_id VARCHAR(255),
    gateway_response JSONB,
    notes TEXT,
    recorded_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_payments_number ON payments(payment_number);
CREATE INDEX idx_payments_customer ON payments(customer_id);
CREATE INDEX idx_payments_date ON payments(payment_date);
CREATE INDEX idx_payments_status ON payments(status);

-- Payment allocations
CREATE TABLE payment_allocations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    payment_id UUID NOT NULL REFERENCES payments(id) ON DELETE CASCADE,
    invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE RESTRICT,
    allocated_amount NUMERIC(15,2) NOT NULL,
    allocated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_allocations_payment ON payment_allocations(payment_id);
CREATE INDEX idx_allocations_invoice ON payment_allocations(invoice_id);

-- Collections workflows
CREATE TABLE collections_workflows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    stages JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Collection actions
CREATE TABLE collection_actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES customers(id),
    invoice_id UUID REFERENCES invoices(id),
    workflow_id UUID REFERENCES collections_workflows(id),
    stage VARCHAR(100),
    action_type collection_action_type NOT NULL,
    status collection_status DEFAULT 'scheduled',
    scheduled_date TIMESTAMPTZ,
    executed_date TIMESTAMPTZ,
    notes TEXT,
    result TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_collection_actions_customer ON collection_actions(customer_id);
CREATE INDEX idx_collection_actions_invoice ON collection_actions(invoice_id);
CREATE INDEX idx_collection_actions_status ON collection_actions(status);
CREATE INDEX idx_collection_actions_scheduled ON collection_actions(scheduled_date);

-- Dunning rules
CREATE TABLE dunning_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    days_overdue_min INTEGER NOT NULL DEFAULT 0,
    days_overdue_max INTEGER,
    action_type collection_action_type NOT NULL,
    template TEXT,
    subject VARCHAR(500),
    priority INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_dunning_rules_days ON dunning_rules(days_overdue_min, days_overdue_max);

-- Credit profiles
CREATE TABLE credit_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID UNIQUE NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    credit_limit NUMERIC(15,2) DEFAULT 0.00,
    current_balance NUMERIC(15,2) DEFAULT 0.00,
    available_credit NUMERIC(15,2) DEFAULT 0.00,
    risk_score NUMERIC(5,2) DEFAULT 0.00,
    risk_level risk_level DEFAULT 'low',
    payment_score NUMERIC(5,2) DEFAULT 100.00,
    avg_days_to_pay NUMERIC(5,1) DEFAULT 0.0,
    on_time_payment_rate NUMERIC(5,2) DEFAULT 100.00,
    late_payment_count INTEGER DEFAULT 0,
    nsf_count INTEGER DEFAULT 0,
    last_review_date DATE,
    next_review_date DATE,
    notes TEXT,
    reviewed_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_credit_profiles_customer ON credit_profiles(customer_id);
CREATE INDEX idx_credit_profiles_risk ON credit_profiles(risk_level);

-- Disputes table
CREATE TABLE disputes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dispute_number VARCHAR(50) UNIQUE NOT NULL,
    customer_id UUID NOT NULL REFERENCES customers(id),
    invoice_id UUID REFERENCES invoices(id),
    status dispute_status DEFAULT 'open',
    reason dispute_reason NOT NULL,
    description TEXT,
    amount_disputed NUMERIC(15,2) DEFAULT 0.00,
    resolution TEXT,
    resolved_amount NUMERIC(15,2),
    assigned_to UUID REFERENCES users(id),
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE INDEX idx_disputes_number ON disputes(dispute_number);
CREATE INDEX idx_disputes_customer ON disputes(customer_id);
CREATE INDEX idx_disputes_invoice ON disputes(invoice_id);
CREATE INDEX idx_disputes_status ON disputes(status);

-- Dispute documents
CREATE TABLE dispute_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dispute_id UUID NOT NULL REFERENCES disputes(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500),
    file_size INTEGER,
    content_type VARCHAR(100),
    uploaded_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_dispute_docs_dispute ON dispute_documents(dispute_id);

-- Audit logs
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id UUID,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at);

-- Notifications
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    customer_id UUID REFERENCES customers(id),
    type VARCHAR(100) NOT NULL,
    title VARCHAR(500) NOT NULL,
    message TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_read ON notifications(user_id, is_read);

-- GL postings
CREATE TABLE gl_postings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    invoice_id UUID REFERENCES invoices(id),
    payment_id UUID REFERENCES payments(id),
    posting_date DATE NOT NULL DEFAULT CURRENT_DATE,
    account_code VARCHAR(50) NOT NULL,
    debit_amount NUMERIC(15,2) DEFAULT 0.00,
    credit_amount NUMERIC(15,2) DEFAULT 0.00,
    description TEXT,
    reference VARCHAR(255),
    status gl_posting_status DEFAULT 'pending',
    posted_by UUID REFERENCES users(id),
    posted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_gl_postings_invoice ON gl_postings(invoice_id);
CREATE INDEX idx_gl_postings_payment ON gl_postings(payment_id);
CREATE INDEX idx_gl_postings_date ON gl_postings(posting_date);

-- Aging snapshots
CREATE TABLE aging_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES customers(id),
    snapshot_date DATE NOT NULL,
    current_amount NUMERIC(15,2) DEFAULT 0.00,
    days_1_30 NUMERIC(15,2) DEFAULT 0.00,
    days_31_60 NUMERIC(15,2) DEFAULT 0.00,
    days_61_90 NUMERIC(15,2) DEFAULT 0.00,
    days_over_90 NUMERIC(15,2) DEFAULT 0.00,
    total_outstanding NUMERIC(15,2) DEFAULT 0.00,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_aging_snapshots_customer ON aging_snapshots(customer_id);
CREATE INDEX idx_aging_snapshots_date ON aging_snapshots(snapshot_date);

-- Updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_customers_updated_at BEFORE UPDATE ON customers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_invoices_updated_at BEFORE UPDATE ON invoices FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_payments_updated_at BEFORE UPDATE ON payments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_credit_profiles_updated_at BEFORE UPDATE ON credit_profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_disputes_updated_at BEFORE UPDATE ON disputes FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ================================================
-- SEED DATA
-- ================================================

-- Default admin user (password: Admin@123)
INSERT INTO users (id, username, email, hashed_password, role, first_name, last_name, is_active)
VALUES
    ('00000000-0000-0000-0000-000000000001', 'admin', 'admin@armanager.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/lewdBPN7QwDFVJDdq', 'admin', 'System', 'Administrator', TRUE),
    ('00000000-0000-0000-0000-000000000002', 'ar_clerk1', 'clerk@armanager.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/lewdBPN7QwDFVJDdq', 'ar_clerk', 'Jane', 'Smith', TRUE),
    ('00000000-0000-0000-0000-000000000003', 'collections1', 'collections@armanager.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/lewdBPN7QwDFVJDdq', 'collections_specialist', 'Bob', 'Johnson', TRUE),
    ('00000000-0000-0000-0000-000000000004', 'finance_mgr', 'finance@armanager.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/lewdBPN7QwDFVJDdq', 'finance_manager', 'Alice', 'Williams', TRUE),
    ('00000000-0000-0000-0000-000000000005', 'credit_mgr', 'credit@armanager.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/lewdBPN7QwDFVJDdq', 'credit_manager', 'Tom', 'Brown', TRUE);

-- Sample customers
INSERT INTO customers (id, customer_number, name, email, phone, address, city, state, zip, country, currency, credit_limit, credit_status, payment_terms, industry)
VALUES
    ('10000000-0000-0000-0000-000000000001', 'CUST-001', 'Acme Corporation', 'ap@acme.com', '555-0101', '123 Main St', 'New York', 'NY', '10001', 'US', 'USD', 50000.00, 'good', 30, 'Manufacturing'),
    ('10000000-0000-0000-0000-000000000002', 'CUST-002', 'Global Tech Solutions', 'billing@globaltech.com', '555-0102', '456 Tech Ave', 'San Francisco', 'CA', '94105', 'US', 'USD', 100000.00, 'good', 45, 'Technology'),
    ('10000000-0000-0000-0000-000000000003', 'CUST-003', 'Metro Retail Group', 'finance@metroretail.com', '555-0103', '789 Commerce Blvd', 'Chicago', 'IL', '60601', 'US', 'USD', 75000.00, 'fair', 30, 'Retail'),
    ('10000000-0000-0000-0000-000000000004', 'CUST-004', 'Sunrise Healthcare', 'accounts@sunrisehealth.com', '555-0104', '321 Medical Way', 'Houston', 'TX', '77001', 'US', 'USD', 200000.00, 'good', 60, 'Healthcare'),
    ('10000000-0000-0000-0000-000000000005', 'CUST-005', 'Pacific Logistics', 'payables@paclogistics.com', '555-0105', '654 Harbor Dr', 'Seattle', 'WA', '98101', 'US', 'USD', 30000.00, 'poor', 15, 'Logistics'),
    ('10000000-0000-0000-0000-000000000006', 'CUST-006', 'Summit Financial Group', 'billing@summitfin.com', '555-0106', '987 Wall St', 'New York', 'NY', '10005', 'US', 'USD', 150000.00, 'good', 30, 'Finance'),
    ('10000000-0000-0000-0000-000000000007', 'CUST-007', 'Greenfield Builders', 'accounts@greenfieldbuild.com', '555-0107', '147 Construction Rd', 'Phoenix', 'AZ', '85001', 'US', 'USD', 80000.00, 'fair', 45, 'Construction'),
    ('10000000-0000-0000-0000-000000000008', 'CUST-008', 'DataStream Analytics', 'finance@datastream.io', '555-0108', '258 Data Center Dr', 'Austin', 'TX', '78701', 'US', 'USD', 60000.00, 'good', 30, 'Technology');

-- Invoice templates
INSERT INTO invoice_templates (id, name, content, is_default)
VALUES
    ('20000000-0000-0000-0000-000000000001', 'Standard Invoice', '<html><body><h1>INVOICE</h1></body></html>', TRUE),
    ('20000000-0000-0000-0000-000000000002', 'Service Invoice', '<html><body><h1>SERVICE INVOICE</h1></body></html>', FALSE);

-- Sample invoices
INSERT INTO invoices (id, invoice_number, customer_id, status, invoice_date, due_date, subtotal, tax_amount, total_amount, paid_amount, balance_due, currency, payment_terms, notes, created_by)
VALUES
    ('30000000-0000-0000-0000-000000000001', 'INV-2024-001', '10000000-0000-0000-0000-000000000001', 'overdue', '2024-01-15', '2024-02-14', 5000.00, 400.00, 5400.00, 0.00, 5400.00, 'USD', 30, 'Software licenses Q1', '00000000-0000-0000-0000-000000000002'),
    ('30000000-0000-0000-0000-000000000002', 'INV-2024-002', '10000000-0000-0000-0000-000000000002', 'paid', '2024-01-20', '2024-03-05', 12000.00, 960.00, 12960.00, 12960.00, 0.00, 'USD', 45, 'Consulting services January', '00000000-0000-0000-0000-000000000002'),
    ('30000000-0000-0000-0000-000000000003', 'INV-2024-003', '10000000-0000-0000-0000-000000000003', 'partial', '2024-02-01', '2024-03-02', 8500.00, 680.00, 9180.00, 4000.00, 5180.00, 'USD', 30, 'Product supply February', '00000000-0000-0000-0000-000000000002'),
    ('30000000-0000-0000-0000-000000000004', 'INV-2024-004', '10000000-0000-0000-0000-000000000004', 'sent', '2024-02-15', '2024-04-15', 25000.00, 2000.00, 27000.00, 0.00, 27000.00, 'USD', 60, 'Medical equipment maintenance', '00000000-0000-0000-0000-000000000002'),
    ('30000000-0000-0000-0000-000000000005', 'INV-2024-005', '10000000-0000-0000-0000-000000000005', 'overdue', '2024-01-01', '2024-01-16', 3200.00, 256.00, 3456.00, 0.00, 3456.00, 'USD', 15, 'Freight services January', '00000000-0000-0000-0000-000000000002'),
    ('30000000-0000-0000-0000-000000000006', 'INV-2024-006', '10000000-0000-0000-0000-000000000006', 'sent', '2024-03-01', '2024-03-31', 18000.00, 1440.00, 19440.00, 0.00, 19440.00, 'USD', 30, 'Financial advisory Q1', '00000000-0000-0000-0000-000000000002'),
    ('30000000-0000-0000-0000-000000000007', 'INV-2024-007', '10000000-0000-0000-0000-000000000001', 'draft', '2024-03-10', '2024-04-09', 7500.00, 600.00, 8100.00, 0.00, 8100.00, 'USD', 30, 'Software support Q2', '00000000-0000-0000-0000-000000000002'),
    ('30000000-0000-0000-0000-000000000008', 'INV-2024-008', '10000000-0000-0000-0000-000000000007', 'overdue', '2024-01-25', '2024-03-10', 15000.00, 1200.00, 16200.00, 5000.00, 11200.00, 'USD', 45, 'Construction materials', '00000000-0000-0000-0000-000000000002');

-- Sample invoice line items
INSERT INTO invoice_line_items (invoice_id, line_number, description, quantity, unit_price, total_price, tax_rate, tax_amount)
VALUES
    ('30000000-0000-0000-0000-000000000001', 1, 'Enterprise Software License - Annual', 5.000, 800.00, 4000.00, 0.08, 320.00),
    ('30000000-0000-0000-0000-000000000001', 2, 'Implementation Support', 10.000, 100.00, 1000.00, 0.08, 80.00),
    ('30000000-0000-0000-0000-000000000002', 1, 'Senior Consultant - 80 hours', 80.000, 150.00, 12000.00, 0.08, 960.00),
    ('30000000-0000-0000-0000-000000000003', 1, 'Product SKU-A100', 100.000, 50.00, 5000.00, 0.08, 400.00),
    ('30000000-0000-0000-0000-000000000003', 2, 'Product SKU-B200', 50.000, 70.00, 3500.00, 0.08, 280.00),
    ('30000000-0000-0000-0000-000000000004', 1, 'MRI Equipment Maintenance Contract', 1.000, 25000.00, 25000.00, 0.08, 2000.00),
    ('30000000-0000-0000-0000-000000000005', 1, 'Cross-country Freight - 4 shipments', 4.000, 800.00, 3200.00, 0.08, 256.00),
    ('30000000-0000-0000-0000-000000000006', 1, 'Investment Portfolio Advisory Q1', 1.000, 18000.00, 18000.00, 0.08, 1440.00),
    ('30000000-0000-0000-0000-000000000008', 1, 'Steel Beams - 50 units', 50.000, 200.00, 10000.00, 0.08, 800.00),
    ('30000000-0000-0000-0000-000000000008', 2, 'Concrete Mix - 10 tons', 10.000, 500.00, 5000.00, 0.08, 400.00);

-- Sample payments
INSERT INTO payments (id, payment_number, customer_id, payment_date, amount, unapplied_amount, payment_method, status, reference, notes, recorded_by)
VALUES
    ('40000000-0000-0000-0000-000000000001', 'PMT-2024-001', '10000000-0000-0000-0000-000000000002', '2024-02-25', 12960.00, 0.00, 'ach', 'applied', 'ACH-REF-12345', 'Full payment for INV-2024-002', '00000000-0000-0000-0000-000000000002'),
    ('40000000-0000-0000-0000-000000000002', 'PMT-2024-002', '10000000-0000-0000-0000-000000000003', '2024-02-20', 4000.00, 0.00, 'check', 'applied', 'CHK-67890', 'Partial payment for INV-2024-003', '00000000-0000-0000-0000-000000000002'),
    ('40000000-0000-0000-0000-000000000003', 'PMT-2024-003', '10000000-0000-0000-0000-000000000007', '2024-02-28', 5000.00, 0.00, 'wire', 'applied', 'WIRE-11111', 'Partial payment INV-2024-008', '00000000-0000-0000-0000-000000000002');

-- Sample payment allocations
INSERT INTO payment_allocations (payment_id, invoice_id, allocated_amount)
VALUES
    ('40000000-0000-0000-0000-000000000001', '30000000-0000-0000-0000-000000000002', 12960.00),
    ('40000000-0000-0000-0000-000000000002', '30000000-0000-0000-0000-000000000003', 4000.00),
    ('40000000-0000-0000-0000-000000000003', '30000000-0000-0000-0000-000000000008', 5000.00);

-- Credit profiles
INSERT INTO credit_profiles (customer_id, credit_limit, current_balance, available_credit, risk_score, risk_level, payment_score, avg_days_to_pay, on_time_payment_rate, last_review_date)
VALUES
    ('10000000-0000-0000-0000-000000000001', 50000.00, 13500.00, 36500.00, 25.00, 'low', 85.00, 28.5, 90.00, '2024-01-01'),
    ('10000000-0000-0000-0000-000000000002', 100000.00, 0.00, 100000.00, 10.00, 'low', 95.00, 20.0, 98.00, '2024-01-01'),
    ('10000000-0000-0000-0000-000000000003', 75000.00, 5180.00, 69820.00, 45.00, 'medium', 70.00, 42.0, 75.00, '2024-01-01'),
    ('10000000-0000-0000-0000-000000000004', 200000.00, 27000.00, 173000.00, 15.00, 'low', 92.00, 35.0, 95.00, '2024-01-01'),
    ('10000000-0000-0000-0000-000000000005', 30000.00, 3456.00, 26544.00, 75.00, 'high', 45.00, 65.0, 55.00, '2024-01-01'),
    ('10000000-0000-0000-0000-000000000006', 150000.00, 19440.00, 130560.00, 20.00, 'low', 90.00, 25.0, 97.00, '2024-01-01'),
    ('10000000-0000-0000-0000-000000000007', 80000.00, 11200.00, 68800.00, 50.00, 'medium', 65.00, 48.0, 70.00, '2024-01-01'),
    ('10000000-0000-0000-0000-000000000008', 60000.00, 0.00, 60000.00, 12.00, 'low', 93.00, 22.0, 96.00, '2024-01-01');

-- Sample dunning rules
INSERT INTO dunning_rules (name, days_overdue_min, days_overdue_max, action_type, template, subject, priority)
VALUES
    ('First Reminder', 1, 7, 'email', 'Dear {{customer_name}}, Your invoice {{invoice_number}} for {{amount}} was due on {{due_date}}. Please arrange payment at your earliest convenience.', 'Payment Reminder - Invoice {{invoice_number}}', 1),
    ('Second Notice', 8, 14, 'email', 'Dear {{customer_name}}, This is a second notice that invoice {{invoice_number}} for {{amount}} is now {{days_overdue}} days past due. Please contact us immediately.', 'SECOND NOTICE: Overdue Invoice {{invoice_number}}', 2),
    ('Final Warning', 15, 30, 'email', 'Dear {{customer_name}}, FINAL NOTICE: Invoice {{invoice_number}} for {{amount}} is {{days_overdue}} days past due. Failure to pay may result in service suspension.', 'FINAL NOTICE: Immediate Payment Required', 3),
    ('Phone Follow-up', 15, 30, 'phone', 'Call customer to discuss outstanding balance', 'Phone Collection Call', 2),
    ('Collections Escalation', 31, NULL, 'escalate', 'Escalate account to collections team for further action', 'Account Escalated to Collections', 1);

-- Sample collections workflow
INSERT INTO collections_workflows (id, name, description, is_active, stages)
VALUES
    ('50000000-0000-0000-0000-000000000001', 'Standard AR Collections', 'Default collections workflow for AR', TRUE,
    '[{"stage": 1, "name": "Initial Reminder", "days_overdue": 1, "action": "email"}, {"stage": 2, "name": "Second Notice", "days_overdue": 8, "action": "email"}, {"stage": 3, "name": "Final Warning", "days_overdue": 15, "action": "email"}, {"stage": 4, "name": "Phone Call", "days_overdue": 20, "action": "phone"}, {"stage": 5, "name": "Escalate", "days_overdue": 31, "action": "escalate"}]'::jsonb);

-- Sample dispute
INSERT INTO disputes (id, dispute_number, customer_id, invoice_id, status, reason, description, amount_disputed, assigned_to, created_by)
VALUES
    ('60000000-0000-0000-0000-000000000001', 'DIS-2024-001', '10000000-0000-0000-0000-000000000003', '30000000-0000-0000-0000-000000000003', 'open', 'price_discrepancy', 'Customer claims they were quoted a different price for SKU-B200', 1400.00, '00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000002');

-- Aging snapshots (current date approximation)
INSERT INTO aging_snapshots (customer_id, snapshot_date, current_amount, days_1_30, days_31_60, days_61_90, days_over_90, total_outstanding)
VALUES
    ('10000000-0000-0000-0000-000000000001', CURRENT_DATE, 8100.00, 0.00, 5400.00, 0.00, 0.00, 13500.00),
    ('10000000-0000-0000-0000-000000000003', CURRENT_DATE, 0.00, 5180.00, 0.00, 0.00, 0.00, 5180.00),
    ('10000000-0000-0000-0000-000000000004', CURRENT_DATE, 27000.00, 0.00, 0.00, 0.00, 0.00, 27000.00),
    ('10000000-0000-0000-0000-000000000005', CURRENT_DATE, 0.00, 0.00, 0.00, 3456.00, 0.00, 3456.00),
    ('10000000-0000-0000-0000-000000000006', CURRENT_DATE, 19440.00, 0.00, 0.00, 0.00, 0.00, 19440.00),
    ('10000000-0000-0000-0000-000000000007', CURRENT_DATE, 0.00, 11200.00, 0.00, 0.00, 0.00, 11200.00);
