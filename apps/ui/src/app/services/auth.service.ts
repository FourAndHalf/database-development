import { HttpClient } from '@angular/common/http';
import { Injectable, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';

export type AuthResponse = {
  token: string;
  email: string;
  id: string;
};

export type AuthRequest = {
  email: string;
  password?: string;
};

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly tokenKey = 'aether.token';
  private readonly userKey = 'aether.user';

  readonly user = signal<AuthResponse | null>(this.loadUser());
  readonly isAuthenticated = signal<boolean>(!!this.user());

  constructor(private readonly http: HttpClient) {}

  register(req: AuthRequest): Observable<AuthResponse> {
    return this.http.post<AuthResponse>('/v1/auth/register', req).pipe(
      tap(res => this.saveSession(res))
    );
  }

  login(req: AuthRequest): Observable<AuthResponse> {
    return this.http.post<AuthResponse>('/v1/auth/login', req).pipe(
      tap(res => this.saveSession(res))
    );
  }

  logout() {
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.userKey);
    this.user.set(null);
    this.isAuthenticated.set(false);
  }

  getToken(): string | null {
    return localStorage.getItem(this.tokenKey);
  }

  private saveSession(res: AuthResponse) {
    localStorage.setItem(this.tokenKey, res.token);
    localStorage.setItem(this.userKey, JSON.stringify(res));
    this.user.set(res);
    this.isAuthenticated.set(true);
  }

  private loadUser(): AuthResponse | null {
    const data = localStorage.getItem(this.userKey);
    if (!data) return null;
    try {
      return JSON.parse(data);
    } catch {
      return null;
    }
  }
}
