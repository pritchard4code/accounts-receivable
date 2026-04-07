import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { Invoice, InvoiceCreate, PaginatedResponse, InvoiceFilters, AgingReport } from '../models';

@Injectable({ providedIn: 'root' })
export class InvoiceService {
  private apiUrl = `${environment.apiUrl}/invoices`;

  constructor(private http: HttpClient) {}

  getInvoices(filters: InvoiceFilters = {}): Observable<PaginatedResponse<Invoice>> {
    let params = new HttpParams();
    if (filters.status) params = params.set('status', filters.status);
    if (filters.customer_id) params = params.set('customer_id', filters.customer_id.toString());
    if (filters.date_from) params = params.set('date_from', filters.date_from);
    if (filters.date_to) params = params.set('date_to', filters.date_to);
    params = params.set('page', (filters.page || 1).toString());
    params = params.set('size', (filters.size || 25).toString());
    return this.http.get<PaginatedResponse<Invoice>>(this.apiUrl, { params });
  }

  getInvoice(id: number): Observable<Invoice> {
    return this.http.get<Invoice>(`${this.apiUrl}/${id}`);
  }

  createInvoice(data: InvoiceCreate): Observable<Invoice> {
    return this.http.post<Invoice>(this.apiUrl, data);
  }

  updateInvoice(id: number, data: Partial<Invoice>): Observable<Invoice> {
    return this.http.put<Invoice>(`${this.apiUrl}/${id}`, data);
  }

  voidInvoice(id: number): Observable<Invoice> {
    return this.http.delete<Invoice>(`${this.apiUrl}/${id}`);
  }

  sendInvoice(id: number): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(`${this.apiUrl}/${id}/send`, {});
  }

  downloadPdf(id: number): Observable<Blob> {
    return this.http.get(`${this.apiUrl}/${id}/pdf`, { responseType: 'blob' });
  }

  getAgingReport(asOfDate?: string): Observable<AgingReport> {
    let params = new HttpParams();
    if (asOfDate) params = params.set('as_of_date', asOfDate);
    return this.http.get<AgingReport>(`${this.apiUrl}/aging`, { params });
  }
}
