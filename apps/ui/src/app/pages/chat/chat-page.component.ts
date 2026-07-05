import { CommonModule } from '@angular/common';
import { Component, ElementRef, HostListener, ViewChild, afterRenderEffect, signal, OnDestroy, inject } from '@angular/core';
import { AuthService } from '../../services/auth.service';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { ChatApiService, Conversation } from '../../services/chat-api.service';
import { firstValueFrom } from 'rxjs';
import { ToastService } from '../../services/toast.service';
import { UiMessage, Tab } from './chat.types';
import { getGreeting, parseChatResponse, simulateTypewriterEffect } from './chat.utils';

import { SidebarComponent } from './components/sidebar/sidebar.component';
import { MessageComponent } from './components/message/message.component';
import { ComposerComponent } from './components/composer/composer.component';

@Component({
  standalone: true,
  selector: 'app-chat-page',
  imports: [CommonModule, RouterModule, SidebarComponent, MessageComponent, ComposerComponent],
  templateUrl: './chat-page.component.html',
  styleUrl: './chat-page.component.css'
})
export class ChatPageComponent implements OnDestroy {
  @ViewChild('thread', { static: false }) private readonly threadEl?: ElementRef<HTMLElement>;
  @ViewChild('centerComposer', { static: false }) private readonly centerComposer?: ComposerComponent;
  @ViewChild('bottomComposer', { static: false }) private readonly bottomComposer?: ComposerComponent;

  private readonly api = inject(ChatApiService);
  protected readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly toast = inject(ToastService);

  protected draft = '';
  private readonly conversationKey = 'db-rag.conversation_id';
  protected readonly conversationId = signal<string>(localStorage.getItem(this.conversationKey) ?? '');
  protected readonly messages = signal<UiMessage[]>([]);
  protected readonly history = signal<Conversation[]>([]);
  protected readonly busy = signal(false);
  protected readonly greeting = getGreeting;

  constructor() {
    if (this.auth.isAuthenticated()) {
      this.fetchHistory();
    }
    afterRenderEffect(() => this.scrollToBottom());

    this.route.paramMap.subscribe(async params => {
      const id = params.get('id');
      if (id) {
        this.conversationId.set(id);
        await this.loadConversation(id);
      }
    });

    this.route.queryParamMap.subscribe(async params => {
      const q = params.get('q');
      if (q) {
        this.prefill(q);
      }
    });
  }
  
  ngOnDestroy() {}

  @HostListener('window:keydown', ['$event'])
  onGlobalKeydown(e: KeyboardEvent) {
    const target = e.target as HTMLElement;
    const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable;
    
    if (isInput || e.ctrlKey || e.metaKey || e.altKey || e.key.length > 1) {
      return;
    }

    const composer = this.messages().length === 0 ? this.centerComposer : this.bottomComposer;
    if (composer) {
      composer.focusInput();
    }
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
      this.history.set(history || []);
    } catch (err) {
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
      this.toast.error('Failed to delete chat.');
    }
  }

  logout() {
    this.auth.logout();
    this.router.navigate(['/auth']);
  }

  prefill(query: string) {
    this.draft = query;
    const composer = this.messages().length === 0 ? this.centerComposer : this.bottomComposer;
    if (composer) {
      composer.focusInput();
    }
  }

  protected async send() {
    const message = this.draft.trim();
    if (!message || this.busy()) return;
    this.draft = '';
    this.busy.set(true);

    // Snapshot the conversation so far as working memory (before adding this turn),
    // so the engine can resolve follow-ups like "make an HTML view of this".
    const history = this.messages()
      .filter((m) => !m.pending && !m.isTyping && m.text)
      .slice(-8)
      .map((m) => ({
        role: m.role,
        text: (m.text || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 1500),
      }));

    const userMsg: UiMessage = { id: crypto.randomUUID(), role: 'user', text: message };
    const assistantId = crypto.randomUUID();
    const assistantMsg: UiMessage = { id: assistantId, role: 'assistant', text: 'Exploring', pending: true };

    this.messages.update((xs) => [...xs, userMsg, assistantMsg]);

    try {
      const res = await firstValueFrom(
        this.api.chat({
          conversation_id: this.conversationId() || undefined,
          message,
          history
        })
      );
      if (!res) throw new Error('no response');
      this.conversationId.set(res.conversation_id);

      const { mainText, parsedTabs } = parseChatResponse(res.answer);

      this.messages.update((xs) => xs.map((m) => m.id === assistantId ? { 
        ...m, text: mainText, displayedText: '', isTyping: true, sources: res.sources, 
        latencyMs: res.latency_ms, pending: false, tabs: parsedTabs, activeTabIdx: 0 
      } : m));

      simulateTypewriterEffect(this.messages, assistantId, mainText);
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
}
