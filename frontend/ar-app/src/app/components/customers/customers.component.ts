import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatSnackBar } from '@angular/material/snack-bar';
import { PageEvent } from '@angular/material/paginator';
import { CustomerService } from '../../services/customer.service';
import { Customer } from '../../models';

@Component({
  selector: 'app-customers',
  templateUrl: './customers.component.html',
  styleUrls: ['./customers.component.scss']
})
export class CustomersComponent implements OnInit {
  customers: Customer[] = [];
  total = 0;
  loading = false;
  search = '';
  page = 1;
  size = 25;
  showForm = false;
  editingId: number | null = null;
  saving = false;
  form!: FormGroup;

  displayedColumns = ['customer_number', 'name', 'email', 'phone', 'credit_limit', 'credit_status', 'payment_terms', 'actions'];

  statusOptions = [
    { value: 'active', label: 'Active' },
    { value: 'on_hold', label: 'On Hold' },
    { value: 'suspended', label: 'Suspended' },
    { value: 'closed', label: 'Closed' },
  ];

  paymentTermsOptions = ['NET_15', 'NET_30', 'NET_45', 'NET_60', 'DUE_ON_RECEIPT'];

  constructor(
    private customerService: CustomerService,
    private fb: FormBuilder,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.buildForm();
    this.loadCustomers();
  }

  buildForm(): void {
    this.form = this.fb.group({
      name: ['', Validators.required],
      email: ['', [Validators.required, Validators.email]],
      phone: [''],
      address: [''],
      city: [''],
      state: [''],
      zip: [''],
      country: ['US'],
      currency: ['USD'],
      credit_limit: [10000, [Validators.required, Validators.min(0)]],
      payment_terms: ['NET_30', Validators.required],
      credit_status: ['active', Validators.required],
    });
  }

  loadCustomers(): void {
    this.loading = true;
    this.customerService.getCustomers(this.search, this.page, this.size).subscribe({
      next: (res) => { this.customers = res.items; this.total = res.total; this.loading = false; },
      error: () => { this.loading = false; }
    });
  }

  onPage(event: PageEvent): void {
    this.page = event.pageIndex + 1;
    this.size = event.pageSize;
    this.loadCustomers();
  }

  openAddForm(): void {
    this.editingId = null;
    this.form.reset({ country: 'US', currency: 'USD', credit_limit: 10000, payment_terms: 'NET_30', credit_status: 'active' });
    this.showForm = true;
  }

  editCustomer(customer: Customer): void {
    this.editingId = customer.id;
    this.form.patchValue(customer);
    this.showForm = true;
  }

  save(): void {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    this.saving = true;
    const data = this.form.value;
    const op = this.editingId
      ? this.customerService.updateCustomer(this.editingId, data)
      : this.customerService.createCustomer(data);

    op.subscribe({
      next: () => {
        this.saving = false;
        this.showForm = false;
        this.snackBar.open(`Customer ${this.editingId ? 'updated' : 'created'} successfully`, 'Close', { duration: 3000, panelClass: 'success-snack' });
        this.loadCustomers();
      },
      error: () => {
        this.saving = false;
        this.snackBar.open('Failed to save customer', 'Close', { duration: 3000, panelClass: 'error-snack' });
      }
    });
  }

  formatCurrency(val: number): string {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val || 0);
  }
}
