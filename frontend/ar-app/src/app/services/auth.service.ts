import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject, tap } from 'rxjs';
import { environment } from '../../environments/environment';
import { User, AuthToken } from '../models';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private apiUrl = environment.apiUrl;
  private currentUserSubject = new BehaviorSubject<User | null>(null);
  public currentUser$ = this.currentUserSubject.asObservable();

  constructor(private http: HttpClient) {
    const stored = localStorage.getItem('ar_user');
    if (stored) {
      this.currentUserSubject.next(JSON.parse(stored));
    }
  }

  login(email: string, password: string): Observable<AuthToken> {
    const body = { email, password };
    return this.http.post<AuthToken>(`${this.apiUrl}/auth/login`, body).pipe(
      tap(res => {
        localStorage.setItem('ar_token', res.access_token);
        localStorage.setItem('ar_user', JSON.stringify(res.user));
        this.currentUserSubject.next(res.user);
      })
    );
  }

  logout(): void {
    localStorage.removeItem('ar_token');
    localStorage.removeItem('ar_user');
    this.currentUserSubject.next(null);
  }

  getToken(): string | null {
    return localStorage.getItem('ar_token');
  }

  isAuthenticated(): boolean {
    return !!this.getToken();
  }

  getCurrentUser(): User | null {
    return this.currentUserSubject.value;
  }

  getMe(): Observable<User> {
    return this.http.get<User>(`${this.apiUrl}/auth/me`);
  }
}
