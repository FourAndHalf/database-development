import { Component, ElementRef, EventEmitter, Input, Output, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-chat-composer',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './composer.component.html',
  styleUrl: './composer.component.css'
})
export class ComposerComponent {
  @ViewChild('inputEl', { static: false }) private readonly inputEl?: ElementRef<HTMLTextAreaElement>;

  @Input() isBottom = false;
  @Input() draft = '';
  @Input() busy = false;

  @Output() draftChange = new EventEmitter<string>();
  @Output() send = new EventEmitter<void>();

  suggestion = '';

  onDraftChange(val: string) {
    this.draftChange.emit(val);
    const match = val.match(/(^|\s)(@[wW]?[eE]?[bB]?[-\s]?[sS]?[eE]?[aA]?[rR]?[cC]?[hH]?)$/);
    if (match) {
      const typed = match[2].toLowerCase();
      if ('@web-search'.startsWith(typed) && typed !== '@web-search') {
        this.suggestion = '@web-search'.substring(typed.length);
      } else {
        this.suggestion = '';
      }
    } else {
      this.suggestion = '';
    }
  }

  onEnter(e: Event) {
    const ke = e as KeyboardEvent;
    
    if (ke.key === 'Tab' && this.suggestion) {
      ke.preventDefault();
      this.draftChange.emit(this.draft + this.suggestion + ' ');
      this.suggestion = '';
      return;
    }

    if (ke.key === 'Enter') {
      if (ke.shiftKey) return;
      ke.preventDefault();
      this.send.emit();
    }
  }

  public focusInput() {
    this.inputEl?.nativeElement.focus();
  }

  onSubmit() {
    if (!this.busy && this.draft.trim()) {
      this.send.emit();
    }
  }
}
