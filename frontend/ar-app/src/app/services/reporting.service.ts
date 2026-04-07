import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { DashboardKpis, AgingReport, CashTrend, CashFlowForecast } from '../models';

@Injectable({ providedIn: 'root' })
export class ReportingService {
  private apiUrl = `${environment.apiUrl}/reports`;

  constructor(private http: HttpClient) {}

  getDashboardKpis(): Observable<DashboardKpis> {
    return this.http.get<DashboardKpis>(`${this.apiUrl}/dashboard-kpis`);
  }

  getAgingReport(asOfDate?: string): Observable<AgingReport> {
    let params = new HttpParams();
    if (asOfDate) params = params.set('as_of_date', asOfDate);
    return this.http.get<AgingReport>(`${this.apiUrl}/aging`, { params });
  }

  getDso(): Observable<{ dso: number; trend: number[] }> {
    return this.http.get<{ dso: number; trend: number[] }>(`${this.apiUrl}/dso`);
  }

  getCashTrend(months: number = 6): Observable<CashTrend[]> {
    return this.http.get<CashTrend[]>(`${this.apiUrl}/cash-trend`, {
      params: new HttpParams().set('months', months.toString())
    });
  }

  getCashFlowForecast(days: number = 90): Observable<CashFlowForecast> {
    return this.http.get<CashFlowForecast>(`${this.apiUrl}/cash-flow-forecast`, {
      params: new HttpParams().set('days', days.toString())
    });
  }

  getCustomerPaymentHistory(customerId: number): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/customer/${customerId}/payment-history`);
  }

  getCollectorPerformance(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/collector-performance`);
  }
}
