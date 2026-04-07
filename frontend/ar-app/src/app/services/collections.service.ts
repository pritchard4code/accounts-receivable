import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { CollectionItem, DunningRule, Invoice } from '../models';

@Injectable({ providedIn: 'root' })
export class CollectionsService {
  private apiUrl = `${environment.apiUrl}/collections`;

  constructor(private http: HttpClient) {}

  getCollectionQueue(): Observable<CollectionItem[]> {
    return this.http.get<CollectionItem[]>(`${this.apiUrl}/queue`);
  }

  getOverdueInvoices(): Observable<Invoice[]> {
    return this.http.get<Invoice[]>(`${this.apiUrl}/overdue`);
  }

  runDunning(): Observable<{ message: string; processed: number }> {
    return this.http.post<{ message: string; processed: number }>(`${this.apiUrl}/dunning/run`, {});
  }

  sendReminder(customerId: number): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(`${this.apiUrl}/reminders`, { customer_id: customerId });
  }

  getDunningRules(): Observable<DunningRule[]> {
    return this.http.get<DunningRule[]>(`${this.apiUrl}/dunning-rules`);
  }

  createDunningRule(data: Partial<DunningRule>): Observable<DunningRule> {
    return this.http.post<DunningRule>(`${this.apiUrl}/dunning-rules`, data);
  }

  updateDunningRule(id: number, data: Partial<DunningRule>): Observable<DunningRule> {
    return this.http.put<DunningRule>(`${this.apiUrl}/dunning-rules/${id}`, data);
  }
}
