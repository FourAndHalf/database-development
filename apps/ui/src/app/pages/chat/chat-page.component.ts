import { CommonModule } from '@angular/common';
import { Component, ElementRef, HostListener, ViewChild, afterRenderEffect, computed, effect, signal, OnDestroy, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { trigger, transition, style, animate } from '@angular/animations';
import { AuthService } from '../../services/auth.service';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { ChatApiService, Conversation, Source } from '../../services/chat-api.service';
import { firstValueFrom } from 'rxjs';

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

  protected draft = '';

  private readonly conversationKey = 'db-rag.conversation_id';
  protected readonly conversationId = signal<string>(localStorage.getItem(this.conversationKey) ?? '');
  protected readonly messages = signal<UiMessage[]>([]);
  protected readonly history = signal<Conversation[]>([]);
  protected readonly expandedSourcesByMessageId = signal<Record<string, boolean>>({});
  protected readonly busy = signal(false);

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

  protected greeting = computed(() => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  });

  private activeTypewriters: Map<string, any> = new Map();

  constructor() {
    // Check for query params to prefill from Explore page
    this.route.queryParams.subscribe(params => {
      if (params['q']) {
        this.draft = params['q'];
        void this.send();
        // Clear params after use
        void this.router.navigate([], { 
          relativeTo: this.route, 
          queryParams: { q: null }, 
          queryParamsHandling: 'merge' 
        });
      }
    });

    effect(() => {
      const id = this.conversationId();
      if (id) localStorage.setItem(this.conversationKey, id);
      else localStorage.removeItem(this.conversationKey);
    });

    effect(() => {
      if (this.auth.isAuthenticated()) {
        this.fetchHistory();
      } else {
        this.history.set([]);
      }
    });

    afterRenderEffect(() => {
      void this.messages();
      this.scrollToBottom();
    });
  }

  logout() {
    this.auth.logout();
    this.newChat();
  }

  async fetchHistory() {
    const user = this.auth.user();
    if (!user) return;
    try {
      const h = await firstValueFrom(this.api.getHistory(user.id));
      this.history.set(h || []);
    } catch (err) {
      console.error('Failed to fetch history:', err);
    }
  }

  async deleteChat(e: Event, id: string) {
    e.stopPropagation();
    const user = this.auth.user();
    if (!user) return;
    try {
      await firstValueFrom(this.api.deleteChat(user.id, id));
      if (this.conversationId() === id) this.newChat();
      await this.fetchHistory();
    } catch (err) {
      console.error('Failed to delete chat:', err);
    }
  }

  async loadConversation(id: string) {
    if (this.busy()) return;
    this.busy.set(true);
    try {
      const msgs = await firstValueFrom(this.api.getMessages(id));
      this.conversationId.set(id);
      this.messages.set(msgs.map(m => ({
        id: m.id,
        role: m.role as Role,
        text: m.text,
        pending: false
      })));
    } catch (err) {
      console.error('Failed to load conversation:', err);
    } finally {
      this.busy.set(false);
    }
  }

  ngOnDestroy() {
    this.activeTypewriters.forEach(id => clearTimeout(id));
  }

  private simulateTypewriter(messageId: string, fullText: string) {
    let currentLength = 0;
    const typeNextChunk = () => {
      if (!this.activeTypewriters.has(messageId)) return;
      if (currentLength >= fullText.length) {
        this.activeTypewriters.delete(messageId);
        this.messages.update((xs) => xs.map((m) => m.id === messageId ? { ...m, displayedText: fullText, isTyping: false } : m));
        return;
      }
      let nextLength = currentLength + Math.floor(Math.random() * 4) + 2;
      if (nextLength > fullText.length) nextLength = fullText.length;
      
      // Handle HTML tags: if the chunk lands inside a tag, fast-forward to the end of it
      const currentSub = fullText.substring(0, nextLength);
      const lastOpen = currentSub.lastIndexOf('<');
      const lastClose = currentSub.lastIndexOf('>');
      if (lastOpen > lastClose) {
        const nextClose = fullText.indexOf('>', lastOpen);
        if (nextClose !== -1) nextLength = nextClose + 1;
      }
      
      currentLength = nextLength;
      this.messages.update((xs) => xs.map((m) => m.id === messageId ? { ...m, displayedText: fullText.substring(0, currentLength) } : m));
      
      let nextDelay = Math.random() * 15 + 10;
      const lastChar = fullText[currentLength - 1];
      if (['.', '?', '!'].includes(lastChar)) nextDelay += 150;
      else if ([',', ':'].includes(lastChar)) nextDelay += 60;
      else if (lastChar === '>') nextDelay = 2;
      
      const timerId = setTimeout(typeNextChunk, nextDelay);
      this.activeTypewriters.set(messageId, timerId);
    };
    const initialTimerId = setTimeout(typeNextChunk, 20);
    this.activeTypewriters.set(messageId, initialTimerId);
  }

  protected trackById = (_: number, m: UiMessage) => m.id;

  protected copyToClipboard(m: UiMessage) {
    void navigator.clipboard.writeText(m.text);
    m.copied = true;
    setTimeout(() => m.copied = false, 2000);
  }

  protected prefill(text: string) {
    this.draft = text;
    if (this.centerInput) this.centerInput.nativeElement.focus();
  }

  protected newChat() {
    this.conversationId.set('');
    this.messages.set([]);
    this.expandedSourcesByMessageId.set({});
    this.draft = '';
  }

  protected isSourcesExpanded(messageId: string): boolean {
    return !!this.expandedSourcesByMessageId()[messageId];
  }

  protected toggleSources(messageId: string) {
    this.expandedSourcesByMessageId.update((state) => ({ ...state, [messageId]: !state[messageId] }));
  }

  protected onEnter(e: Event) {
    const ke = e as KeyboardEvent;
    if (ke.shiftKey) return;
    ke.preventDefault();
    void this.send();
  }

  protected getActiveContent(m: UiMessage): string {
    if (m.isTyping) return m.displayedText || '';
    if (m.tabs && m.tabs.length > 0) return m.tabs[m.activeTabIdx ?? 0].content;
    return m.text;
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
          message 
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
    } finally {
      this.busy.set(false);
    }
  }

  private scrollToBottom() {
    const el = this.threadEl?.nativeElement;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }
}
