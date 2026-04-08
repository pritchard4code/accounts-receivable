--
-- PostgreSQL database dump
--

-- Dumped from database version 16.1
-- Dumped by pg_dump version 16.1

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA public;


--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA public IS 'standard public schema';


--
-- Name: collection_action_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.collection_action_type AS ENUM (
    'email',
    'sms',
    'phone',
    'letter',
    'escalate',
    'hold',
    'write_off'
);


--
-- Name: collection_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.collection_status AS ENUM (
    'scheduled',
    'executed',
    'failed',
    'cancelled'
);


--
-- Name: credit_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.credit_status AS ENUM (
    'good',
    'fair',
    'poor',
    'suspended',
    'on_hold',
    'active',
    'closed'
);


--
-- Name: creditstatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.creditstatus AS ENUM (
    'active',
    'on_hold',
    'suspended',
    'closed'
);


--
-- Name: dispute_reason; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.dispute_reason AS ENUM (
    'billing_error',
    'goods_not_received',
    'service_not_rendered',
    'quality_issue',
    'duplicate_charge',
    'price_discrepancy',
    'other'
);


--
-- Name: dispute_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.dispute_status AS ENUM (
    'open',
    'under_review',
    'resolved',
    'rejected',
    'withdrawn'
);


--
-- Name: gl_posting_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.gl_posting_status AS ENUM (
    'pending',
    'posted',
    'reversed'
);


--
-- Name: invoice_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.invoice_status AS ENUM (
    'draft',
    'sent',
    'viewed',
    'partial',
    'paid',
    'overdue',
    'void',
    'disputed'
);


--
-- Name: payment_method; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.payment_method AS ENUM (
    'credit_card',
    'ach',
    'wire',
    'check',
    'cash',
    'other'
);


--
-- Name: payment_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.payment_status AS ENUM (
    'pending',
    'applied',
    'partially_applied',
    'refunded',
    'voided'
);


--
-- Name: risk_level; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.risk_level AS ENUM (
    'low',
    'medium',
    'high',
    'critical'
);


--
-- Name: user_role; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.user_role AS ENUM (
    'admin',
    'ar_clerk',
    'collections_specialist',
    'finance_manager',
    'credit_manager',
    'customer'
);


