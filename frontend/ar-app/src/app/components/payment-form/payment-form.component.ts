import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { PaymentService } from '../../services/payment.service';
import { CustomerService } from '../../services/customer.service';
import { InvoiceService } from '../../services/invoice.service';
import { Customer, Invoice } from '../../models';

@Component({
  selector: 'app-payment-form',
  templateUrl: './payment-form.component.html',
  styleUrls: ['./payment-form.component.scss']
})
export class PaymentFormComponent implements OnInit {
  form!: FormGroup;
  customers: Customer[] = [];
  openInvoices: Invoice[] = [];
  saving = false;

  paymentMethods = [
    { value: 'credit_card', label: 'Credit Card' },
    { value: 'debit_card', label: 'Debit Card' },
    { value: 'ach', label: 'ACH / EFT' },
    { value: 'wire', label: 'Wire Transfer' },
    { value: 'check', label: 'Check' },
    { value: 'digital_wallet', label: 'Digital Wallet' },
    { value: 'other', label: 'Other' },
  ];

  constructor(
    private fb: FormBuilder,
    private paymentService: PaymentService,
    private customerService: CustomerService,
    private invoiceService: InvoiceService,
    private route: ActivatedRoute,
    private router: Router,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    const today = new Date().toISOString().split('T')[0];
    const invoiceId = this.route.snapshot.queryParamMap.get('invoice_id');

    this.form = this.fb.group({
      customer_id: [null, Validators.required],
      payment_date: [today, Validators.required],
      amount: [null, [Validators.required, Validators.min(0.01)]],
      payment_method: ['ach', Validators.required],
      reference: [''],
      notes: [''],
      auto_apply: [true],
      invoice_id: [invoiceId ? +invoiceId : null]
    });

    this.loadCustomers();

    this.form.get('customer_id')?.valueChanges.subscribe(customerId => {
      if (customerId) this.loadOpenInvoices(customerId);
    });
  }

  loadCustomers(): void {
    this.customerService.getCustomers('', 1, 200).subscribe({
      next: (res) => { this.customers = res.items; }
    });
  }

  loadOpenInvoices(customerId: number): void {
    this.invoiceService.getInvoices({ customer_id: customerId, status: 'overdue', size: 50 }).subscribe({
      next: (res) => { this.openInvoices = res.items; }
    });
  }

  save(): void {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    this.saving = true;
    const data = { ...this.form.value };

    this.paymentService.createPayment(data).subscribe({
      next: (payment) => {
        if (data.auto_apply) {
          this.paymentService.autoApply(payment.id).subscribe();
        } else if (data.invoice_id) {
          this.paymentService.applyPayment(payment.id, data.invoice_id, data.amount).subscribe();
        }
        this.snackBar.open('Payment recorded successfully', 'Close', { duration: 3000, panelClass: 'success-snack' });
        this.router.navigate(['/payments']);
      },
      error: () => {
        this.saving = false;
        this.snackBar.open('Failed to record payment', 'Close', { duration: 3000, panelClass: 'error-snack' });
      }
    });
  }

  formatCurrency(val: number): string {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val || 0);
  }

  get totalOpenBalance(): number {
    return this.openInvoices.reduce((s, i) => s + i.balance_due, 0);
  }
}
