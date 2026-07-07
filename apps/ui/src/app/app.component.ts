import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { ToastComponent } from './components/toast/toast.component';
import { ConfirmDialogComponent } from './components/confirm-dialog/confirm-dialog.component';
import { BugReportComponent } from './components/bug-report/bug-report.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, ToastComponent, ConfirmDialogComponent, BugReportComponent],
  template: `
    <router-outlet />
    <app-toast></app-toast>
    <app-confirm-dialog></app-confirm-dialog>
    <app-bug-report></app-bug-report>
  `
})
export class AppComponent {}

