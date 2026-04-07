export interface User {
  id: number;
  username: string;
  email: string;
  role: 'admin' | 'ar_clerk' | 'collections_specialist' | 'finance_manager' | 'credit_manager' | 'customer';
  is_active: boolean;
  created_at?: string;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Customer {
  id: number;
  customer_number: string;
  name: string;
  email: string;
  phone?: string;
  address?: string;
  city?: string;
  state?: string;
  zip?: string;
  country?: string;
  currency: string;
  language?: string;
  credit_limit: number;
  credit_status: 'active' | 'on_hold' | 'suspended' | 'closed';
  payment_terms: string;
  created_at?: string;
  updated_at?: string;
}

export interface InvoiceLineItem {
  id?: number;
  description: string;
  quantity: number;
  unit_price: number;
  tax_rate: number;
  total_price: number;
}

export interface Invoice {
  id: number;
  invoice_number: string;
  customer_id: number;
  customer_name?: string;
  status: 'draft' | 'sent' | 'viewed' | 'partial' | 'paid' | 'overdue' | 'void' | 'disputed';
  invoice_date: string;
  due_date: string;
  subtotal: number;
  tax_amount: number;
  total_amount: number;
  paid_amount: number;
  balance_due: number;
  currency: string;
  plan_id?: string;
  notes?: string;
  line_items?: InvoiceLineItem[];
  created_at?: string;
  updated_at?: string;
}

export interface InvoiceCreate {
  customer_id: number;
  invoice_date: string;
  due_date: string;
  currency: string;
  notes?: string;
  line_items: Omit<InvoiceLineItem, 'id'>[];
}

export interface Payment {
  id: number;
  payment_number: string;
  customer_id: number;
  customer_name?: string;
  payment_date: string;
  amount: number;
  payment_method: 'credit_card' | 'debit_card' | 'ach' | 'wire' | 'check' | 'digital_wallet' | 'other';
  status: 'pending' | 'applied' | 'partially_applied' | 'unapplied' | 'refunded' | 'void';
  reference?: string;
  gateway_transaction_id?: string;
  notes?: string;
  allocations?: PaymentAllocation[];
  created_at?: string;
}

export interface PaymentAllocation {
  id: number;
  payment_id: number;
  invoice_id: number;
  invoice_number?: string;
  allocated_amount: number;
  created_at?: string;
}

export interface CollectionItem {
  customer_id: number;
  customer_name: string;
  customer_email?: string;
  total_overdue: number;
  days_overdue: number;
  last_contact?: string;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  open_invoices: number;
  overdue_invoices: number;
}

export interface DunningRule {
  id: number;
  name: string;
  days_overdue_min: number;
  days_overdue_max: number;
  action_type: 'email' | 'sms' | 'call' | 'hold' | 'suspend';
  template?: string;
  is_active: boolean;
  created_at?: string;
}

export interface CreditProfile {
  id: number;
  customer_id: number;
  customer_name?: string;
  customer_email?: string;
  credit_limit: number;
  current_balance: number;
  available_credit: number;
  risk_score: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  payment_score: number;
  last_review_date?: string;
  notes?: string;
  updated_at?: string;
}

export interface Dispute {
  id: number;
  dispute_number: string;
  customer_id: number;
  customer_name?: string;
  invoice_id: number;
  invoice_number?: string;
  status: 'open' | 'under_review' | 'resolved' | 'rejected';
  reason: string;
  description?: string;
  amount_disputed: number;
  resolution?: string;
  created_at?: string;
  updated_at?: string;
  resolved_at?: string;
}

export interface DashboardKpis {
  total_receivables: number;
  dso: number;
  overdue_amount: number;
  collection_rate: number;
  current_month_collections: number;
  overdue_count: number;
  total_customers: number;
  invoices_this_month: number;
}

export interface AgingBucket {
  customer_id: number;
  customer_name: string;
  current: number;
  days_1_30: number;
  days_31_60: number;
  days_61_90: number;
  days_over_90: number;
  total: number;
}

export interface AgingReport {
  as_of_date: string;
  buckets: AgingBucket[];
  totals: {
    current: number;
    days_1_30: number;
    days_31_60: number;
    days_61_90: number;
    days_over_90: number;
    total: number;
  };
}

export interface CashTrend {
  month: string;
  collected: number;
  invoiced: number;
}

export interface CashFlowForecast {
  forecast: { date: string; expected_amount: number; cumulative: number }[];
  total_expected: number;
  confidence: number;
}

export interface RefStatus {
  status_id: string;
  status_nm: string;
  status_desc?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface InvoiceFilters {
  status?: string;
  customer_id?: number;
  date_from?: string;
  date_to?: string;
  page?: number;
  size?: number;
}

export interface PaymentFilters {
  status?: string;
  payment_method?: string;
  customer_id?: number;
  date_from?: string;
  date_to?: string;
  page?: number;
  size?: number;
}
