import { Component, OnInit } from '@angular/core';
import { PageEvent } from '@angular/material/paginator';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Router } from '@angular/router';
import { PaymentService } from '../../services/payment.service';
import { CustomerService } from '../../services/customer.service';
import { Payment, Customer, PaymentFilters } from '../../models';

@Component({
  selector: 'app-payments',
  templateUrl: './payments.component.html',
  styleUrls: ['./payments.component.scss']
})
export class PaymentsComponent implements OnInit {
  payments: Payment[] = [];
  customers: Customer[] = [];
  total = 0;
  loading = false;
  filters: PaymentFilters = { page: 1, size: 25 };

  statusOptions = [
    { value: '', label: 'All Statuses' },
    { value: 'pending', label: 'Pending' },
    { value: 'applied', label: 'Applied' },
    { value: 'partially_applied', label: 'Partially Applied' },
    { value: 'unapplied', label: 'Unapplied' },
    { value: 'refunded', label: 'Refunded' },
  ];

  methodOptions = [
    { value: '', label: 'All Methods' },
    { value: 'credit_card', label: 'Credit Card' },
    { value: 'debit_card', label: 'Debit Card' },
    { value: 'ach', label: 'ACH / EFT' },
    { value: 'wire', label: 'Wire Transfer' },
    { value: 'check', label: 'Check' },
    { value: 'digital_wallet', label: 'Digital Wallet' },
    { value: 'other', label: 'Other' },
  ];

  displayedColumns = ['payment_number', 'customer_name', 'payment_date', 'amount', 'payment_method', 'status', 'reference', 'actions'];

  constructor(
    private paymentService: PaymentService,
    private customerService: CustomerService,
    private snackBar: MatSnackBar,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadPayments();
    this.loadCustomers();
  }

  loadPayments(): void {
    this.loading = true;
    this.paymentService.getPayments(this.filters).subscribe({
      next: (res) => { this.payments = res.items; this.total = res.total; this.loading = false; },
      error: () => { this.loading = false; }
    });
  }

  loadCustomers(): void {
    this.customerService.getCustomers('', 1, 200).subscribe({
      next: (res) => { this.customers = res.items; }
    });
  }

  onFilterChange(): void {
    this.filters.page = 1;
    this.loadPayments();
  }

  onPage(event: PageEvent): void {
    this.filters.page = event.pageIndex + 1;
    this.filters.size = event.pageSize;
    this.loadPayments();
  }

  autoApply(payment: Payment): void {
    this.paymentService.autoApply(payment.id).subscribe({
      next: () => {
        this.snackBar.open('Payment auto-applied successfully', 'Close', { duration: 3000, panelClass: 'success-snack' });
        this.loadPayments();
      },
      error: () => this.snackBar.open('Auto-apply failed', 'Close', { duration: 3000, panelClass: 'error-snack' })
    });
  }

  getMethodLabel(method: string): string {
    return this.methodOptions.find(m => m.value === method)?.label || method;
  }

  formatCurrency(val: number): string {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val || 0);
  }
}
