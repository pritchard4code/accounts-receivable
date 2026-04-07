import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { HttpClientModule, HTTP_INTERCEPTORS } from '@angular/common/http';
import { ReactiveFormsModule, FormsModule } from '@angular/forms';

// Angular Material
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatSortModule } from '@angular/material/sort';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatDialogModule } from '@angular/material/dialog';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatMenuModule } from '@angular/material/menu';
import { MatTabsModule } from '@angular/material/tabs';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatRadioModule } from '@angular/material/radio';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatDividerModule } from '@angular/material/divider';
import { MatBadgeModule } from '@angular/material/badge';

// Charts
import { NgChartsModule } from 'ng2-charts';

// Routing & Interceptors
import { AppRoutingModule } from './app-routing.module';
import { AuthInterceptor } from './interceptors/auth.interceptor';

// Components
import { AppComponent } from './app.component';
import { LoginComponent } from './components/login/login.component';
import { ShellComponent } from './components/shell/shell.component';
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
import { InvoiceDialogComponent } from './components/invoice-dialog/invoice-dialog.component';

const MATERIAL_MODULES = [
  MatToolbarModule, MatSidenavModule, MatListModule, MatIconModule, MatButtonModule,
  MatCardModule, MatTableModule, MatPaginatorModule, MatSortModule, MatFormFieldModule,
  MatInputModule, MatSelectModule, MatDatepickerModule, MatNativeDateModule, MatDialogModule,
  MatSnackBarModule, MatProgressSpinnerModule, MatProgressBarModule, MatChipsModule,
  MatTooltipModule, MatMenuModule, MatTabsModule, MatCheckboxModule, MatRadioModule,
  MatSlideToggleModule, MatAutocompleteModule, MatDividerModule, MatBadgeModule
];

@NgModule({
  declarations: [
    AppComponent,
    LoginComponent,
    ShellComponent,
    DashboardComponent,
    InvoicesComponent,
    InvoiceFormComponent,
    InvoiceDetailComponent,
    PaymentsComponent,
    PaymentFormComponent,
    CollectionsComponent,
    CreditComponent,
    DisputesComponent,
    ReportsComponent,
    CustomersComponent,
    InvoiceDialogComponent,
  ],
  imports: [
    BrowserModule,
    BrowserAnimationsModule,
    HttpClientModule,
    ReactiveFormsModule,
    FormsModule,
    AppRoutingModule,
    NgChartsModule,
    ...MATERIAL_MODULES,
  ],
  providers: [
    { provide: HTTP_INTERCEPTORS, useClass: AuthInterceptor, multi: true }
  ],
  bootstrap: [AppComponent]
})
export class AppModule {}
