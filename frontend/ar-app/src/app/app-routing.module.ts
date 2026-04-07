import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AuthGuard } from './guards/auth.guard';
import { ShellComponent } from './components/shell/shell.component';
import { LoginComponent } from './components/login/login.component';
import { DashboardComponent } from './components/dashboard/dashboard.component';
import { InvoicesComponent } from './components/invoices/invoices.component';
import { InvoiceFormComponent } from './components/invoice-form/invoice-form.component';
import { InvoiceDetailComponent } from './components/invoice-detail/invoice-detail.component';
import { PaymentsComponent } from './components/payments/payments.component';
import { PaymentFormComponent } from './components/payment-form/payment-form.component';
import { CollectionsComponent } from './components/collections/collections.component';
import { CreditComponent } from './components/credit/credit.component';
import { DisputesComponent } from './components/disputes/disputes.component';
import { ReportsComponent } from './components/reports/reports.component';
import { CustomersComponent } from './components/customers/customers.component';

const routes: Routes = [
  { path: 'login', component: LoginComponent },
  {
    path: '',
    component: ShellComponent,
    canActivate: [AuthGuard],
    children: [
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
      { path: 'dashboard', component: DashboardComponent },
      { path: 'invoices', component: InvoicesComponent },
      { path: 'invoices/new', component: InvoiceFormComponent },
      { path: 'invoices/:id/edit', component: InvoiceFormComponent },
      { path: 'invoices/:id', component: InvoiceDetailComponent },
      { path: 'payments', component: PaymentsComponent },
      { path: 'payments/new', component: PaymentFormComponent },
      { path: 'collections', component: CollectionsComponent },
      { path: 'credit', component: CreditComponent },
      { path: 'disputes', component: DisputesComponent },
      { path: 'reports', component: ReportsComponent },
      { path: 'customers', component: CustomersComponent },
    ]
  },
  { path: '**', redirectTo: 'dashboard' }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule {}
