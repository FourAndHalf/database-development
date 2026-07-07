import { Injectable, signal } from '@angular/core';

export interface ConfirmRequest {
  message: string;
  title?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
}

interface ConfirmState extends ConfirmRequest {
  resolve: (result: boolean) => void;
}

@Injectable({ providedIn: 'root' })
export class ConfirmDialogService {
  readonly request = signal<ConfirmState | null>(null);

  confirm(message: string, options: Omit<ConfirmRequest, 'message'> = {}): Promise<boolean> {
    return new Promise<boolean>(resolve => {
      this.request.set({ message, ...options, resolve });
    });
  }

  resolve(result: boolean) {
    this.request()?.resolve(result);
    this.request.set(null);
  }
}
