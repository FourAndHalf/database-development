import { Routes } from '@angular/router';
import { ChatPageComponent } from './pages/chat-page.component';
import { AuthComponent } from './pages/auth.component';

export const routes: Routes = [
  { path: '', redirectTo: 'chat', pathMatch: 'full' },
  { path: 'chat', component: ChatPageComponent },
  { path: 'auth', component: AuthComponent }
];

