import { Component, Inject, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, FormArray, Validators } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { InvoiceService } from '../../services/invoice.service';
import { CustomerService } from '../../services/customer.service';
import { RefService } from '../../services/ref.service';
import { Invoice, Customer } from '../../models';

export interface InvoiceDialogData {
  invoiceId: number;
}

@Component({
  selector: 'app-invoice-dialog',
  templateUrl: './invoice-dialog.component.html',
  styleUrls: ['./invoice-dialog.component.scss']
})
export class InvoiceDialogComponent implements OnInit {
  invoice: Invoice | null = null;
  customers: Customer[] = [];
  form!: FormGroup;
  loading = true;
  saving = false;
  editMode = false;

  statusOptions: { value: string; label: string }[] = [];

  constructor(
    private fb: FormBuilder,
    private invoiceService: InvoiceService,
    private customerService: CustomerService,
    private refService: RefService,
    private snackBar: MatSnackBar,
    public dialogRef: MatDialogRef<InvoiceDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: InvoiceDialogData
  ) {}

  ngOnInit(): void {
    this.refService.getStatuses().subscribe({
      next: (statuses) => {
        this.statusOptions = statuses.map(s => ({
          value: s.status_nm.toLowerCase(),
          label: s.status_nm.charAt(0) + s.status_nm.slice(1).toLowerCase()
        }));
      },
      error: () => {}
    });

    this.customerService.getCustomers('', 1, 200).subscribe({
      next: (res) => { this.customers = res.items; },
      error: () => {}
    });

    this.invoiceService.getInvoice(this.data.invoiceId).subscribe({
      next: (inv) => {
        this.invoice = inv;
        this.buildForm(inv);
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.snackBar.open('Failed to load invoice', 'Close', { duration: 3000, panelClass: 'error-snack' });
      }
    });
  }

  buildForm(inv: Invoice): void {
    this.form = this.fb.group({
      customer_id: [inv.customer_id, Validators.required],
      invoice_date: [inv.invoice_date, Validators.required],
      due_date: [inv.due_date, Validators.required],
      status: [inv.status, Validators.required],
      currency: [inv.currency, Validators.required],
      plan_id: [inv.plan_id || '', Validators.maxLength(16)],
      notes: [inv.notes || ''],
      line_items: this.fb.array(
        (inv.line_items || []).map(li => this.fb.group({
          id: [li.id],
          description: [li.description, Validators.required],
          quantity: [li.quantity, [Validators.required, Validators.min(0.01)]],
          unit_price: [li.unit_price, [Validators.required, Validators.min(0)]],
          tax_rate: [li.tax_rate ?? 0, [Validators.required, Validators.min(0)]],
          total_price: [li.total_price]
        }))
      )
    });
  }

  get lineItems(): FormArray {
    return this.form.get('line_items') as FormArray;
  }

  addLineItem(): void {
    this.lineItems.push(this.fb.group({
      id: [null],
      description: ['', Validators.required],
      quantity: [1, [Validators.required, Validators.min(0.01)]],
      unit_price: [0, [Validators.required, Validators.min(0)]],
      tax_rate: [0, [Validators.required, Validators.min(0)]],
      total_price: [0]
    }));
  }

  removeLineItem(index: number): void {
    this.lineItems.removeAt(index);
  }

  recalcLine(index: number): void {
    const group = this.lineItems.at(index);
    const qty = +group.get('quantity')!.value || 0;
    const price = +group.get('unit_price')!.value || 0;
    const tax = +group.get('tax_rate')!.value || 0;
    const total = qty * price * (1 + tax / 100);
    group.get('total_price')!.setValue(+total.toFixed(2), { emitEvent: false });
  }

  get computedSubtotal(): number {
    return this.lineItems.controls.reduce((sum, g) => {
      const qty = +g.get('quantity')!.value || 0;
      const price = +g.get('unit_price')!.value || 0;
      return sum + qty * price;
    }, 0);
  }

  get computedTax(): number {
    return this.lineItems.controls.reduce((sum, g) => {
      const qty = +g.get('quantity')!.value || 0;
      const price = +g.get('unit_price')!.value || 0;
      const tax = +g.get('tax_rate')!.value || 0;
      return sum + qty * price * (tax / 100);
    }, 0);
  }

  get computedTotal(): number {
    return this.computedSubtotal + this.computedTax;
  }

  toggleEdit(): void {
    this.editMode = !this.editMode;
    if (!this.editMode && this.invoice) {
      this.buildForm(this.invoice);
    }
  }

  save(): void {
    if (this.form.invalid) return;
    this.saving = true;
    const payload = {
      ...this.form.value,
      line_items: this.lineItems.value.map((li: any) => ({
        ...li,
        total_price: +(
          (+li.quantity) * (+li.unit_price) * (1 + (+li.tax_rate) / 100)
        ).toFixed(2)
      }))
    };
    this.invoiceService.updateInvoice(this.data.invoiceId, payload).subscribe({
      next: (updated) => {
        this.saving = false;
        this.editMode = false;
        this.invoice = updated;
        this.buildForm(updated);
        this.snackBar.open('Invoice saved successfully', 'Close', { duration: 3000, panelClass: 'success-snack' });
        this.dialogRef.close(updated);
      },
      error: () => {
        this.saving = false;
        this.snackBar.open('Failed to save invoice', 'Close', { duration: 3000, panelClass: 'error-snack' });
      }
    });
  }

  cancel(): void {
    this.dialogRef.close();
  }

  formatCurrency(val: number): string {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val || 0);
  }
}
