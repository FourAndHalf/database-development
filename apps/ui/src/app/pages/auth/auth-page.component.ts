import { CommonModule } from '@angular/common';
import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  standalone: true,
  selector: 'app-auth',
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './auth-page.component.html',
  styleUrl: './auth-page.component.css'
})
export class AuthComponent {
  isLogin = signal(true);
  busy = signal(false);
  error = signal('');

  email = '';
  password = '';
  username = '';

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
      : this.auth.register({ email: this.email, password: this.password, username: this.username });

    obs.subscribe({
      next: () => {
        this.router.navigate(['/chat']);
      },
      error: (err: any) => {
        this.busy.set(false);
        this.error.set(err.error?.error || 'Authentication failed');
      }
    });
  }
}
