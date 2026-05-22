import { Routes } from '@angular/router';
import { ChatPageComponent } from './pages/chat/chat-page.component';
import { AuthComponent } from './pages/auth/auth-page.component';
import { ExplorePageComponent } from './pages/explore/explore-page.component';

export const routes: Routes = [
  { path: '', redirectTo: 'chat', pathMatch: 'full' },
  { path: 'chat', component: ChatPageComponent },
  { path: 'auth', component: AuthComponent },
  { path: 'explore', component: ExplorePageComponent }
];

