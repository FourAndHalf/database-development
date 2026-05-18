import { CommonModule } from '@angular/common';
import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../services/auth.service';

@Component({
  standalone: true,
  selector: 'app-auth',
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <div class="auth-container">
      <div class="auth-shell">
        <div class="auth-card">
          <div class="brand">
            <div class="logo">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="brand-icon"><path d="M12 12c-2-2.67-4-4-6-4a4 4 0 1 0 0 8c2 0 4-1.33 6-4Zm0 0c2 2.67 4 4 6 4a4 4 0 0 0 0-8c-2 0-4 1.33-6 4Z"/></svg>
            </div>
            <span class="brand-text">Aether</span>
          </div>

          <h2 class="auth-title">{{ isLogin() ? 'Welcome back' : 'Join Aether' }}</h2>
          <p class="auth-sub">{{ isLogin() ? 'Enter your credentials to access your history.' : 'Create an account to save your research.' }}</p>

          <form (ngSubmit)="submit()" class="auth-form">
            <div class="input-group">
              <label>Email</label>
              <input type="email" name="email" [(ngModel)]="email" placeholder="researcher@aether.ai" required>
            </div>
            <div class="input-group">
              <label>Password</label>
              <input type="password" name="password" [(ngModel)]="password" placeholder="••••••••" required>
            </div>

            <div class="error-msg" *ngIf="error()">{{ error() }}</div>

            <button type="submit" class="submit-btn" [disabled]="busy()">
              {{ busy() ? 'Please wait...' : (isLogin() ? 'Sign In' : 'Register') }}
            </button>
          </form>

          <div class="auth-toggle">
            {{ isLogin() ? "Don't have an account?" : "Already have an account?" }}
            <button (click)="toggleMode()">{{ isLogin() ? 'Register' : 'Sign In' }}</button>
          </div>
          
          <div class="guest-link">
            <a routerLink="/chat">Continue as Guest</a>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .auth-container {
      height: 100vh;
      width: 100vw;
      display: grid;
      place-items: center;
      background: #110e13;
      background-image: 
        radial-gradient(circle at 15% 30%, rgba(220, 90, 60, 0.2) 0%, transparent 45%),
        radial-gradient(circle at 85% 20%, rgba(60, 120, 220, 0.15) 0%, transparent 50%);
    }
    .auth-shell {
      width: 100%;
      max-width: 400px;
      padding: 20px;
    }
    .auth-card {
      background: rgba(255, 255, 255, 0.03);
      backdrop-filter: blur(20px);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 24px;
      padding: 40px;
      box-shadow: 0 20px 50px rgba(0, 0, 0, 0.3);
      text-align: center;
    }
    .brand {
      display: inline-flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 32px;
    }
    .logo { color: #8b5cf6; }
    .brand-text {
      font-weight: 800;
      font-size: 20px;
      letter-spacing: 0.15em;
      text-transform: uppercase;
    }
    .auth-title {
      font-size: 24px;
      font-weight: 700;
      margin-bottom: 8px;
    }
    .auth-sub {
      color: rgba(255, 255, 255, 0.5);
      font-size: 14px;
      margin-bottom: 32px;
    }
    .auth-form {
      display: flex;
      flex-direction: column;
      gap: 20px;
      text-align: left;
    }
    .input-group label {
      display: block;
      font-size: 12px;
      font-weight: 600;
      color: rgba(255, 255, 255, 0.4);
      text-transform: uppercase;
      margin-bottom: 8px;
      margin-left: 4px;
    }
    .input-group input {
      width: 100%;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 12px;
      padding: 12px 16px;
      color: white;
      font-size: 15px;
      transition: all 0.2s ease;
    }
    .input-group input:focus {
      background: rgba(255, 255, 255, 0.08);
      border-color: #8b5cf6;
    }
    .submit-btn {
      background: #8b5cf6;
      color: white;
      font-weight: 600;
      padding: 14px;
      border-radius: 12px;
      cursor: pointer;
      margin-top: 8px;
      transition: all 0.2s ease;
    }
    .submit-btn:hover { background: #7c3aed; transform: translateY(-1px); }
    .submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }
    
    .error-msg {
      color: #ef4444;
      font-size: 13px;
      text-align: center;
      background: rgba(239, 68, 68, 0.1);
      padding: 8px;
      border-radius: 8px;
    }

    .auth-toggle {
      margin-top: 24px;
      font-size: 14px;
      color: rgba(255, 255, 255, 0.5);
    }
    .auth-toggle button {
      color: #8b5cf6;
      font-weight: 600;
      background: none;
      border: none;
      cursor: pointer;
      margin-left: 4px;
    }
    .guest-link {
      margin-top: 16px;
    }
    .guest-link a {
      font-size: 13px;
      color: rgba(255, 255, 255, 0.3);
      text-decoration: none;
    }
    .guest-link a:hover { color: white; }
  `]
})
export class AuthComponent {
  isLogin = signal(true);
  busy = signal(false);
  error = signal('');

  email = '';
  password = '';

  constructor(
    private readonly auth: AuthService,
    private readonly router: Router
  ) {}

  toggleMode() {
    this.isLogin.set(!this.isLogin());
    this.error.set('');
  }

  async submit() {
    if (!this.email || !this.password) return;
    
    this.busy.set(true);
    this.error.set('');

    const obs = this.isLogin() 
      ? this.auth.login({ email: this.email, password: this.password })
      : this.auth.register({ email: this.email, password: this.password });

    obs.subscribe({
      next: () => {
        this.router.navigate(['/chat']);
      },
      error: (err) => {
        this.busy.set(false);
        this.error.set(err.error?.error || 'Authentication failed');
      }
    });
  }
}
