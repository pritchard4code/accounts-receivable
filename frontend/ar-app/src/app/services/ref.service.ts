import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, shareReplay } from 'rxjs';
import { environment } from '../../environments/environment';
import { RefStatus } from '../models';

@Injectable({ providedIn: 'root' })
export class RefService {
  private apiUrl = `${environment.apiUrl}/ref`;
  private statuses$?: Observable<RefStatus[]>;

  constructor(private http: HttpClient) {}

  getStatuses(): Observable<RefStatus[]> {
    if (!this.statuses$) {
      this.statuses$ = this.http.get<RefStatus[]>(`${this.apiUrl}/statuses`).pipe(shareReplay(1));
    }
    return this.statuses$;
  }
}
