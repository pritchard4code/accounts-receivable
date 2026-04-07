import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { Dispute, PaginatedResponse } from '../models';

@Injectable({ providedIn: 'root' })
export class DisputeService {
  private apiUrl = `${environment.apiUrl}/disputes`;

  constructor(private http: HttpClient) {}

  getDisputes(filters: { status?: string; customer_id?: number; page?: number; size?: number } = {}): Observable<PaginatedResponse<Dispute>> {
    let params = new HttpParams();
    if (filters.status) params = params.set('status', filters.status);
    if (filters.customer_id) params = params.set('customer_id', filters.customer_id.toString());
    params = params.set('page', (filters.page || 1).toString());
    params = params.set('size', (filters.size || 25).toString());
    return this.http.get<PaginatedResponse<Dispute>>(this.apiUrl, { params });
  }

  getDispute(id: number): Observable<Dispute> {
    return this.http.get<Dispute>(`${this.apiUrl}/${id}`);
  }

  createDispute(data: Partial<Dispute>): Observable<Dispute> {
    return this.http.post<Dispute>(this.apiUrl, data);
  }

  updateDisputeStatus(id: number, status: string, resolution?: string): Observable<Dispute> {
    return this.http.put<Dispute>(`${this.apiUrl}/${id}/status`, { status, resolution });
  }
}
