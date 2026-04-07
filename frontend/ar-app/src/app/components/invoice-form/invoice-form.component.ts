import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, FormArray, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { InvoiceService } from '../../services/invoice.service';
import { CustomerService } from '../../services/customer.service';
import { Customer } from '../../models';

@Component({
  selector: 'app-invoice-form',
  templateUrl: './invoice-form.component.html',
  styleUrls: ['./invoice-form.component.scss']
})
export class InvoiceFormComponent implements OnInit {
  form!: FormGroup;
  customers: Customer[] = [];
  loading = false;
  saving = false;
  isEdit = false;
  invoiceId?: number;

  paymentTerms = [
    { value: 'NET_15', label: 'Net 15' },
    { value: 'NET_30', label: 'Net 30' },
    { value: 'NET_45', label: 'Net 45' },
    { value: 'NET_60', label: 'Net 60' },
    { value: 'DUE_ON_RECEIPT', label: 'Due on Receipt' },
  ];

  taxRates = [0, 5, 8, 8.5, 10, 12, 15];

  constructor(
    private fb: FormBuilder,
    private invoiceService: InvoiceService,
    private customerService: CustomerService,
    private route: ActivatedRoute,
    private router: Router,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.buildForm();
    this.loadCustomers();

    const id = this.route.snapshot.paramMap.get('id');
    if (id && id !== 'new') {
      this.isEdit = true;
      this.invoiceId = +id;
      this.loadInvoice(this.invoiceId);
    } else {
      this.addLineItem();
    }
  }

  buildForm(): void {
    const today = new Date().toISOString().split('T')[0];
    const due = new Date(Date.now() + 30 * 24 * 3600000).toISOString().split('T')[0];

    this.form = this.fb.group({
      customer_id: [null, Validators.required],
      invoice_date: [today, Validators.required],
      due_date: [due, Validators.required],
      currency: ['USD'],
      notes: [''],
      line_items: this.fb.array([])
    });
  }

  get lineItems(): FormArray {
    return this.form.get('line_items') as FormArray;
  }

  addLineItem(): void {
    this.lineItems.push(this.fb.group({
      description: ['', Validators.required],
      quantity: [1, [Validators.required, Validators.min(0.01)]],
      unit_price: [0, [Validators.required, Validators.min(0)]],
      tax_rate: [0],
      total_price: [{ value: 0, disabled: true }]
    }));
  }

  removeLineItem(index: number): void {
    this.lineItems.removeAt(index);
  }

  updateLineTotal(index: number): void {
    const item = this.lineItems.at(index);
    const qty = +item.get('quantity')?.value || 0;
    const price = +item.get('unit_price')?.value || 0;
    item.get('total_price')?.setValue((qty * price).toFixed(2));
  }

  get subtotal(): number {
    return this.lineItems.controls.reduce((sum, item) => {
      const qty = +item.get('quantity')?.value || 0;
      const price = +item.get('unit_price')?.value || 0;
      return sum + qty * price;
    }, 0);
  }

  get taxTotal(): number {
    return this.lineItems.controls.reduce((sum, item) => {
      const qty = +item.get('quantity')?.value || 0;
      const price = +item.get('unit_price')?.value || 0;
      const rate = +item.get('tax_rate')?.value || 0;
      return sum + (qty * price * rate / 100);
    }, 0);
  }

  get grandTotal(): number {
    return this.subtotal + this.taxTotal;
  }

  loadCustomers(): void {
    this.customerService.getCustomers('', 1, 200).subscribe({
      next: (res) => { this.customers = res.items; }
    });
  }

  loadInvoice(id: number): void {
    this.loading = true;
    this.invoiceService.getInvoice(id).subscribe({
      next: (inv) => {
        this.form.patchValue({
          customer_id: inv.customer_id,
          invoice_date: inv.invoice_date,
          due_date: inv.due_date,
          currency: inv.currency,
          notes: inv.notes
        });
        if (inv.line_items) {
          inv.line_items.forEach(li => {
            this.lineItems.push(this.fb.group({
              description: [li.description, Validators.required],
              quantity: [li.quantity, [Validators.required, Validators.min(0.01)]],
              unit_price: [li.unit_price, [Validators.required, Validators.min(0)]],
              tax_rate: [li.tax_rate],
              total_price: [{ value: li.total_price, disabled: true }]
            }));
          });
        }
        this.loading = false;
      },
      error: () => { this.loading = false; this.router.navigate(['/invoices']); }
    });
  }

  save(sendNow = false): void {
    if (this.form.invalid || this.lineItems.length === 0) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving = true;
    const data = {
      ...this.form.value,
      line_items: this.lineItems.controls.map(c => ({
        description: c.get('description')?.value,
        quantity: +c.get('quantity')?.value,
        unit_price: +c.get('unit_price')?.value,
        tax_rate: +c.get('tax_rate')?.value,
        total_price: +c.get('quantity')?.value * +c.get('unit_price')?.value
      }))
    };

    const op = this.isEdit
      ? this.invoiceService.updateInvoice(this.invoiceId!, data)
      : this.invoiceService.createInvoice(data);

    op.subscribe({
      next: (inv) => {
        if (sendNow) {
          this.invoiceService.sendInvoice(inv.id).subscribe();
        }
        this.snackBar.open(`Invoice ${this.isEdit ? 'updated' : 'created'} successfully`, 'Close', { duration: 3000, panelClass: 'success-snack' });
        this.router.navigate(['/invoices', inv.id]);
      },
      error: () => {
        this.saving = false;
        this.snackBar.open('Failed to save invoice', 'Close', { duration: 3000, panelClass: 'error-snack' });
      }
    });
  }

  formatCurrency(val: number): string {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val || 0);
  }
}
