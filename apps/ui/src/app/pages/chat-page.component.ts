import { CommonModule } from '@angular/common';
import { Component, ElementRef, HostListener, ViewChild, afterRenderEffect, computed, effect, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ChatApiService, Source } from '../services/chat-api.service';
import { firstValueFrom } from 'rxjs';

type Role = 'user' | 'assistant';

type UiMessage = {
  id: string;
  role: Role;
  text: string;
  displayedText?: string;
  isTyping?: boolean;
  sources?: Source[];
  latencyMs?: number;
  pending?: boolean;
};

@Component({
  standalone: true,
  selector: 'app-chat-page',
  imports: [CommonModule, FormsModule],
  styleUrl: './chat-page.component.css',
  template: `
    <div class="app-container">
      <div class="shell">
        
        <!-- Sidebar -->
        <aside class="sidebar">
          <div class="sidebar-scroll">
            <div class="brand">
              <div class="logo">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="brand-icon"><path d="M12 12c-2-2.67-4-4-6-4a4 4 0 1 0 0 8c2 0 4-1.33 6-4Zm0 0c2 2.67 4 4 6 4a4 4 0 0 0 0-8c-2 0-4 1.33-6 4Z"/></svg>
              </div>
              <span class="brand-text">Aether</span>
            </div>

            <button class="new-chat-btn" (click)="newChat()">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></svg>
              New synthesis
            </button>

            <nav class="nav-menu">
              <a class="nav-item active">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
                Home
              </a>
              <a class="nav-item">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
                Explore Repository
              </a>
            </nav>

            <div class="nav-section">
              <div class="nav-title">Indexed Sources <button class="add-btn">+</button></div>
              <a class="nav-item"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg> Distributed Systems</a>
              <a class="nav-item"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg> Consensus Protocols</a>
            </div>

            <div class="nav-section">
              <div class="nav-title">History</div>
              <a class="nav-item"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg> CAP Theorem limits</a>
              <a class="nav-item"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg> Dynamo ring</a>
              <a class="nav-item"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg> Spanner clock sync</a>
            </div>
          </div>

          <div class="system-metrics">
            <div class="metrics-header">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
              <span>System Status</span>
            </div>
            <div class="metric-row">
              <span class="m-label">Model</span>
              <span class="m-val">Qwen-0.5B</span>
            </div>
            <div class="metric-row">
              <span class="m-label">Vector DB</span>
              <span class="m-val active">Connected</span>
            </div>
            <div class="metric-row">
              <span class="m-label">PostgreSQL</span>
              <span class="m-val active">Connected</span>
            </div>
          </div>
        </aside>

        <!-- Main Window -->
        <main class="main">
          
          <!-- HOME VIEW (Empty State) -->
          <div class="home-view" *ngIf="messages().length === 0">
            <div class="greeting">
              <h1>{{ greeting() }}, Researcher</h1>
              <p>How can I help you?</p>
            </div>

            <div class="center-composer">
              <form class="center-composer-inner" (ngSubmit)="send()" autocomplete="off">
                <div class="composer-header">
                  <div class="model-selector">
                    Aether 1.0 <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
                  </div>
                  <div class="search-hint">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
                    Use <span>@web-search</span> for live internet results
                  </div>
                </div>
                <textarea
                  #centerInput
                  [(ngModel)]="draft"
                  name="draft"
                  class="center-input"
                  rows="2"
                  placeholder="Ask Aether... (Try adding @web-search)"
                  (keydown.enter)="onEnter($event)"
                ></textarea>
                
                <div class="composer-toolbar">
                  <div class="toolbar-actions">
                    <button type="button" class="tool-btn"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg></button>
                    <button type="button" class="tool-btn"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg></button>
                    <button type="button" class="tool-btn"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg></button>
                  </div>
                  <button type="submit" class="tool-btn submit-btn" [disabled]="busy() || !draft.trim()">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 19V5M5 12l7-7 7 7"/></svg>
                  </button>
                </div>
              </form>
            </div>

            <div class="quick-actions">
              <button class="action-chip" (click)="prefill('Compare Bigtable and Dynamo architecture.')"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg> Compare papers</button>
              <button class="action-chip" (click)="prefill('Summarize the Raft consensus algorithm.')"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg> Summarize text</button>
              <button class="action-chip" (click)="prefill('Explain Spanner TrueTime')"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg> Deep dive</button>
            </div>

            <div class="widgets-row">
              <div class="widget">
                 <div class="w-head">Index Status <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg></div>
                 <div class="w-body">
                   <div class="w-main-val">9.9k</div>
                   <div class="w-sub">Vectors Indexed<br>ChromaDB Ready</div>
                 </div>
              </div>
              <div class="widget w-wide">
                 <div class="w-head"><span class="badge">New</span> Context-Aware Chat <button class="w-close">×</button></div>
                 <div class="w-text">Aether automatically retrieves chunks from indexed systems papers to ground your answers, avoiding hallucinations.</div>              </div>
            </div>
            
            <div class="recent-chats-header">Your recent chats <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg></div>
            <div class="recent-cards">
              <div class="r-card">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                <div class="r-title">CAP Theorem limits</div>
                <div class="r-time">2 hours ago</div>
              </div>
              <div class="r-card">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                <div class="r-title">Dynamo ring hash</div>
                <div class="r-time">5 hours ago</div>
              </div>
              <div class="r-card">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                <div class="r-title">Spanner clock sync</div>
                <div class="r-time">1 day ago</div>
              </div>
            </div>
          </div>

          <!-- CHAT VIEW (Active State) -->
          <div class="chat-view" *ngIf="messages().length > 0">
            <header class="chat-header">
              <div class="header-title">Aether</div>
            </header>
            
            <section class="thread" #thread>
              <div class="threadInner">
                <div class="row" *ngFor="let m of messages(); trackBy: trackById" [class.user]="m.role === 'user'">
                  <ng-container *ngIf="m.role === 'assistant'; else userRow">
                    <div class="avatar assistant-avatar" [class.exploring]="m.pending">
                       <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 12c-2-2.67-4-4-6-4a4 4 0 1 0 0 8c2 0 4-1.33 6-4Zm0 0c2 2.67 4 4 6 4a4 4 0 0 0 0-8c-2 0-4 1.33-6 4Z"/></svg>
                    </div>
                    <div class="bubble assistant" [class.typing]="m.isTyping">
                      <div class="text" [class.pending]="m.pending">
                        <span [innerHTML]="m.displayedText !== undefined ? m.displayedText : m.text"></span><span class="cursor" *ngIf="m.isTyping"></span>
                      </div>
                      <div class="msgMeta" *ngIf="!m.pending && !m.isTyping">
                        <button class="action-btn"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg></button>
                        <span *ngIf="m.latencyMs != null">~{{(m.latencyMs / 1000).toFixed(1)}}s</span>
                        <button class="toggleSources" *ngIf="m.sources?.length" (click)="toggleSources(m.id)">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
                          {{ isSourcesExpanded(m.id) ? 'Hide Citations' : ((m.sources?.length ?? 0) + ' Citations') }}
                        </button>
                      </div>
                      <div class="sources-accordion" [class.expanded]="isSourcesExpanded(m.id)" *ngIf="m.sources?.length">
                        <div class="sources-inner">
                          <div class="sources">
                            <div class="source" *ngFor="let s of m.sources; let idx = index">
                              <div class="sourceHead">
                                <span class="sourceTitle" *ngIf="!s.url">📄 [{{ idx + 1 }}] {{ s.title }}</span>
                                <span class="sourceTitle" *ngIf="s.url"><a [href]="s.url" target="_blank">🌐 [{{ idx + 1 }}] {{ s.title }}</a></span>
                                <span class="sourceMeta" *ngIf="!s.url">p. {{ s.page }}</span>
                              </div>
                              <div class="sourceSnippet">"{{ s.snippet }}"</div>
                            </div>                          </div>
                        </div>
                      </div>                    </div>
                  </ng-container>

                  <ng-template #userRow>
                    <div class="bubble user">
                      <div class="text">{{ m.text }}</div>
                    </div>
                  </ng-template>
                </div>
              </div>
            </section>

            <footer class="bottom-composer">
              <form class="center-composer bottom" (ngSubmit)="send()" autocomplete="off">
                <div class="center-composer-inner bottom-inner">
                  <textarea
                    #bottomInput
                    [(ngModel)]="draft"
                    name="draft"
                    class="center-input bottom-input"
                    rows="1"
                    placeholder="Ask a follow up... (Try @web-search)"
                    (keydown.enter)="onEnter($event)"
                  ></textarea>
                  <div class="composer-toolbar">
                    <div class="model-selector">
                      Aether 1.0 <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
                    </div>
                    <div class="toolbar-actions">
                      <button type="submit" class="tool-btn submit-btn" [disabled]="busy() || !draft.trim()">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 19V5M5 12l7-7 7 7"/></svg>
                      </button>
                    </div>
                  </div>
                </div>
              </form>
            </footer>
          </div>

        </main>
      </div>
    </div>
  `,
  styles: []
})
export class ChatPageComponent {
  @ViewChild('thread', { static: false }) private readonly threadEl?: ElementRef<HTMLElement>;
  @ViewChild('centerInput', { static: false }) private readonly centerInput?: ElementRef<HTMLTextAreaElement>;
  @ViewChild('bottomInput', { static: false }) private readonly bottomInput?: ElementRef<HTMLTextAreaElement>;