--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: aging_snapshots; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.aging_snapshots (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    customer_id uuid NOT NULL,
    snapshot_date date NOT NULL,
    current_amount numeric(15,2) DEFAULT 0.00,
    days_1_30 numeric(15,2) DEFAULT 0.00,
    days_31_60 numeric(15,2) DEFAULT 0.00,
    days_61_90 numeric(15,2) DEFAULT 0.00,
    days_over_90 numeric(15,2) DEFAULT 0.00,
    total_outstanding numeric(15,2) DEFAULT 0.00,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid,
    action character varying(100) NOT NULL,
    entity_type character varying(100) NOT NULL,
    entity_id uuid,
    old_values jsonb,
    new_values jsonb,
    ip_address inet,
    user_agent text,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: collection_actions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.collection_actions (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    customer_id uuid NOT NULL,
    invoice_id uuid,
    workflow_id uuid,
    stage character varying(100),
    action_type public.collection_action_type NOT NULL,
    status public.collection_status DEFAULT 'scheduled'::public.collection_status,
    scheduled_date timestamp with time zone,
    executed_date timestamp with time zone,
    notes text,
    result text,
    created_by uuid,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: collections_workflows; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.collections_workflows (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    is_active boolean DEFAULT true,
    stages jsonb DEFAULT '[]'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: credit_profiles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.credit_profiles (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    customer_id uuid NOT NULL,
    credit_limit numeric(15,2) DEFAULT 0.00,
    current_balance numeric(15,2) DEFAULT 0.00,
    available_credit numeric(15,2) DEFAULT 0.00,
    risk_score numeric(5,2) DEFAULT 0.00,
    risk_level public.risk_level DEFAULT 'low'::public.risk_level,
    payment_score numeric(5,2) DEFAULT 100.00,
    avg_days_to_pay numeric(5,1) DEFAULT 0.0,
    on_time_payment_rate numeric(5,2) DEFAULT 100.00,
    late_payment_count integer DEFAULT 0,
    nsf_count integer DEFAULT 0,
    last_review_date date,
    next_review_date date,
    notes text,
    reviewed_by uuid,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: customers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.customers (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    customer_number character varying(50) NOT NULL,
    name character varying(255) NOT NULL,
    email character varying(255),
    phone character varying(30),
    address character varying(500),
    city character varying(100),
    state character varying(100),
    zip character varying(20),
    country character varying(100) DEFAULT 'US'::character varying,
    currency character varying(10) DEFAULT 'USD'::character varying,
    language character varying(10) DEFAULT 'en'::character varying,
    credit_limit numeric(15,2) DEFAULT 0.00,
    credit_status public.credit_status DEFAULT 'good'::public.credit_status,
    payment_terms integer DEFAULT 30,
    tax_id character varying(50),
    website character varying(255),
    notes text,
    sales_rep character varying(100),
    industry character varying(100),
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: dispute_documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dispute_documents (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    dispute_id uuid NOT NULL,
    filename character varying(255) NOT NULL,
    file_path character varying(500),
    file_size integer,
    content_type character varying(100),
    uploaded_by uuid,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: disputes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.disputes (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    dispute_number character varying(50) NOT NULL,
    customer_id uuid NOT NULL,
    invoice_id uuid,
    status public.dispute_status DEFAULT 'open'::public.dispute_status,
    reason public.dispute_reason NOT NULL,
    description text,
    amount_disputed numeric(15,2) DEFAULT 0.00,
    resolution text,
    resolved_amount numeric(15,2),
    assigned_to uuid,
    created_by uuid,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    resolved_at timestamp with time zone
);


--
-- Name: dunning_rules; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dunning_rules (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name character varying(255) NOT NULL,
    days_overdue_min integer DEFAULT 0 NOT NULL,
    days_overdue_max integer,
    action_type public.collection_action_type NOT NULL,
    template text,
    subject character varying(500),
    priority integer DEFAULT 1,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: gl_postings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gl_postings (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    invoice_id uuid,
    payment_id uuid,
    posting_date date DEFAULT CURRENT_DATE NOT NULL,
    account_code character varying(50) NOT NULL,
    debit_amount numeric(15,2) DEFAULT 0.00,
    credit_amount numeric(15,2) DEFAULT 0.00,
    description text,
    reference character varying(255),
    status public.gl_posting_status DEFAULT 'pending'::public.gl_posting_status,
    posted_by uuid,
    posted_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: invoice_line_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.invoice_line_items (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    invoice_id uuid NOT NULL,
    line_number integer DEFAULT 1 NOT NULL,
    description text NOT NULL,
    quantity numeric(10,3) DEFAULT 1.000,
    unit_price numeric(15,2) DEFAULT 0.00,
    total_price numeric(15,2) DEFAULT 0.00,
    tax_rate numeric(5,4) DEFAULT 0.0000,
    tax_amount numeric(15,2) DEFAULT 0.00,
    discount_rate numeric(5,4) DEFAULT 0.0000,
    discount_amount numeric(15,2) DEFAULT 0.00,
    product_code character varying(50),
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: invoice_templates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.invoice_templates (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name character varying(255) NOT NULL,
    content text,
    is_default boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: invoices; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.invoices (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    invoice_number character varying(50) NOT NULL,
    customer_id uuid NOT NULL,
    status public.invoice_status DEFAULT 'draft'::public.invoice_status,
    invoice_date date DEFAULT CURRENT_DATE NOT NULL,
    due_date date NOT NULL,
    subtotal numeric(15,2) DEFAULT 0.00,
    tax_amount numeric(15,2) DEFAULT 0.00,
    discount_amount numeric(15,2) DEFAULT 0.00,
    total_amount numeric(15,2) DEFAULT 0.00,
    paid_amount numeric(15,2) DEFAULT 0.00,
    balance_due numeric(15,2) DEFAULT 0.00,
    currency character varying(10) DEFAULT 'USD'::character varying,
    payment_terms integer DEFAULT 30,
    po_number character varying(100),
    notes text,
    internal_notes text,
    template_id uuid,
    sent_at timestamp with time zone,
    viewed_at timestamp with time zone,
    created_by uuid,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    plan_id character varying(16)
);


--
-- Name: notifications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notifications (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid,
    customer_id uuid,
    type character varying(100) NOT NULL,
    title character varying(500) NOT NULL,
    message text,
    is_read boolean DEFAULT false,
    data jsonb,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: payment_allocations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payment_allocations (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    payment_id uuid NOT NULL,
    invoice_id uuid NOT NULL,
    allocated_amount numeric(15,2) NOT NULL,
    allocated_at timestamp with time zone DEFAULT now(),
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: payments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payments (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    payment_number character varying(50) NOT NULL,
    customer_id uuid NOT NULL,
    payment_date date DEFAULT CURRENT_DATE NOT NULL,
    amount numeric(15,2) NOT NULL,
    unapplied_amount numeric(15,2) DEFAULT 0.00,
    payment_method public.payment_method NOT NULL,
    status public.payment_status DEFAULT 'pending'::public.payment_status,
    reference character varying(255),
    gateway_transaction_id character varying(255),
    gateway_response jsonb,
    notes text,
    recorded_by uuid,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: recurring_invoices; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.recurring_invoices (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    customer_id uuid NOT NULL,
    template_invoice_id uuid,
    frequency character varying(20) DEFAULT 'monthly'::character varying NOT NULL,
    next_invoice_date date,
    end_date date,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: ref_status; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ref_status (
    status_id uuid NOT NULL,
    status_nm character varying(50) NOT NULL,
    status_desc character varying(255)
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    username character varying(100) NOT NULL,
    email character varying(255) NOT NULL,
    hashed_password character varying(255) NOT NULL,
    role public.user_role DEFAULT 'ar_clerk'::public.user_role NOT NULL,
    first_name character varying(100),
    last_name character varying(100),
    phone character varying(30),
    is_active boolean DEFAULT true,
    last_login timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Data for Name: aging_snapshots; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.aging_snapshots (id, customer_id, snapshot_date, current_amount, days_1_30, days_31_60, days_61_90, days_over_90, total_outstanding, created_at) FROM stdin;
42fc3e63-dbb6-4da9-b4ba-60cc86dc424f	10000000-0000-0000-0000-000000000001	2026-04-06	8100.00	0.00	5400.00	0.00	0.00	13500.00	2026-04-06 18:52:31.800303-04
3e698b97-8a02-4909-ab4a-15704aa670ff	10000000-0000-0000-0000-000000000003	2026-04-06	0.00	5180.00	0.00	0.00	0.00	5180.00	2026-04-06 18:52:31.800303-04
d569de58-a989-46ce-8338-17f5036de1a8	10000000-0000-0000-0000-000000000004	2026-04-06	27000.00	0.00	0.00	0.00	0.00	27000.00	2026-04-06 18:52:31.800303-04
63f355af-5ed6-4aab-943c-8edf97714d8e	10000000-0000-0000-0000-000000000005	2026-04-06	0.00	0.00	0.00	3456.00	0.00	3456.00	2026-04-06 18:52:31.800303-04
6635caf0-470a-4f85-a27e-6641d79b504f	10000000-0000-0000-0000-000000000006	2026-04-06	19440.00	0.00	0.00	0.00	0.00	19440.00	2026-04-06 18:52:31.800303-04
4515dd71-0d50-44ee-90a4-bd8153f3ec22	10000000-0000-0000-0000-000000000007	2026-04-06	0.00	11200.00	0.00	0.00	0.00	11200.00	2026-04-06 18:52:31.800303-04
\.


--
-- Data for Name: audit_logs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.audit_logs (id, user_id, action, entity_type, entity_id, old_values, new_values, ip_address, user_agent, created_at) FROM stdin;
\.


--
-- Data for Name: collection_actions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.collection_actions (id, customer_id, invoice_id, workflow_id, stage, action_type, status, scheduled_date, executed_date, notes, result, created_by, created_at) FROM stdin;
\.


--
-- Data for Name: collections_workflows; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.collections_workflows (id, name, description, is_active, stages, created_at, updated_at) FROM stdin;
50000000-0000-0000-0000-000000000001	Standard AR Collections	Default collections workflow for AR	t	[{"name": "Initial Reminder", "stage": 1, "action": "email", "days_overdue": 1}, {"name": "Second Notice", "stage": 2, "action": "email", "days_overdue": 8}, {"name": "Final Warning", "stage": 3, "action": "email", "days_overdue": 15}, {"name": "Phone Call", "stage": 4, "action": "phone", "days_overdue": 20}, {"name": "Escalate", "stage": 5, "action": "escalate", "days_overdue": 31}]	2026-04-06 18:52:31.794699-04	2026-04-06 18:52:31.794699-04
\.


--
-- Data for Name: credit_profiles; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.credit_profiles (id, customer_id, credit_limit, current_balance, available_credit, risk_score, risk_level, payment_score, avg_days_to_pay, on_time_payment_rate, late_payment_count, nsf_count, last_review_date, next_review_date, notes, reviewed_by, created_at, updated_at) FROM stdin;
516b0b76-e5cc-4d10-93d4-917c48bd198e	10000000-0000-0000-0000-000000000001	50000.00	13500.00	36500.00	25.00	low	85.00	28.5	90.00	0	0	2026-01-01	\N	\N	\N	2026-04-06 18:52:31.780499-04	2026-04-07 21:23:28.328072-04
0b5477cd-7414-448f-8373-b3392bce9e34	10000000-0000-0000-0000-000000000002	100000.00	0.00	100000.00	10.00	low	95.00	20.0	98.00	0	0	2026-01-01	\N	\N	\N	2026-04-06 18:52:31.780499-04	2026-04-07 21:23:28.328072-04
fcd39d4a-0566-445a-8c1b-00000a3af8a8	10000000-0000-0000-0000-000000000003	75000.00	5180.00	69820.00	45.00	medium	70.00	42.0	75.00	0	0	2026-01-01	\N	\N	\N	2026-04-06 18:52:31.780499-04	2026-04-07 21:23:28.328072-04
ea6baaaa-0eae-49cd-b9e8-b7066ec8566a	10000000-0000-0000-0000-000000000004	200000.00	27000.00	173000.00	15.00	low	92.00	35.0	95.00	0	0	2026-01-01	\N	\N	\N	2026-04-06 18:52:31.780499-04	2026-04-07 21:23:28.328072-04
431756d1-9827-4429-9c88-95442b8f6131	10000000-0000-0000-0000-000000000005	30000.00	3456.00	26544.00	75.00	high	45.00	65.0	55.00	0	0	2026-01-01	\N	\N	\N	2026-04-06 18:52:31.780499-04	2026-04-07 21:23:28.328072-04
225a53a6-fa43-4786-8b0e-f9a9113812e4	10000000-0000-0000-0000-000000000006	150000.00	19440.00	130560.00	20.00	low	90.00	25.0	97.00	0	0	2026-01-01	\N	\N	\N	2026-04-06 18:52:31.780499-04	2026-04-07 21:23:28.328072-04
76a2cf45-46d9-4bce-90c4-f4ac6f64d485	10000000-0000-0000-0000-000000000007	80000.00	11200.00	68800.00	50.00	medium	65.00	48.0	70.00	0	0	2026-01-01	\N	\N	\N	2026-04-06 18:52:31.780499-04	2026-04-07 21:23:28.328072-04
e8668e5f-7d37-4bf7-9090-c20cecf13be4	10000000-0000-0000-0000-000000000008	60000.00	0.00	60000.00	12.00	low	93.00	22.0	96.00	0	0	2026-01-01	\N	\N	\N	2026-04-06 18:52:31.780499-04	2026-04-07 21:23:28.328072-04
\.


--
-- Data for Name: customers; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.customers (id, customer_number, name, email, phone, address, city, state, zip, country, currency, language, credit_limit, credit_status, payment_terms, tax_id, website, notes, sales_rep, industry, is_active, created_at, updated_at) FROM stdin;
10000000-0000-0000-0000-000000000001	CUST-001	Acme Corporation	ap@acme.com	555-0101	123 Main St	New York	NY	10001	US	USD	en	50000.00	active	30	\N	\N	\N	\N	Manufacturing	t	2026-04-06 18:52:31.743897-04	2026-04-07 21:38:46.366819-04
10000000-0000-0000-0000-000000000002	CUST-002	Global Tech Solutions	billing@globaltech.com	555-0102	456 Tech Ave	San Francisco	CA	94105	US	USD	en	100000.00	active	45	\N	\N	\N	\N	Technology	t	2026-04-06 18:52:31.743897-04	2026-04-07 21:38:46.366819-04
10000000-0000-0000-0000-000000000004	CUST-004	Sunrise Healthcare	accounts@sunrisehealth.com	555-0104	321 Medical Way	Houston	TX	77001	US	USD	en	200000.00	active	60	\N	\N	\N	\N	Healthcare	t	2026-04-06 18:52:31.743897-04	2026-04-07 21:38:46.366819-04
10000000-0000-0000-0000-000000000006	CUST-006	Summit Financial Group	billing@summitfin.com	555-0106	987 Wall St	New York	NY	10005	US	USD	en	150000.00	active	30	\N	\N	\N	\N	Finance	t	2026-04-06 18:52:31.743897-04	2026-04-07 21:38:46.366819-04
10000000-0000-0000-0000-000000000008	CUST-008	DataStream Analytics	finance@datastream.io	555-0108	258 Data Center Dr	Austin	TX	78701	US	USD	en	60000.00	active	30	\N	\N	\N	\N	Technology	t	2026-04-06 18:52:31.743897-04	2026-04-07 21:38:46.366819-04
10000000-0000-0000-0000-000000000003	CUST-003	Metro Retail Group	finance@metroretail.com	555-0103	789 Commerce Blvd	Chicago	IL	60601	US	USD	en	75000.00	on_hold	30	\N	\N	\N	\N	Retail	t	2026-04-06 18:52:31.743897-04	2026-04-07 21:38:46.366819-04
10000000-0000-0000-0000-000000000007	CUST-007	Greenfield Builders	accounts@greenfieldbuild.com	555-0107	147 Construction Rd	Phoenix	AZ	85001	US	USD	en	80000.00	on_hold	45	\N	\N	\N	\N	Construction	t	2026-04-06 18:52:31.743897-04	2026-04-07 21:38:46.366819-04
10000000-0000-0000-0000-000000000005	CUST-005	Pacific Logistics	payables@paclogistics.com	555-0105	654 Harbor Dr	Seattle	WA	98101	US	USD	en	30000.00	suspended	15	\N	\N	\N	\N	Logistics	t	2026-04-06 18:52:31.743897-04	2026-04-07 21:38:46.366819-04
\.


--
-- Data for Name: dispute_documents; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dispute_documents (id, dispute_id, filename, file_path, file_size, content_type, uploaded_by, created_at) FROM stdin;
\.


--
-- Data for Name: disputes; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.disputes (id, dispute_number, customer_id, invoice_id, status, reason, description, amount_disputed, resolution, resolved_amount, assigned_to, created_by, created_at, updated_at, resolved_at) FROM stdin;
60000000-0000-0000-0000-000000000001	DIS-2024-001	10000000-0000-0000-0000-000000000003	30000000-0000-0000-0000-000000000003	open	price_discrepancy	Customer claims they were quoted a different price for SKU-B200	1400.00	\N	\N	00000000-0000-0000-0000-000000000002	00000000-0000-0000-0000-000000000002	2026-04-06 18:52:31.795954-04	2026-04-07 21:23:28.328072-04	\N
\.


--
-- Data for Name: dunning_rules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dunning_rules (id, name, days_overdue_min, days_overdue_max, action_type, template, subject, priority, is_active, created_at, updated_at) FROM stdin;
9ef464d0-efe2-43c2-ae0c-356622ced880	First Reminder	1	7	email	Dear {{customer_name}}, Your invoice {{invoice_number}} for {{amount}} was due on {{due_date}}. Please arrange payment at your earliest convenience.	Payment Reminder - Invoice {{invoice_number}}	1	t	2026-04-06 18:52:31.789478-04	2026-04-06 18:52:31.789478-04
f8f43bab-37d1-4a20-982e-cd06dbccd5e1	Second Notice	8	14	email	Dear {{customer_name}}, This is a second notice that invoice {{invoice_number}} for {{amount}} is now {{days_overdue}} days past due. Please contact us immediately.	SECOND NOTICE: Overdue Invoice {{invoice_number}}	2	t	2026-04-06 18:52:31.789478-04	2026-04-06 18:52:31.789478-04
fbfa0bb9-eab8-4ce1-ac20-66bc6ab62918	Final Warning	15	30	email	Dear {{customer_name}}, FINAL NOTICE: Invoice {{invoice_number}} for {{amount}} is {{days_overdue}} days past due. Failure to pay may result in service suspension.	FINAL NOTICE: Immediate Payment Required	3	t	2026-04-06 18:52:31.789478-04	2026-04-06 18:52:31.789478-04
857148fe-bc06-41ce-8cfd-373a8616e5e1	Phone Follow-up	15	30	phone	Call customer to discuss outstanding balance	Phone Collection Call	2	t	2026-04-06 18:52:31.789478-04	2026-04-06 18:52:31.789478-04
ceea57a0-40d9-42be-8921-cb6d7208f7d2	Collections Escalation	31	\N	escalate	Escalate account to collections team for further action	Account Escalated to Collections	1	t	2026-04-06 18:52:31.789478-04	2026-04-06 18:52:31.789478-04
\.


--
-- Data for Name: gl_postings; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.gl_postings (id, invoice_id, payment_id, posting_date, account_code, debit_amount, credit_amount, description, reference, status, posted_by, posted_at, created_at) FROM stdin;
\.


--
-- Data for Name: invoice_line_items; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.invoice_line_items (id, invoice_id, line_number, description, quantity, unit_price, total_price, tax_rate, tax_amount, discount_rate, discount_amount, product_code, created_at) FROM stdin;
53ddb794-24b0-416d-b976-a15e7eba177c	30000000-0000-0000-0000-000000000001	1	Enterprise Software License - Annual	5.000	800.00	4000.00	0.0800	320.00	0.0000	0.00	\N	2026-04-06 18:52:31.755018-04
cd039023-f46c-4053-a269-7b790fd31d2a	30000000-0000-0000-0000-000000000001	2	Implementation Support	10.000	100.00	1000.00	0.0800	80.00	0.0000	0.00	\N	2026-04-06 18:52:31.755018-04
6b700fe4-feac-42ee-bb5f-61ef1c2ebbf8	30000000-0000-0000-0000-000000000003	1	Product SKU-A100	100.000	50.00	5000.00	0.0800	400.00	0.0000	0.00	\N	2026-04-06 18:52:31.755018-04
f2836ef5-cde7-416f-b520-cd16b32fdced	30000000-0000-0000-0000-000000000003	2	Product SKU-B200	50.000	70.00	3500.00	0.0800	280.00	0.0000	0.00	\N	2026-04-06 18:52:31.755018-04
84dae74c-5d19-4774-a4f2-9f58f878d0bb	30000000-0000-0000-0000-000000000004	1	MRI Equipment Maintenance Contract	1.000	25000.00	25000.00	0.0800	2000.00	0.0000	0.00	\N	2026-04-06 18:52:31.755018-04
70862a1f-4d9c-4761-be0d-7d03671512f0	30000000-0000-0000-0000-000000000005	1	Cross-country Freight - 4 shipments	4.000	800.00	3200.00	0.0800	256.00	0.0000	0.00	\N	2026-04-06 18:52:31.755018-04
85b1c7c5-2fbf-4c85-9150-a1c68cda8fd7	30000000-0000-0000-0000-000000000008	1	Steel Beams - 50 units	50.000	200.00	10000.00	0.0800	800.00	0.0000	0.00	\N	2026-04-06 18:52:31.755018-04
d8fe3558-eb52-4dce-84ba-4daa14f54678	30000000-0000-0000-0000-000000000008	2	Concrete Mix - 10 tons	10.000	500.00	5000.00	0.0800	400.00	0.0000	0.00	\N	2026-04-06 18:52:31.755018-04
979f8c10-7f45-4b75-acb5-475976a6843c	30000000-0000-0000-0000-000000000002	1	Senior Consultant - 80 hours	80.000	150.00	12960.00	0.0800	960.00	0.0000	0.00	\N	2026-04-07 10:21:57.291573-04
953f76ed-3b5f-43dc-8ac9-9b98f03fbf97	30000000-0000-0000-0000-000000000006	1	Investment Portfolio Advisory Q1	1.000	18000.00	19440.00	0.0800	1440.00	0.0000	0.00	\N	2026-04-07 14:52:46.620453-04
\.


--
-- Data for Name: invoice_templates; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.invoice_templates (id, name, content, is_default, created_at) FROM stdin;
20000000-0000-0000-0000-000000000001	Standard Invoice	<html><body><h1>INVOICE</h1></body></html>	t	2026-04-06 18:52:31.747951-04
20000000-0000-0000-0000-000000000002	Service Invoice	<html><body><h1>SERVICE INVOICE</h1></body></html>	f	2026-04-06 18:52:31.747951-04
\.


--
-- Data for Name: invoices; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.invoices (id, invoice_number, customer_id, status, invoice_date, due_date, subtotal, tax_amount, discount_amount, total_amount, paid_amount, balance_due, currency, payment_terms, po_number, notes, internal_notes, template_id, sent_at, viewed_at, created_by, created_at, updated_at, plan_id) FROM stdin;
30000000-0000-0000-0000-000000000001	INV-2024-001	10000000-0000-0000-0000-000000000001	overdue	2026-01-15	2026-02-14	5000.00	400.00	0.00	5400.00	0.00	5400.00	USD	30	\N	Software licenses Q1	\N	\N	\N	\N	00000000-0000-0000-0000-000000000002	2026-04-06 18:52:31.74928-04	2026-04-07 21:23:28.328072-04	\N
30000000-0000-0000-0000-000000000002	INV-2024-002	10000000-0000-0000-0000-000000000002	paid	2026-01-20	2026-03-05	12000.00	960.00	0.00	12960.00	12960.00	0.00	USD	45	\N	Consulting services January	\N	\N	\N	\N	00000000-0000-0000-0000-000000000002	2026-04-06 18:52:31.74928-04	2026-04-07 21:23:28.328072-04	\N
30000000-0000-0000-0000-000000000004	INV-2024-004	10000000-0000-0000-0000-000000000004	sent	2026-02-15	2026-04-15	25000.00	2000.00	0.00	27000.00	0.00	27000.00	USD	60	\N	Medical equipment maintenance	\N	\N	\N	\N	00000000-0000-0000-0000-000000000002	2026-04-06 18:52:31.74928-04	2026-04-07 21:23:28.328072-04	\N
30000000-0000-0000-0000-000000000005	INV-2024-005	10000000-0000-0000-0000-000000000005	overdue	2026-01-01	2026-01-16	3200.00	256.00	0.00	3456.00	0.00	3456.00	USD	15	\N	Freight services January	\N	\N	\N	\N	00000000-0000-0000-0000-000000000002	2026-04-06 18:52:31.74928-04	2026-04-07 21:23:28.328072-04	\N
30000000-0000-0000-0000-000000000007	INV-2024-007	10000000-0000-0000-0000-000000000001	draft	2026-03-10	2026-04-09	7500.00	600.00	0.00	8100.00	0.00	8100.00	USD	30	\N	Software support Q2	\N	\N	\N	\N	00000000-0000-0000-0000-000000000002	2026-04-06 18:52:31.74928-04	2026-04-07 21:23:28.328072-04	\N
30000000-0000-0000-0000-000000000008	INV-2024-008	10000000-0000-0000-0000-000000000007	overdue	2026-01-25	2026-03-10	15000.00	1200.00	0.00	16200.00	5000.00	11200.00	USD	45	\N	Construction materials	\N	\N	\N	\N	00000000-0000-0000-0000-000000000002	2026-04-06 18:52:31.74928-04	2026-04-07 21:23:28.328072-04	\N
30000000-0000-0000-0000-000000000003	INV-2024-003	10000000-0000-0000-0000-000000000003	void	2026-02-01	2026-03-02	8500.00	680.00	0.00	9180.00	4000.00	5180.00	USD	30	\N	Product supply February	\N	\N	\N	\N	00000000-0000-0000-0000-000000000002	2026-04-06 18:52:31.74928-04	2026-04-07 21:23:28.328072-04	\N
30000000-0000-0000-0000-000000000006	INV-2024-006	10000000-0000-0000-0000-000000000006	sent	2026-03-01	2026-03-31	18000.00	1440.00	0.00	19440.00	0.00	19440.00	USD	30	\N	Financial advisory Q1	\N	\N	\N	\N	00000000-0000-0000-0000-000000000002	2026-04-06 18:52:31.74928-04	2026-04-07 21:23:28.328072-04	BEE-001
\.


--
-- Data for Name: notifications; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.notifications (id, user_id, customer_id, type, title, message, is_read, data, created_at) FROM stdin;
\.


--
-- Data for Name: payment_allocations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.payment_allocations (id, payment_id, invoice_id, allocated_amount, allocated_at, created_at) FROM stdin;
f75994f7-7e35-45d8-8c72-d81ec5b64c63	40000000-0000-0000-0000-000000000001	30000000-0000-0000-0000-000000000002	12960.00	2026-04-06 18:52:31.774736-04	2026-04-06 18:52:31.774736-04
a67e6952-e569-4f1e-82ea-c50c2d7989cc	40000000-0000-0000-0000-000000000002	30000000-0000-0000-0000-000000000003	4000.00	2026-04-06 18:52:31.774736-04	2026-04-06 18:52:31.774736-04
c486fb5d-7fc8-4729-b3f0-53a0773422bf	40000000-0000-0000-0000-000000000003	30000000-0000-0000-0000-000000000008	5000.00	2026-04-06 18:52:31.774736-04	2026-04-06 18:52:31.774736-04
\.


--
-- Data for Name: payments; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.payments (id, payment_number, customer_id, payment_date, amount, unapplied_amount, payment_method, status, reference, gateway_transaction_id, gateway_response, notes, recorded_by, created_at, updated_at) FROM stdin;
40000000-0000-0000-0000-000000000001	PMT-2024-001	10000000-0000-0000-0000-000000000002	2026-02-25	12960.00	0.00	ach	applied	ACH-REF-12345	\N	\N	Full payment for INV-2024-002	00000000-0000-0000-0000-000000000002	2026-04-06 18:52:31.769042-04	2026-04-07 21:23:28.328072-04
40000000-0000-0000-0000-000000000002	PMT-2024-002	10000000-0000-0000-0000-000000000003	2026-02-20	4000.00	0.00	check	applied	CHK-67890	\N	\N	Partial payment for INV-2024-003	00000000-0000-0000-0000-000000000002	2026-04-06 18:52:31.769042-04	2026-04-07 21:23:28.328072-04
40000000-0000-0000-0000-000000000003	PMT-2024-003	10000000-0000-0000-0000-000000000007	2026-02-28	5000.00	0.00	wire	applied	WIRE-11111	\N	\N	Partial payment INV-2024-008	00000000-0000-0000-0000-000000000002	2026-04-06 18:52:31.769042-04	2026-04-07 21:23:28.328072-04
\.


--
-- Data for Name: recurring_invoices; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.recurring_invoices (id, customer_id, template_invoice_id, frequency, next_invoice_date, end_date, is_active, created_at) FROM stdin;
\.


--
-- Data for Name: ref_status; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.ref_status (status_id, status_nm, status_desc) FROM stdin;
10000000-0000-0000-0000-000000000001	OVERDUE	Overdue invoice
10000000-0000-0000-0000-000000000002	PAID	Paid invoice
10000000-0000-0000-0000-000000000003	SENT	Sent Invoice
10000000-0000-0000-0000-000000000004	DRAFT	Invoice under construction
10000000-0000-0000-0000-000000000005	VOID	Voided invoice
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.users (id, username, email, hashed_password, role, first_name, last_name, phone, is_active, last_login, created_at, updated_at) FROM stdin;
00000000-0000-0000-0000-000000000003	collections1	collections@armanager.com	$2b$12$i5Ma02QHBGLNySCFIX8Io.uT4PH2vRe/1mRcYhWmOIZQlZRtKE.CC	collections_specialist	Bob	Johnson	\N	t	\N	2026-04-06 18:52:31.739641-04	2026-04-07 21:23:28.328072-04
00000000-0000-0000-0000-000000000004	finance_mgr	finance@armanager.com	$2b$12$k3xeW7P5dtB7PjyNZaBkneSoDZzs3PS0vmUalnnY5/vB9xCuvRNQi	finance_manager	Alice	Williams	\N	t	\N	2026-04-06 18:52:31.739641-04	2026-04-07 21:23:28.328072-04
00000000-0000-0000-0000-000000000005	credit_mgr	credit@armanager.com	$2b$12$Df4oFgefMj0SPzkZcyzpaevmNqFV3X8Uvd4IT.1TaQAEQXd/4n4vm	credit_manager	Tom	Brown	\N	t	\N	2026-04-06 18:52:31.739641-04	2026-04-07 21:23:28.328072-04
00000000-0000-0000-0000-000000000001	admin	admin@armanager.com	$2b$12$5s4KutzndemQS3Qf18wmeel4QEcXPnSKSEb/OY5bmNWHd/s5Zlxj6	admin	System	Administrator	\N	t	2026-04-08 01:28:40.790403-04	2026-04-06 18:52:31.739641-04	2026-04-07 21:28:40.519839-04
00000000-0000-0000-0000-000000000002	ar_clerk1	clerk@armanager.com	$2b$12$X10F7l2NFftpO/.oWr/Zq.pMF8B7ivZnumjKrMgQZDCek3IZ8oWgS	ar_clerk	Jane	Smith	\N	t	2026-04-08 01:56:19.360684-04	2026-04-06 18:52:31.739641-04	2026-04-07 21:56:19.12393-04
\.


--
-- Name: aging_snapshots aging_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.aging_snapshots
    ADD CONSTRAINT aging_snapshots_pkey PRIMARY KEY (id);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: collection_actions collection_actions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.collection_actions
    ADD CONSTRAINT collection_actions_pkey PRIMARY KEY (id);


--
-- Name: collections_workflows collections_workflows_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.collections_workflows
    ADD CONSTRAINT collections_workflows_pkey PRIMARY KEY (id);


--
-- Name: credit_profiles credit_profiles_customer_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credit_profiles
    ADD CONSTRAINT credit_profiles_customer_id_key UNIQUE (customer_id);


--
-- Name: credit_profiles credit_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credit_profiles
    ADD CONSTRAINT credit_profiles_pkey PRIMARY KEY (id);


--
-- Name: customers customers_customer_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customers
    ADD CONSTRAINT customers_customer_number_key UNIQUE (customer_number);


--
-- Name: customers customers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customers
    ADD CONSTRAINT customers_pkey PRIMARY KEY (id);


--
-- Name: dispute_documents dispute_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dispute_documents
    ADD CONSTRAINT dispute_documents_pkey PRIMARY KEY (id);


--
-- Name: disputes disputes_dispute_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.disputes
    ADD CONSTRAINT disputes_dispute_number_key UNIQUE (dispute_number);


--
-- Name: disputes disputes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.disputes
    ADD CONSTRAINT disputes_pkey PRIMARY KEY (id);


--
-- Name: dunning_rules dunning_rules_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dunning_rules
    ADD CONSTRAINT dunning_rules_pkey PRIMARY KEY (id);


--
-- Name: gl_postings gl_postings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gl_postings
    ADD CONSTRAINT gl_postings_pkey PRIMARY KEY (id);


--
-- Name: invoice_line_items invoice_line_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_line_items
    ADD CONSTRAINT invoice_line_items_pkey PRIMARY KEY (id);


--
-- Name: invoice_templates invoice_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_templates
    ADD CONSTRAINT invoice_templates_pkey PRIMARY KEY (id);


--
-- Name: invoices invoices_invoice_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_invoice_number_key UNIQUE (invoice_number);


--
-- Name: invoices invoices_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_pkey PRIMARY KEY (id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: payment_allocations payment_allocations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_allocations
    ADD CONSTRAINT payment_allocations_pkey PRIMARY KEY (id);


--
-- Name: payments payments_payment_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_payment_number_key UNIQUE (payment_number);


--
-- Name: payments payments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_pkey PRIMARY KEY (id);


--
-- Name: recurring_invoices recurring_invoices_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recurring_invoices
    ADD CONSTRAINT recurring_invoices_pkey PRIMARY KEY (id);


--
-- Name: ref_status ref_status_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ref_status
    ADD CONSTRAINT ref_status_pkey PRIMARY KEY (status_id);


--
-- Name: ref_status ref_status_status_nm_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ref_status
    ADD CONSTRAINT ref_status_status_nm_key UNIQUE (status_nm);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: idx_aging_snapshots_customer; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_aging_snapshots_customer ON public.aging_snapshots USING btree (customer_id);


--
-- Name: idx_aging_snapshots_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_aging_snapshots_date ON public.aging_snapshots USING btree (snapshot_date);


--
-- Name: idx_allocations_invoice; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_allocations_invoice ON public.payment_allocations USING btree (invoice_id);


--
-- Name: idx_allocations_payment; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_allocations_payment ON public.payment_allocations USING btree (payment_id);


--
-- Name: idx_audit_logs_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_logs_created ON public.audit_logs USING btree (created_at);


--
-- Name: idx_audit_logs_entity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_logs_entity ON public.audit_logs USING btree (entity_type, entity_id);


--
-- Name: idx_audit_logs_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_logs_user ON public.audit_logs USING btree (user_id);


--
-- Name: idx_collection_actions_customer; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_collection_actions_customer ON public.collection_actions USING btree (customer_id);


--
-- Name: idx_collection_actions_invoice; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_collection_actions_invoice ON public.collection_actions USING btree (invoice_id);


--
-- Name: idx_collection_actions_scheduled; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_collection_actions_scheduled ON public.collection_actions USING btree (scheduled_date);


--
-- Name: idx_collection_actions_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_collection_actions_status ON public.collection_actions USING btree (status);


--
-- Name: idx_credit_profiles_customer; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_credit_profiles_customer ON public.credit_profiles USING btree (customer_id);


--
-- Name: idx_credit_profiles_risk; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_credit_profiles_risk ON public.credit_profiles USING btree (risk_level);


--
-- Name: idx_customers_credit_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_customers_credit_status ON public.customers USING btree (credit_status);


--
-- Name: idx_customers_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_customers_email ON public.customers USING btree (email);


--
-- Name: idx_customers_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_customers_name ON public.customers USING gin (name public.gin_trgm_ops);


--
-- Name: idx_customers_number; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_customers_number ON public.customers USING btree (customer_number);


--
-- Name: idx_dispute_docs_dispute; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dispute_docs_dispute ON public.dispute_documents USING btree (dispute_id);


--
-- Name: idx_disputes_customer; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_disputes_customer ON public.disputes USING btree (customer_id);


--
-- Name: idx_disputes_invoice; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_disputes_invoice ON public.disputes USING btree (invoice_id);


--
-- Name: idx_disputes_number; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_disputes_number ON public.disputes USING btree (dispute_number);


--
-- Name: idx_disputes_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_disputes_status ON public.disputes USING btree (status);


--
-- Name: idx_dunning_rules_days; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dunning_rules_days ON public.dunning_rules USING btree (days_overdue_min, days_overdue_max);


--
-- Name: idx_gl_postings_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gl_postings_date ON public.gl_postings USING btree (posting_date);


--
-- Name: idx_gl_postings_invoice; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gl_postings_invoice ON public.gl_postings USING btree (invoice_id);


--
-- Name: idx_gl_postings_payment; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_gl_postings_payment ON public.gl_postings USING btree (payment_id);


--
-- Name: idx_invoices_customer; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_invoices_customer ON public.invoices USING btree (customer_id);


--
-- Name: idx_invoices_due_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_invoices_due_date ON public.invoices USING btree (due_date);


--
-- Name: idx_invoices_invoice_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_invoices_invoice_date ON public.invoices USING btree (invoice_date);


--
-- Name: idx_invoices_number; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_invoices_number ON public.invoices USING btree (invoice_number);


--
-- Name: idx_invoices_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_invoices_status ON public.invoices USING btree (status);


--
-- Name: idx_line_items_invoice; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_line_items_invoice ON public.invoice_line_items USING btree (invoice_id);


--
-- Name: idx_notifications_read; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notifications_read ON public.notifications USING btree (user_id, is_read);


--
-- Name: idx_notifications_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notifications_user ON public.notifications USING btree (user_id);


--
-- Name: idx_payments_customer; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_payments_customer ON public.payments USING btree (customer_id);


--
-- Name: idx_payments_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_payments_date ON public.payments USING btree (payment_date);


--
-- Name: idx_payments_number; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_payments_number ON public.payments USING btree (payment_number);


--
-- Name: idx_payments_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_payments_status ON public.payments USING btree (status);


--
-- Name: idx_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_email ON public.users USING btree (email);


--
-- Name: idx_users_role; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_role ON public.users USING btree (role);


--
-- Name: idx_users_username; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_username ON public.users USING btree (username);


--
-- Name: credit_profiles update_credit_profiles_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_credit_profiles_updated_at BEFORE UPDATE ON public.credit_profiles FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: customers update_customers_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_customers_updated_at BEFORE UPDATE ON public.customers FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: disputes update_disputes_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_disputes_updated_at BEFORE UPDATE ON public.disputes FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: invoices update_invoices_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_invoices_updated_at BEFORE UPDATE ON public.invoices FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: payments update_payments_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_payments_updated_at BEFORE UPDATE ON public.payments FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: users update_users_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: aging_snapshots aging_snapshots_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.aging_snapshots
    ADD CONSTRAINT aging_snapshots_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id);


--
-- Name: audit_logs audit_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: collection_actions collection_actions_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.collection_actions
    ADD CONSTRAINT collection_actions_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: collection_actions collection_actions_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.collection_actions
    ADD CONSTRAINT collection_actions_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id);


--
-- Name: collection_actions collection_actions_invoice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.collection_actions
    ADD CONSTRAINT collection_actions_invoice_id_fkey FOREIGN KEY (invoice_id) REFERENCES public.invoices(id);


--
-- Name: collection_actions collection_actions_workflow_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.collection_actions
    ADD CONSTRAINT collection_actions_workflow_id_fkey FOREIGN KEY (workflow_id) REFERENCES public.collections_workflows(id);


--
-- Name: credit_profiles credit_profiles_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credit_profiles
    ADD CONSTRAINT credit_profiles_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id) ON DELETE CASCADE;


--
-- Name: credit_profiles credit_profiles_reviewed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credit_profiles
    ADD CONSTRAINT credit_profiles_reviewed_by_fkey FOREIGN KEY (reviewed_by) REFERENCES public.users(id);


--
-- Name: dispute_documents dispute_documents_dispute_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dispute_documents
    ADD CONSTRAINT dispute_documents_dispute_id_fkey FOREIGN KEY (dispute_id) REFERENCES public.disputes(id) ON DELETE CASCADE;


--
-- Name: dispute_documents dispute_documents_uploaded_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dispute_documents
    ADD CONSTRAINT dispute_documents_uploaded_by_fkey FOREIGN KEY (uploaded_by) REFERENCES public.users(id);


--
-- Name: disputes disputes_assigned_to_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.disputes
    ADD CONSTRAINT disputes_assigned_to_fkey FOREIGN KEY (assigned_to) REFERENCES public.users(id);


--
-- Name: disputes disputes_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.disputes
    ADD CONSTRAINT disputes_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: disputes disputes_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.disputes
    ADD CONSTRAINT disputes_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id);


--
-- Name: disputes disputes_invoice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.disputes
    ADD CONSTRAINT disputes_invoice_id_fkey FOREIGN KEY (invoice_id) REFERENCES public.invoices(id);


--
-- Name: gl_postings gl_postings_invoice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gl_postings
    ADD CONSTRAINT gl_postings_invoice_id_fkey FOREIGN KEY (invoice_id) REFERENCES public.invoices(id);


--
-- Name: gl_postings gl_postings_payment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gl_postings
    ADD CONSTRAINT gl_postings_payment_id_fkey FOREIGN KEY (payment_id) REFERENCES public.payments(id);


--
-- Name: gl_postings gl_postings_posted_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gl_postings
    ADD CONSTRAINT gl_postings_posted_by_fkey FOREIGN KEY (posted_by) REFERENCES public.users(id);


--
-- Name: invoice_line_items invoice_line_items_invoice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_line_items
    ADD CONSTRAINT invoice_line_items_invoice_id_fkey FOREIGN KEY (invoice_id) REFERENCES public.invoices(id) ON DELETE CASCADE;


--
-- Name: invoices invoices_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: invoices invoices_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id) ON DELETE RESTRICT;


--
-- Name: invoices invoices_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.invoice_templates(id);


--
-- Name: notifications notifications_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id);


--
-- Name: notifications notifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: payment_allocations payment_allocations_invoice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_allocations
    ADD CONSTRAINT payment_allocations_invoice_id_fkey FOREIGN KEY (invoice_id) REFERENCES public.invoices(id) ON DELETE RESTRICT;


--
-- Name: payment_allocations payment_allocations_payment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_allocations
    ADD CONSTRAINT payment_allocations_payment_id_fkey FOREIGN KEY (payment_id) REFERENCES public.payments(id) ON DELETE CASCADE;


--
-- Name: payments payments_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id) ON DELETE RESTRICT;


--
-- Name: payments payments_recorded_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_recorded_by_fkey FOREIGN KEY (recorded_by) REFERENCES public.users(id);


--
-- Name: recurring_invoices recurring_invoices_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recurring_invoices
    ADD CONSTRAINT recurring_invoices_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id);


--
-- Name: recurring_invoices recurring_invoices_template_invoice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recurring_invoices
    ADD CONSTRAINT recurring_invoices_template_invoice_id_fkey FOREIGN KEY (template_invoice_id) REFERENCES public.invoices(id);


--
-- PostgreSQL database dump complete
--

