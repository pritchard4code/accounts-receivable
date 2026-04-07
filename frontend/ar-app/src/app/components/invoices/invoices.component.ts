import { Component, OnInit, ViewChild } from '@angular/core';
import { MatPaginator, PageEvent } from '@angular/material/paginator';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatDialog } from '@angular/material/dialog';
import { Router } from '@angular/router';
import { InvoiceService } from '../../services/invoice.service';
import { CustomerService } from '../../services/customer.service';
import { Invoice, Customer, InvoiceFilters } from '../../models';
import { InvoiceDialogComponent } from '../invoice-dialog/invoice-dialog.component';

@Component({
  selector: 'app-invoices',
  templateUrl: './invoices.component.html',
  styleUrls: ['./invoices.component.scss']
})
export class InvoicesComponent implements OnInit {
  @ViewChild(MatPaginator) paginator!: MatPaginator;

  invoices: Invoice[] = [];
  customers: Customer[] = [];
  total = 0;
  loading = false;

  filters: InvoiceFilters = { page: 1, size: 25 };

  statusOptions = [
    { value: '', label: 'All Statuses' },
    { value: 'draft', label: 'Draft' },
    { value: 'sent', label: 'Sent' },
    { value: 'viewed', label: 'Viewed' },
    { value: 'partial', label: 'Partial' },
    { value: 'paid', label: 'Paid' },
    { value: 'overdue', label: 'Overdue' },
    { value: 'void', label: 'Void' },
    { value: 'disputed', label: 'Disputed' },
  ];

  displayedColumns = ['invoice_number', 'customer_name', 'invoice_date', 'due_date', 'total_amount', 'balance_due', 'status', 'actions'];

  constructor(
    private invoiceService: InvoiceService,
    private customerService: CustomerService,
    private snackBar: MatSnackBar,
    private router: Router,
    private dialog: MatDialog
  ) {}

  ngOnInit(): void {
    this.loadInvoices();
    this.loadCustomers();
  }

  loadInvoices(): void {
    this.loading = true;
    this.invoiceService.getInvoices(this.filters).subscribe({
      next: (res) => {
        this.invoices = res.items;
        this.total = res.total;
        this.loading = false;
      },
      error: () => { this.loading = false; }
    });
  }

  loadCustomers(): void {
    this.customerService.getCustomers('', 1, 200).subscribe({
      next: (res) => { this.customers = res.items; },
      error: () => {}
    });
  }

  onFilterChange(): void {
    this.filters.page = 1;
    this.loadInvoices();
  }

  onPage(event: PageEvent): void {
    this.filters.page = event.pageIndex + 1;
    this.filters.size = event.pageSize;
    this.loadInvoices();
  }

  viewInvoice(id: number): void {
    const ref = this.dialog.open(InvoiceDialogComponent, {
      data: { invoiceId: id },
      width: '900px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      panelClass: 'invoice-dialog-panel'
    });
    ref.afterClosed().subscribe(updated => {
      if (updated) this.loadInvoices();
    });
  }

  editInvoice(id: number): void {
    this.viewInvoice(id);
  }

  sendInvoice(inv: Invoice): void {
    this.invoiceService.sendInvoice(inv.id).subscribe({
      next: () => {
        this.snackBar.open(`Invoice ${inv.invoice_number} sent successfully`, 'Close', { duration: 3000, panelClass: 'success-snack' });
        this.loadInvoices();
      },
      error: () => this.snackBar.open('Failed to send invoice', 'Close', { duration: 3000, panelClass: 'error-snack' })
    });
  }

  downloadPdf(inv: Invoice): void {
    this.invoiceService.downloadPdf(inv.id).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${inv.invoice_number}.pdf`;
        a.click();
        window.URL.revokeObjectURL(url);
      },
      error: () => this.snackBar.open('PDF generation failed', 'Close', { duration: 3000, panelClass: 'error-snack' })
    });
  }

  voidInvoice(inv: Invoice): void {
    if (!confirm(`Void invoice ${inv.invoice_number}? This cannot be undone.`)) return;
    this.invoiceService.voidInvoice(inv.id).subscribe({
      next: () => {
        this.snackBar.open(`Invoice ${inv.invoice_number} voided`, 'Close', { duration: 3000, panelClass: 'success-snack' });
        this.loadInvoices();
      },
      error: () => this.snackBar.open('Failed to void invoice', 'Close', { duration: 3000, panelClass: 'error-snack' })
    });
  }

  formatCurrency(val: number): string {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val || 0);
  }

  canSend(inv: Invoice): boolean {
    return ['draft', 'viewed'].includes(inv.status);
  }

  canVoid(inv: Invoice): boolean {
    return !['void', 'paid'].includes(inv.status);
  }
}