  protected draft = '';

  private readonly conversationKey = 'db-rag.conversation_id';
  protected readonly conversationId = signal<string>(localStorage.getItem(this.conversationKey) ?? '');
  protected readonly messages = signal<UiMessage[]>([]);
  protected readonly expandedSourcesByMessageId = signal<Record<string, boolean>>({});
  protected readonly busy = signal(false);

  @HostListener('window:keydown', ['$event'])
  onGlobalKeydown(e: KeyboardEvent) {
    // Only focus if not already focused on an input/textarea
    const target = e.target as HTMLElement;
    const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable;
    
    // Ignore control keys, function keys, etc.
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

  constructor(private readonly api: ChatApiService) {
    effect(() => {
      const id = this.conversationId();
      if (id) localStorage.setItem(this.conversationKey, id);
    });

    afterRenderEffect(() => {
      // Track message changes and scroll only after Angular flushes DOM updates.
      void this.messages();
      this.scrollToBottom();
    });
  }

  ngOnDestroy() {
    this.activeTypewriters.forEach(id => clearTimeout(id));
  }

  private simulateTypewriter(messageId: string, fullText: string) {
    let currentLength = 0;

    const typeNextChunk = () => {
      if (!this.activeTypewriters.has(messageId)) return;

      if (currentLength >= fullText.length) {
        currentLength = fullText.length;
        this.activeTypewriters.delete(messageId);
        
        this.messages.update((xs) =>
          xs.map((m) =>
            m.id === messageId
              ? { ...m, displayedText: fullText, isTyping: false }
              : m
          )
        );
        return;
      }

      // Calculate next chunk size
      let nextLength = currentLength + Math.floor(Math.random() * 4) + 2;
      if (nextLength > fullText.length) nextLength = fullText.length;

      // Prevent splitting HTML tags: if the chunk lands inside a tag, fast-forward to the end of it
      const currentSub = fullText.substring(0, nextLength);
      const lastOpen = currentSub.lastIndexOf('<');
      const lastClose = currentSub.lastIndexOf('>');
      
      if (lastOpen > lastClose) {
        // We are inside an HTML tag. Find its closing bracket.
        const nextClose = fullText.indexOf('>', lastOpen);
        if (nextClose !== -1) {
          nextLength = nextClose + 1;
        }
      }
      
      currentLength = nextLength;

      // Update UI with the new chunk
      this.messages.update((xs) =>
        xs.map((m) =>
          m.id === messageId
            ? { ...m, displayedText: fullText.substring(0, currentLength) }
            : m
        )
      );

      // Calculate dynamic delay for easing effect
      let nextDelay = Math.random() * 15 + 10;
      
      // Pause slightly on punctuation for a natural reading rhythm
      const lastChar = fullText[currentLength - 1];
      if (lastChar === '.' || lastChar === '?' || lastChar === '!') {
        nextDelay += 150;
      } else if (lastChar === ',' || lastChar === ':') {
        nextDelay += 60;
      } else if (lastChar === '>') {
         // Fast forward immediately after an HTML tag to keep rendering smooth
         nextDelay = 2;
      }

      const timerId = setTimeout(typeNextChunk, nextDelay);
      this.activeTypewriters.set(messageId, timerId);
    };

    const timerId = setTimeout(typeNextChunk, 20);
    this.activeTypewriters.set(messageId, timerId);
  }

  protected trackById = (_: number, m: UiMessage) => m.id;

  protected prefill(text: string) {
    this.draft = text;
  }

  protected newChat() {
    this.conversationId.set('');
    localStorage.removeItem(this.conversationKey);
    this.messages.set([]);
    this.expandedSourcesByMessageId.set({});
    this.draft = '';
  }

  protected isSourcesExpanded(messageId: string): boolean {
    return !!this.expandedSourcesByMessageId()[messageId];
  }

  protected toggleSources(messageId: string) {
    this.expandedSourcesByMessageId.update((state) => ({
      ...state,
      [messageId]: !state[messageId]
    }));
  }

  protected onEnter(e: Event) {
    const ke = e as KeyboardEvent;
    if (ke.shiftKey) return;
    ke.preventDefault();
    void this.send();
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
      
      // Update message state to begin typing
      this.messages.update((xs) =>
        xs.map((m) =>
          m.id === assistantId
            ? {
                ...m,
                text: res.answer,
                displayedText: '',
                isTyping: true,
                sources: res.sources,
                latencyMs: res.latency_ms,
                pending: false
              }
            : m
        )
      );

      // Start the typing effect
      this.simulateTypewriter(assistantId, res.answer);

    } catch (err) {
      this.messages.update((xs) =>
        xs.map((m) =>
          m.id === assistantId
            ? {
                ...m,
                text:
                  'Request failed. Make sure the backend API is running.\n\nError: ' +
                  String(err),
                pending: false
              }
            : m
        )
      );
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
