import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { Payment, PaginatedResponse, PaymentFilters } from '../models';

@Injectable({ providedIn: 'root' })
export class PaymentService {
  private apiUrl = `${environment.apiUrl}/payments`;

  constructor(private http: HttpClient) {}

  getPayments(filters: PaymentFilters = {}): Observable<PaginatedResponse<Payment>> {
    let params = new HttpParams();
    if (filters.status) params = params.set('status', filters.status);
    if (filters.payment_method) params = params.set('payment_method', filters.payment_method);
    if (filters.customer_id) params = params.set('customer_id', filters.customer_id.toString());
    if (filters.date_from) params = params.set('date_from', filters.date_from);
    if (filters.date_to) params = params.set('date_to', filters.date_to);
    params = params.set('page', (filters.page || 1).toString());
    params = params.set('size', (filters.size || 25).toString());
    return this.http.get<PaginatedResponse<Payment>>(this.apiUrl, { params });
  }

  getPayment(id: number): Observable<Payment> {
    return this.http.get<Payment>(`${this.apiUrl}/${id}`);
  }

  createPayment(data: Partial<Payment>): Observable<Payment> {
    return this.http.post<Payment>(this.apiUrl, data);
  }

  applyPayment(paymentId: number, invoiceId: number, amount: number): Observable<Payment> {
    return this.http.post<Payment>(`${this.apiUrl}/${paymentId}/apply`, { invoice_id: invoiceId, amount });
  }

  autoApply(paymentId: number): Observable<Payment> {
    return this.http.post<Payment>(`${this.apiUrl}/${paymentId}/auto-apply`, {});
  }

  refund(paymentId: number, amount: number): Observable<Payment> {
    return this.http.post<Payment>(`${this.apiUrl}/${paymentId}/refund`, { amount });
  }
}
