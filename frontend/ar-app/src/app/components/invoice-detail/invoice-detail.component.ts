import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { InvoiceService } from '../../services/invoice.service';
import { PaymentService } from '../../services/payment.service';
import { Invoice, Payment } from '../../models';

@Component({
  selector: 'app-invoice-detail',
  templateUrl: './invoice-detail.component.html',
  styleUrls: ['./invoice-detail.component.scss']
})
export class InvoiceDetailComponent implements OnInit {
  invoice: Invoice | null = null;
  payments: Payment[] = [];
  loading = true;

  lineItemCols = ['description', 'quantity', 'unit_price', 'tax_rate', 'total_price'];
  paymentCols = ['payment_date', 'payment_number', 'payment_method', 'amount', 'status'];

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private invoiceService: InvoiceService,
    private paymentService: PaymentService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    const id = +this.route.snapshot.paramMap.get('id')!;
    this.loadInvoice(id);
    this.loadPayments(id);
  }

  loadInvoice(id: number): void {
    this.loading = true;
    this.invoiceService.getInvoice(id).subscribe({
      next: (inv) => { this.invoice = inv; this.loading = false; },
      error: () => { this.loading = false; this.router.navigate(['/invoices']); }
    });
  }

  loadPayments(invoiceId: number): void {
    this.paymentService.getPayments({ size: 50 }).subscribe({
      next: (res) => {
        this.payments = res.items.filter(p =>
          p.allocations?.some(a => a.invoice_id === invoiceId)
        );
      }
    });
  }

  send(): void {
    if (!this.invoice) return;
    this.invoiceService.sendInvoice(this.invoice.id).subscribe({
      next: () => {
        this.snackBar.open('Invoice sent successfully', 'Close', { duration: 3000, panelClass: 'success-snack' });
        this.loadInvoice(this.invoice!.id);
      },
      error: () => this.snackBar.open('Failed to send invoice', 'Close', { duration: 3000, panelClass: 'error-snack' })
    });
  }

  downloadPdf(): void {
    if (!this.invoice) return;
    this.invoiceService.downloadPdf(this.invoice.id).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${this.invoice!.invoice_number}.pdf`;
        a.click();
        window.URL.revokeObjectURL(url);
      }
    });
  }

  formatCurrency(val: number): string {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val || 0);
  }

  getPaymentMethodLabel(method: string): string {
    const labels: Record<string, string> = {
      credit_card: 'Credit Card', debit_card: 'Debit Card',
      ach: 'ACH', wire: 'Wire Transfer', check: 'Check',
      digital_wallet: 'Digital Wallet', other: 'Other'
    };
    return labels[method] || method;
  }
}
