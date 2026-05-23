import { Component, Input, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { trigger, transition, style, animate } from '@angular/animations';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { UiMessage } from '../../chat.types';

@Component({
  selector: 'app-chat-message',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './message.component.html',
  styleUrl: './message.component.css',
  animations: [
    trigger('popScale', [
      transition(':enter', [
        style({ transform: 'scale(0.5)', opacity: 0 }),
        animate('200ms cubic-bezier(0.175, 0.885, 0.32, 1.275)', style({ transform: 'scale(1)', opacity: 1 }))
      ])
    ])
  ]
})
export class MessageComponent {
  private readonly sanitizer = inject(DomSanitizer);

  @Input() m!: UiMessage;

  isSourcesExpanded = false;
  copied = false;

  toggleSources() {
    this.isSourcesExpanded = !this.isSourcesExpanded;
  }

  copyToClipboard() {
    navigator.clipboard.writeText(this.m.text);
    this.copied = true;
    setTimeout(() => {
      this.copied = false;
    }, 1500);
  }

  getActiveContent(): SafeHtml {
    let content = this.m.text;
    if (this.m.isTyping) content = this.m.displayedText || '';
    else if (this.m.tabs && this.m.tabs.length > 0) content = this.m.tabs[this.m.activeTabIdx ?? 0].content;
    return this.sanitizer.bypassSecurityTrustHtml(content);
  }
}
