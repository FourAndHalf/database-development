import { CommonModule } from '@angular/common';
import { Component, ElementRef, HostListener, ViewChild, afterRenderEffect, signal, OnDestroy, OnInit, inject } from '@angular/core';
import { AuthService } from '../../services/auth.service';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { ChatApiService, Conversation, DashboardMetrics } from '../../services/chat-api.service';
import { firstValueFrom } from 'rxjs';
import { ToastService } from '../../services/toast.service';
import { ConfirmDialogService } from '../../services/confirm-dialog.service';
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
export class ChatPageComponent implements OnInit, OnDestroy {
  @ViewChild('thread', { static: false }) private readonly threadEl?: ElementRef<HTMLElement>;
  @ViewChild('centerComposer', { static: false }) private readonly centerComposer?: ComposerComponent;
  @ViewChild('bottomComposer', { static: false }) private readonly bottomComposer?: ComposerComponent;

  private readonly api = inject(ChatApiService);
  protected readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly toast = inject(ToastService);
  private readonly confirmDialog = inject(ConfirmDialogService);

  protected draft = '';
  private readonly conversationKey = 'db-rag.conversation_id';
  protected readonly conversationId = signal<string>(localStorage.getItem(this.conversationKey) ?? '');
  protected readonly messages = signal<UiMessage[]>([]);
  protected readonly history = signal<Conversation[]>([]);
  protected readonly busy = signal(false);
  protected readonly greeting = getGreeting;

  protected readonly dashboardMetrics = signal<DashboardMetrics | null>(null);
  protected readonly metricsLoading = signal(true);
  protected readonly showMetricsModal = signal(false);
  private metricsInterval: any = null;

  private readonly mobileBreakpoint = 980;
  protected readonly sidebarOpen = signal(typeof window === 'undefined' || window.innerWidth > this.mobileBreakpoint);

  constructor() {
    this.fetchHistory();
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
        this.messages.set([]);
        this.conversationId.set('');
        localStorage.removeItem(this.conversationKey);
        this.prefill(q);
      }
    });
  }

  ngOnInit() {
    this.loadDashboardMetrics();
    // Auto-refresh every 30 seconds
    this.metricsInterval = setInterval(() => {
      if (this.messages().length === 0) {
        this.loadDashboardMetrics();
      }
    }, 30000);
  }
  
  ngOnDestroy() {
    if (this.metricsInterval) {
      clearInterval(this.metricsInterval);
    }
  }

  private loadDashboardMetrics() {
    this.api.getDashboardMetrics().subscribe({
      next: (metrics) => {
        this.dashboardMetrics.set(metrics);
        this.metricsLoading.set(false);
      },
      error: () => {
        this.metricsLoading.set(false);
      },
    });
  }

  protected formatUptime(seconds: number): string {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return m > 0 ? `${h}h ${m}m` : `${h}h`;
  }

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

  protected toggleSidebar() {
    this.sidebarOpen.update((v) => !v);
  }

  protected onSidebarClose() {
    if (window.innerWidth <= this.mobileBreakpoint) {
      this.sidebarOpen.set(false);
    }
  }

  protected newChat() {
    this.messages.set([]);
    this.conversationId.set('');
    localStorage.removeItem(this.conversationKey);
    this.router.navigate(['/chat']);
  }
  
  protected async fetchHistory() {
    let userId = '00000000-0000-0000-0000-000000000000';
    const user = this.auth.user();
    if (user) {
      userId = user.id;
    }
    try {
      const history = await firstValueFrom(this.api.getHistory(userId));
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
      const mapped: UiMessage[] = res.map((m: any) => {
        const { mainText, parsedTabs } = parseChatResponse(m.content ?? '');
        return {
          id: m.id,
          role: m.role,
          text: m.role === 'assistant' ? mainText : (m.content ?? ''),
          sources: m.role === 'assistant' ? m.sources : undefined,
          tabs: m.role === 'assistant' ? parsedTabs : undefined,
          activeTabIdx: 0,
        };
      });
      // External (web) citations for an answer are shown as breadcrumbs under the
      // question that prompted them, so hang them off the preceding user message.
      for (let i = 1; i < mapped.length; i++) {
        if (mapped[i].role === 'assistant' && mapped[i - 1].role === 'user') {
          mapped[i - 1].externalLinks = mapped[i].sources?.filter((s) => s.url);
        }
      }
      this.messages.set(mapped);
    } catch (err) {
      this.toast.error('Failed to load conversation.');
    } finally {
      this.busy.set(false);
    }
  }

  protected async deleteConversation(id: string) {
    const confirmed = await this.confirmDialog.confirm('Are you sure you want to delete this chat?', {
      title: 'Delete chat',
      confirmLabel: 'Delete',
      danger: true
    });
    if (!confirmed) return;
    let userId = '00000000-0000-0000-0000-000000000000';
    const user = this.auth.user();
    if (user) {
      userId = user.id;
    }
    try {
      await firstValueFrom(this.api.deleteChat(userId, id));
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
      localStorage.setItem(this.conversationKey, res.conversation_id);

      const { mainText, parsedTabs } = parseChatResponse(res.answer);
      const externalLinks = res.sources?.filter((s) => s.url);

      this.messages.update((xs) => xs.map((m) => {
        if (m.id === assistantId) {
          return {
            ...m, text: mainText, displayedText: '', isTyping: true, sources: res.sources,
            latencyMs: res.latency_ms, pending: false, tabs: parsedTabs, activeTabIdx: 0
          };
        }
        if (m.id === userMsg.id) {
          return { ...m, externalLinks };
        }
        return m;
      }));

      simulateTypewriterEffect(this.messages, assistantId, mainText);
      void this.fetchHistory();

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
