import { CommonModule } from '@angular/common';
import { Component, ElementRef, HostListener, ViewChild, afterRenderEffect, computed, effect, signal, OnDestroy, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { trigger, transition, style, animate } from '@angular/animations';
import { AuthService } from '../../services/auth.service';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { ChatApiService, Conversation, Source } from '../../services/chat-api.service';
import { firstValueFrom } from 'rxjs';
import { ToastService } from '../../services/toast.service';

type Role = 'user' | 'assistant';

type Tab = {
  title: string;
  content: string;
};

type UiMessage = {
  id: string;
  role: Role;
  text: string;
  displayedText?: string;
  isTyping?: boolean;
  sources?: Source[];
  latencyMs?: number;
  pending?: boolean;
  tabs?: Tab[];
  activeTabIdx?: number;
  copied?: boolean;
};

@Component({
  standalone: true,
  selector: 'app-chat-page',
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './chat-page.component.html',
  styleUrl: './chat-page.component.css',
  animations: [
    trigger('popScale', [
      transition(':enter', [
        style({ transform: 'scale(0.5)', opacity: 0 }),
        animate('200ms cubic-bezier(0.175, 0.885, 0.32, 1.275)', style({ transform: 'scale(1)', opacity: 1 }))
      ])
    ])
  ]
})
export class ChatPageComponent implements OnDestroy {
  @ViewChild('thread', { static: false }) private readonly threadEl?: ElementRef<HTMLElement>;
  @ViewChild('centerInput', { static: false }) private readonly centerInput?: ElementRef<HTMLTextAreaElement>;
  @ViewChild('bottomInput', { static: false }) private readonly bottomInput?: ElementRef<HTMLTextAreaElement>;

  private readonly api = inject(ChatApiService);
  protected readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly sanitizer = inject(DomSanitizer);
  private readonly toast = inject(ToastService);

  protected draft = '';
  protected suggestion = '';

  private readonly conversationKey = 'db-rag.conversation_id';
  protected readonly conversationId = signal<string>(localStorage.getItem(this.conversationKey) ?? '');
  protected readonly messages = signal<UiMessage[]>([]);
  protected readonly history = signal<Conversation[]>([]);
  protected readonly expandedSourcesByMessageId = signal<Record<string, boolean>>({});
  protected readonly busy = signal(false);
  protected readonly selectedModel = signal<'aether-1.0' | 'aether-2.0'>('aether-2.0');

  constructor() {
    if (this.auth.isAuthenticated()) {
      this.fetchHistory();
    }
    afterRenderEffect(() => this.scrollToBottom());

    // Load conversation if id is in query params
    this.route.paramMap.subscribe(async params => {
      const id = params.get('id');
      if (id) {
        this.conversationId.set(id);
        await this.loadConversation(id);
      }
    });
  }
  
  ngOnDestroy() {
    // Clean up subscriptions if any
  }

  @HostListener('window:keydown', ['$event'])
  onGlobalKeydown(e: KeyboardEvent) {
    const target = e.target as HTMLElement;
    const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable;
    
    if (isInput || e.ctrlKey || e.metaKey || e.altKey || e.key.length > 1) {
      return;
    }

    const input = this.messages().length === 0 ? this.centerInput : this.bottomInput;
    if (input) {
      input.nativeElement.focus();
    }
  }

  onDraftChange(val: string) {
    this.draft = val;
    // Autocomplete logic for @web-search
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

  protected onEnter(e: Event) {
    const ke = e as KeyboardEvent;
    
    if (ke.key === 'Tab' && this.suggestion) {
      ke.preventDefault();
      this.draft += this.suggestion + ' ';
      this.suggestion = '';
      return;
    }

    if (ke.key === 'Enter') {
      if (ke.shiftKey) return;
      ke.preventDefault();
      void this.send();
    }
  }

  protected getActiveContent(m: UiMessage): SafeHtml {
    let content = m.text;
    if (m.isTyping) content = m.displayedText || '';
    else if (m.tabs && m.tabs.length > 0) content = m.tabs[m.activeTabIdx ?? 0].content;
    return this.sanitizer.bypassSecurityTrustHtml(content);
  }

  protected newChat() {
    this.messages.set([]);
    this.conversationId.set('');
    localStorage.removeItem(this.conversationKey);
    this.router.navigate(['/chat']);
  }
  
  protected async fetchHistory() {
    const user = this.auth.user();
    if (!user) return;
    try {
      const history = await firstValueFrom(this.api.getHistory(user.id));
      this.history.set(history);
    } catch (err) {
      console.error('Failed to fetch history:', err);
      this.toast.error('Failed to fetch chat history.');
    }
  }

  protected async loadConversation(id: string) {
    this.messages.set([]);
    this.busy.set(true);
    this.conversationId.set(id);
    localStorage.setItem(this.conversationKey, id);
    this.router.navigate(['/chat', { id }]);

    try {
      const res = await firstValueFrom(this.api.getMessages(id));
      this.messages.set(res.map((m: any) => ({
        id: m.id,
        role: m.role,
        text: m.content,
      })));
    } catch (err) {
      console.error('Failed to load conversation:', err);
      this.toast.error('Failed to load conversation.');
    } finally {
      this.busy.set(false);
    }
  }

  protected async deleteConversation(id: string) {
    if (!confirm('Are you sure you want to delete this chat?')) return;
    const user = this.auth.user();
    if (!user) return;
    try {
      await firstValueFrom(this.api.deleteChat(user.id, id));
      this.history.update(h => h.filter(c => c.id !== id));
      if (this.conversationId() === id) {
        this.newChat();
      }
      this.toast.success('Chat deleted successfully.');
    } catch (err) {
      console.error('Failed to delete chat:', err);
      this.toast.error('Failed to delete chat.');
    }
  }

  logout() {
    this.auth.logout();
    this.router.navigate(['/auth']);
  }

  greeting() {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  }

  prefill(query: string) {
    this.draft = query;
    const input = this.messages().length === 0 ? this.centerInput : this.bottomInput;
    if (input) {
      input.nativeElement.focus();
    }
  }

  toggleSources(messageId: string) {
    this.expandedSourcesByMessageId.update(s => ({ ...s, [messageId]: !s[messageId] }));
  }

  isSourcesExpanded(messageId: string): boolean {
    return this.expandedSourcesByMessageId()[messageId] ?? false;
  }

  copyToClipboard(m: UiMessage) {
    navigator.clipboard.writeText(m.text);
    m.copied = true;
    setTimeout(() => {
      m.copied = false;
      // This is needed to trigger change detection
      this.messages.update(msgs => [...msgs]);
    }, 1500);
  }

  protected async send() {
    const message = this.draft.trim();
    if (!message || this.busy()) return;
    this.draft = '';
    this.busy.set(true);

    const userMsg: UiMessage = { 
      id: crypto.randomUUID(), 
      role: 'user', 
      text: message 
    };

    const assistantId = crypto.randomUUID();
    const assistantMsg: UiMessage = { 
      id: assistantId, 
      role: 'assistant', 
      text: 'Exploring', 
      pending: true 
    };

    this.messages.update((xs) => [...xs, userMsg, assistantMsg]);

    try {
      const res = await firstValueFrom(
        this.api.chat({ 
          conversation_id: this.conversationId() || undefined, 
          message,
          model: this.selectedModel()
        })
      );
      if (!res) throw new Error('no response');
      this.conversationId.set(res.conversation_id);

      let parsedTabs: Tab[] = [];
      let mainText = res.answer;
      try {
        const structured = JSON.parse(res.answer);
        if (structured.main && Array.isArray(structured.tabs)) {
          mainText = structured.main;
          parsedTabs = [{ title: 'Overview', content: structured.main }, ...structured.tabs];
        }
      } catch (e) {
        // Fallback for plain text
      }

      this.messages.update((xs) => xs.map((m) => m.id === assistantId ? { 
        ...m, 
        text: mainText, 
        displayedText: '', 
        isTyping: true, 
        sources: res.sources, 
        latencyMs: res.latency_ms, 
        pending: false, 
        tabs: parsedTabs, 
        activeTabIdx: 0 
      } : m));

      this.simulateTypewriter(assistantId, mainText);
      if (this.auth.isAuthenticated()) void this.fetchHistory();

    } catch (err) {
      this.messages.update((xs) => xs.map((m) => m.id === assistantId ? { ...m, text: 'Failed to synthesize answer.', pending: false } : m));
      this.toast.error('Failed to get an answer from the assistant.');
    } finally {
      this.busy.set(false);
    }
  }

  private scrollToBottom() {
    const el = this.threadEl?.nativeElement;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }

  private simulateTypewriter(messageId: string, text: string) {
    let i = 0;
    const interval = setInterval(() => {
      this.messages.update(xs => xs.map(m => {
        if (m.id === messageId) {
          return { ...m, displayedText: text.substring(0, i) };
        }
        return m;
      }));
      i++;
      if (i > text.length) {
        clearInterval(interval);
        this.messages.update(xs => xs.map(m => {
          if (m.id === messageId) {
            return { ...m, isTyping: false };
          }
          return m;
        }));
      }
    }, 20);
  }
}
