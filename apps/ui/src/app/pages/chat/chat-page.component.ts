import { CommonModule } from '@angular/common';
import { Component, ElementRef, HostListener, ViewChild, afterRenderEffect, computed, effect, signal, OnDestroy } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { trigger, transition, style, animate } from '@angular/animations';
import { AuthService } from '../services/auth.service';
import { Router, RouterModule } from '@angular/router';
import { ChatApiService, Conversation, Source } from '../services/chat-api.service';
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
  styleUrl: './chat-page.component.css',
  animations: [
    trigger('popScale', [
      transition(':enter', [
        style({ transform: 'scale(0.5)', opacity: 0 }),
        animate('200ms cubic-bezier(0.175, 0.885, 0.32, 1.275)', style({ transform: 'scale(1)', opacity: 1 }))
      ])
    ])
  ],
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
              <a class="nav-item" [class.active]="!showExplore()" (click)="toggleExplore(false)">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
                Home
              </a>
              <a class="nav-item" [class.active]="showExplore()" (click)="toggleExplore(true)">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
                Explore Repository
              </a>
            </nav>

            <div class="nav-section">
              <div class="nav-title">Indexed Sources <button class="add-btn">+</button></div>
              <a class="nav-item"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg> Distributed Systems</a>
              <a class="nav-item"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg> Consensus Protocols</a>
            </div>

            @if (auth.isAuthenticated() && history().length > 0) {
              <div class="nav-section">
                <div class="nav-title">History</div>
                <div class="history-list">
                  @for (c of history(); track c.id) {
                    <div class="nav-item history-item" (click)="loadConversation(c.id)">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                      <span class="h-title">{{ c.title }}</span>
                      <button class="del-chat" (click)="deleteChat($event, c.id)">×</button>
                    </div>
                  }
                </div>
              </div>
            }
          </div>

          <div class="sidebar-footer">
            @if (!auth.isAuthenticated()) {
              <div class="auth-box">
                <p>Sign in to save research history.</p>
                <button class="auth-btn" routerLink="/auth">Sign In</button>
              </div>
            } @else {
              <div class="auth-box authenticated">
                <div class="user-info">
                  <div class="user-avatar">{{ auth.user()?.email?.charAt(0)?.toUpperCase() }}</div>
                  <div class="user-details">
                    <span class="u-email" [title]="auth.user()?.email">{{ auth.user()?.email }}</span>
                    <button class="logout-link" (click)="logout()">Sign Out</button>
                  </div>
                </div>
              </div>
            }

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
          </div>
        </aside>

        <!-- Main Window -->
        <main class="main">
          
          <!-- EXPLORE VIEW -->
          @if (showExplore()) {
            <div class="explore-view">
              <div class="explore-header">
                <h2>Research Repository</h2>
                <p>Query metadata and discover papers indexed in Aether.</p>
                <div class="search-bar">
                  <input 
                    type="text" 
                    placeholder="Search by title or author..." 
                    [ngModel]="repositorySearchQuery()" 
                    (ngModelChange)="repositorySearchQuery.set($event)"
                    (input)="searchRepository()"
                  >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                </div>
              </div>

              <div class="explore-results">
                @for (p of repositoryResults(); track p.id) {
                  <div class="p-card">
                    <div class="p-title">{{ p.title }}</div>
                    <div class="p-meta">
                      <span class="p-file">PDF: {{ p.filename }}</span>
                      @if (p.url) { <a [href]="p.url" target="_blank" class="p-link">View Source</a> }
                    </div>
                    <button class="p-action" (click)="prefill('Summarize ' + p.title); toggleExplore(false)">Synthesize</button>
                  </div>
                } @empty {
                  <div class="empty-results">No papers found matching your query.</div>
                }
              </div>
            </div>
          } @else {
            <!-- HOME VIEW (Empty State) -->
            @if (messages().length === 0) {
              <div class="home-view">
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
                      [ngModel]="draft"
                      (ngModelChange)="draft = $event"
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
                
                @if (auth.isAuthenticated() && history().length > 0) {
                  <div class="recent-chats-header">Your recent chats <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg></div>
                  <div class="recent-cards">
                    @for (c of history().slice(0, 3); track c.id) {
                      <div class="r-card" (click)="loadConversation(c.id)">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                        <div class="r-title">{{ c.title }}</div>
                        <div class="r-time">Recent</div>
                      </div>
                    }
                  </div>
                }
              </div>
            }

            <!-- CHAT VIEW (Active State) -->
            @if (messages().length > 0) {
              <div class="chat-view">
                <header class="chat-header">
                  <div class="header-title">Aether</div>
                </header>

                <section class="thread" #thread>
                  <div class="threadInner">
                    @for (m of messages(); track m.id) {
                      <div class="row" [class.user]="m.role === 'user'">
                        @if (m.role === 'assistant') {
                          <div class="avatar assistant-avatar" [class.exploring]="m.pending">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 12c-2-2.67-4-4-6-4a4 4 0 1 0 0 8c2 0 4-1.33 6-4Zm0 0c2 2.67 4 4 6 4a4 4 0 0 0 0-8c-2 0-4 1.33-6 4Z"/></svg>
                          </div>
                          <div class="bubble assistant" [class.typing]="m.isTyping">
                            <!-- Tab Bar -->
                            @if (m.tabs && m.tabs.length > 0 && !m.isTyping) {
                              <div class="tab-bar">
                                @for (tab of m.tabs; track $index) {
                                  <button 
                                    class="tab-btn" 
                                    [class.active]="(m.activeTabIdx ?? 0) === $index"
                                    (click)="m.activeTabIdx = $index"
                                  >
                                    {{ tab.title }}
                                  </button>
                                }
                              </div>
                            }

                            <div class="assistant-content-wrap">
                              <div class="text" [class.pending]="m.pending">
                                <span [innerHTML]="getActiveContent(m)"></span><span class="cursor" *ngIf="m.isTyping"></span>
                              </div>
                            </div>
                            @if (!m.pending && !m.isTyping) {
                              <div class="msgMeta">
                                <button class="action-btn"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg></button>
                                @if (m.latencyMs != null) { <span>~{{(m.latencyMs / 1000).toFixed(1)}}s</span> }
                                @if (m.sources?.length) {
                                  <button class="toggleSources" (click)="toggleSources(m.id)">
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
                                    {{ isSourcesExpanded(m.id) ? 'Hide Citations' : ((m.sources?.length ?? 0) + ' Citations') }}
                                  </button>
                                }
                              </div>
                            }
                            @if (m.sources?.length) {
                              <div class="sources-accordion" [class.expanded]="isSourcesExpanded(m.id)">
                                <div class="sources-inner">
                                  <div class="sources">
                                    @for (s of m.sources; track $index) {
                                      <div class="source">
                                        <div class="sourceHead">
                                          @if (!s.url) { <span class="sourceTitle">📄 [{{ $index + 1 }}] {{ s.title }}</span> }
                                          @if (s.url) { <span class="sourceTitle"><a [href]="s.url" target="_blank">🌐 [{{ $index + 1 }}] {{ s.title }}</a></span> }
                                          @if (!s.url) { <span class="sourceMeta">p. {{ s.page }}</span> }
                                        </div>
                                        <div class="sourceSnippet">"{{ s.snippet }}"</div>
                                      </div>
                                    }
                                  </div>
                                </div>
                              </div>
                            }
                          </div>
                        } @else {
                          <div class="bubble user">
                            <div class="text">{{ m.text }}</div>
                            <button class="copy-query-btn" (click)="copyToClipboard(m)" title="Copy query">
                              @if (!m.copied) {
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                              } @else {
                                <svg @popScale width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
                              }
                            </button>
                          </div>
                        }
                      </div>
                    }
                  </div>
                </section>

                <footer class="bottom-composer">
                  <form class="center-composer bottom" (ngSubmit)="send()" autocomplete="off">
                    <div class="center-composer-inner bottom-inner">
                      <textarea
                        #bottomInput
                        [ngModel]="draft"
                        (ngModelChange)="draft = $event"
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
            }
          }
        </main>
      </div>
    </div>
  `,
  styles: []
})
export class ChatPageComponent implements OnDestroy {
  @ViewChild('thread', { static: false }) private readonly threadEl?: ElementRef<HTMLElement>;
  @ViewChild('centerInput', { static: false }) private readonly centerInput?: ElementRef<HTMLTextAreaElement>;
  @ViewChild('bottomInput', { static: false }) private readonly bottomInput?: ElementRef<HTMLTextAreaElement>;

  protected draft = '';

  private readonly conversationKey = 'db-rag.conversation_id';
  protected readonly conversationId = signal<string>(localStorage.getItem(this.conversationKey) ?? '');
  protected readonly messages = signal<UiMessage[]>([]);
  protected readonly history = signal<Conversation[]>([]);
  protected readonly expandedSourcesByMessageId = signal<Record<string, boolean>>({});
  protected readonly busy = signal(false);
  protected readonly showExplore = signal(false);
  protected readonly repositorySearchQuery = signal('');
  protected readonly repositoryResults = signal<any[]>([]);

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

  constructor(
    private readonly api: ChatApiService,
    protected readonly auth: AuthService,
    private readonly router: Router
  ) {
    effect(() => {
      const id = this.conversationId();
      if (id) localStorage.setItem(this.conversationKey, id);
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

  async searchRepository() {
    const q = this.repositorySearchQuery().trim();
    if (!q) {
      this.repositoryResults.set([]);
      return;
    }
    try {
      const results = await firstValueFrom(this.api.searchPapers(q));
      this.repositoryResults.set(results || []);
    } catch (err) {
      console.error('Failed to search repository:', err);
    }
  }

  toggleExplore(show: boolean) {
    this.showExplore.set(show);
    if (show) this.searchRepository();
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
        role: m.role,
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
    const userMsg: UiMessage = { id: crypto.randomUUID(), role: 'user', text: message };
    const assistantId = crypto.randomUUID();
    const assistantMsg: UiMessage = { id: assistantId, role: 'assistant', text: 'Exploring', pending: true };
    this.messages.update((xs) => [...xs, userMsg, assistantMsg]);
    try {
      const res = await firstValueFrom(this.api.chat({ conversation_id: this.conversationId() || undefined, message }));
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
        console.warn('Response was not structured JSON:', e);
      }
      this.messages.update((xs) => xs.map((m) => m.id === assistantId ? { ...m, text: mainText, displayedText: '', isTyping: true, sources: res.sources, latencyMs: res.latency_ms, pending: false, tabs: parsedTabs, activeTabIdx: 0 } : m));
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
