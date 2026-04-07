import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { CreditProfile } from '../models';

@Injectable({ providedIn: 'root' })
export class CreditService {
  private apiUrl = `${environment.apiUrl}/credit`;

  constructor(private http: HttpClient) {}

  getCreditProfiles(): Observable<CreditProfile[]> {
    return this.http.get<CreditProfile[]>(`${this.apiUrl}/profiles`);
  }

  getCreditProfile(customerId: number): Observable<CreditProfile> {
    return this.http.get<CreditProfile>(`${this.apiUrl}/profiles/${customerId}`);
  }

  updateCreditLimit(customerId: number, creditLimit: number, notes?: string): Observable<CreditProfile> {
    return this.http.put<CreditProfile>(`${this.apiUrl}/profiles/${customerId}`, { credit_limit: creditLimit, notes });
  }

  getRiskAssessment(): Observable<CreditProfile[]> {
    return this.http.get<CreditProfile[]>(`${this.apiUrl}/risk-assessment`);
  }

  checkCreditAvailability(customerId: number, amount: number): Observable<{ available: boolean; available_credit: number }> {
    return this.http.post<{ available: boolean; available_credit: number }>(`${this.apiUrl}/check-availability`, {
      customer_id: customerId,
      amount
    });
  }
}
