import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { trigger, transition, style, animate } from '@angular/animations';
import { ConfirmDialogService } from '../../services/confirm-dialog.service';

@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (dialog.request(); as req) {
      <div class="backdrop" @fadeInOut (click)="dialog.resolve(false)">
        <div class="dialog" [class.danger]="req.danger" @popInOut (click)="$event.stopPropagation()">
          @if (req.title) {
            <h3 class="title">{{ req.title }}</h3>
          }
          <p class="message">{{ req.message }}</p>
          <div class="actions">
            <button class="cancel" (click)="dialog.resolve(false)">{{ req.cancelLabel ?? 'Cancel' }}</button>
            <button class="confirm" (click)="dialog.resolve(true)">{{ req.confirmLabel ?? 'Confirm' }}</button>
          </div>
        </div>
      </div>
    }
  `,
  styles: [`
    .backdrop {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.55);
      backdrop-filter: blur(4px);
      display: grid;
      place-items: center;
      z-index: 10000;
    }
    .dialog {
      background: rgba(24, 22, 26, 0.95);
      backdrop-filter: blur(24px);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 16px;
      padding: 24px;
      width: 360px;
      max-width: calc(100vw - 48px);
      color: rgba(255, 255, 255, 0.95);
      box-shadow: 0 20px 40px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.05);
    }
    .title {
      margin: 0 0 8px;
      font-size: 16px;
      font-weight: 600;
    }
    .message {
      margin: 0 0 20px;
      font-size: 14px;
      line-height: 1.5;
      color: rgba(255, 255, 255, 0.75);
    }
    .actions {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
    }
    .actions button {
      padding: 8px 18px;
      border-radius: 10px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      border: 1px solid rgba(255, 255, 255, 0.1);
      background: rgba(255, 255, 255, 0.06);
      color: rgba(255, 255, 255, 0.9);
      transition: background 0.2s;
    }
    .actions button:hover { background: rgba(255, 255, 255, 0.12); }
    .dialog.danger .confirm {
      background: #ef4444;
      border-color: #ef4444;
      color: white;
    }
    .dialog.danger .confirm:hover { background: #dc2626; }
    .dialog:not(.danger) .confirm {
      background: #3b82f6;
      border-color: #3b82f6;
      color: white;
    }
    .dialog:not(.danger) .confirm:hover { background: #2563eb; }
  `],
  animations: [
    trigger('fadeInOut', [
      transition(':enter', [
        style({ opacity: 0 }),
        animate('150ms ease-out', style({ opacity: 1 }))
      ]),
      transition(':leave', [
        animate('150ms ease-in', style({ opacity: 0 }))
      ])
    ]),
    trigger('popInOut', [
      transition(':enter', [
        style({ transform: 'scale(0.9)', opacity: 0 }),
        animate('180ms cubic-bezier(0.175, 0.885, 0.32, 1.275)', style({ transform: 'scale(1)', opacity: 1 }))
      ]),
      transition(':leave', [
        animate('120ms ease-in', style({ transform: 'scale(0.95)', opacity: 0 }))
      ])
    ])
  ]
})
export class ConfirmDialogComponent {
  protected readonly dialog = inject(ConfirmDialogService);
}
