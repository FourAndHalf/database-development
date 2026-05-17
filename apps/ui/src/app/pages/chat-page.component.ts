import { CommonModule } from '@angular/common';
import { Component, computed, effect, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ChatApiService, Source } from '../services/chat-api.service';
import { firstValueFrom } from 'rxjs';

type Role = 'user' | 'assistant';

type UiMessage = {
  id: string;
  role: Role;
  text: string;
  sources?: Source[];
  pending?: boolean;
};

@Component({
  standalone: true,
  selector: 'app-chat-page',
  imports: [CommonModule, FormsModule],
  template: `
    <div class="shell">
      <aside class="sidebar">
        <div class="brand">
          <div class="logo">DB</div>
          <div>
            <div class="title">Database RAG</div>
            <div class="subtitle">papers • citations • chat</div>
          </div>
        </div>

        <button class="new" (click)="newChat()">New chat</button>

        <div class="meta">
          <div class="kv"><span>API</span><span class="pill">{{ apiPill() }}</span></div>
          <div class="kv"><span>Conversation</span><span class="mono">{{ conversationId() || '—' }}</span></div>
        </div>
      </aside>

      <main class="main">
        <header class="topbar">
          <div class="hint">Ask anything about your indexed papers (Spanner, Dynamo, Raft, Paxos, …)</div>
        </header>

        <section class="thread" #thread>
          <div class="empty" *ngIf="messages().length === 0">
            <div class="emptyCard">
              <div class="emptyTitle">Try a question</div>
              <div class="chips">
                <button (click)="prefill('Explain Spanner TrueTime and external consistency.')">Spanner + TrueTime</button>
                <button (click)="prefill('How does Dynamo handle conflicts and what are the tradeoffs?')">Dynamo conflicts</button>
                <button (click)="prefill('Compare Raft vs Paxos for implementing consensus.')">Raft vs Paxos</button>
              </div>
            </div>
          </div>

          <div class="msg" *ngFor="let m of messages(); trackBy: trackById" [class.user]="m.role === 'user'">
            <div class="avatar">{{ m.role === 'user' ? 'You' : 'RAG' }}</div>
            <div class="bubble">
              <pre class="text" [class.pending]="m.pending">{{ m.text }}</pre>
              <div class="sources" *ngIf="m.sources?.length">
                <div class="sourcesTitle">Sources</div>
                <div class="source" *ngFor="let s of m.sources">
                  <div class="sourceHead">
                    <span class="sourceTitle">{{ s.title }}</span>
                    <span class="sourceMeta">p. {{ s.page }} • {{ s.paper_id }}</span>
                  </div>
                  <div class="sourceSnippet">{{ s.snippet }}</div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <footer class="composer">
          <form class="composerInner" (ngSubmit)="send()" autocomplete="off">
            <textarea
              [(ngModel)]="draft"
              name="draft"
              class="input"
              rows="1"
              placeholder="Ask a question about the papers…"
              (keydown.enter)="onEnter($event)"
            ></textarea>
            <button class="send" type="submit" [disabled]="busy() || !draft.trim()">Send</button>
          </form>
          <div class="footnote">Mock UI • answers currently come from a mocked backend response.</div>
        </footer>
      </main>
    </div>
  `,
  styles: [
    `
      .shell {
        height: 100vh;
        display: grid;
        grid-template-columns: 320px 1fr;
      }

      .sidebar {
        background: rgba(15, 22, 41, 0.8);
        border-right: 1px solid var(--border);
        padding: 18px;
        display: flex;
        flex-direction: column;
        gap: 16px;
        backdrop-filter: blur(10px);
      }

      .brand {
        display: flex;
        align-items: center;
        gap: 12px;
      }
      .logo {
        width: 42px;
        height: 42px;
        border-radius: 12px;
        display: grid;
        place-items: center;
        font-weight: 700;
        background: linear-gradient(135deg, rgba(37, 99, 235, 0.9), rgba(99, 102, 241, 0.8));
        box-shadow: var(--shadow);
      }
      .title {
        font-weight: 650;
        letter-spacing: 0.2px;
      }
      .subtitle {
        font-size: 12px;
        color: var(--muted);
        margin-top: 2px;
      }

      .new {
        border: 1px solid var(--border);
        background: rgba(255, 255, 255, 0.03);
        color: var(--text);
        padding: 10px 12px;
        border-radius: 12px;
        cursor: pointer;
        font-weight: 600;
      }
      .new:hover {
        background: rgba(255, 255, 255, 0.06);
      }

      .meta {
        margin-top: auto;
        border-top: 1px solid var(--border);
        padding-top: 14px;
        display: grid;
        gap: 10px;
        color: var(--muted);
        font-size: 12px;
      }
      .kv {
        display: grid;
        grid-template-columns: 88px 1fr;
        gap: 10px;
        align-items: baseline;
      }
      .pill {
        display: inline-block;
        padding: 2px 8px;
        border: 1px solid var(--border);
        border-radius: 999px;
        color: var(--text);
        justify-self: start;
      }
      .mono {
        font-family: var(--mono);
        color: var(--text);
        opacity: 0.9;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .main {
        display: grid;
        grid-template-rows: auto 1fr auto;
        min-width: 0;
      }

      .topbar {
        padding: 14px 18px;
        border-bottom: 1px solid var(--border);
        background: rgba(15, 22, 41, 0.35);
        backdrop-filter: blur(10px);
      }
      .hint {
        color: var(--muted);
        font-size: 13px;
      }

      .thread {
        overflow: auto;
        padding: 22px 18px 0 18px;
      }

      .empty {
        display: grid;
        place-items: center;
        padding: 48px 0;
      }
      .emptyCard {
        border: 1px solid var(--border);
        background: rgba(255, 255, 255, 0.02);
        border-radius: 18px;
        padding: 18px;
        width: min(720px, 100%);
        box-shadow: var(--shadow);
      }
      .emptyTitle {
        font-weight: 650;
        margin-bottom: 12px;
      }
      .chips {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
      }
      .chips button {
        cursor: pointer;
        border: 1px solid var(--border);
        background: rgba(255, 255, 255, 0.03);
        color: var(--text);
        padding: 8px 10px;
        border-radius: 999px;
      }
      .chips button:hover {
        background: rgba(255, 255, 255, 0.06);
      }

      .msg {
        display: grid;
        grid-template-columns: 46px 1fr;
        gap: 12px;
        margin: 0 auto 16px auto;
        width: min(840px, 100%);
      }
      .msg.user .avatar {
        background: rgba(37, 99, 235, 0.25);
        border-color: rgba(37, 99, 235, 0.35);
      }

      .avatar {
        height: 36px;
        width: 46px;
        border-radius: 12px;
        display: grid;
        place-items: center;
        font-size: 12px;
        border: 1px solid var(--border);
        background: rgba(255, 255, 255, 0.02);
        color: var(--text);
      }

      .bubble {
        border: 1px solid var(--border);
        background: rgba(255, 255, 255, 0.02);
        border-radius: var(--radius);
        padding: 12px 12px;
      }

      .msg.user .bubble {
        background: rgba(37, 99, 235, 0.14);
        border-color: rgba(37, 99, 235, 0.25);
      }

      .text {
        margin: 0;
        white-space: pre-wrap;
        word-break: break-word;
        font: 13.5px/1.5 var(--sans);
      }
      .text.pending {
        opacity: 0.75;
      }

      .sources {
        margin-top: 12px;
        border-top: 1px solid var(--border);
        padding-top: 12px;
        display: grid;
        gap: 10px;
      }
      .sourcesTitle {
        font-size: 12px;
        color: var(--muted);
        font-weight: 650;
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }
      .source {
        border: 1px solid var(--border);
        background: rgba(255, 255, 255, 0.02);
        border-radius: 12px;
        padding: 10px;
      }
      .sourceHead {
        display: flex;
        gap: 10px;
        justify-content: space-between;
        align-items: baseline;
      }
      .sourceTitle {
        font-weight: 650;
        font-size: 13px;
      }
      .sourceMeta {
        font-family: var(--mono);
        color: var(--muted);
        font-size: 11px;
        white-space: nowrap;
      }
      .sourceSnippet {
        margin-top: 6px;
        color: var(--muted);
        font-size: 12.5px;
        line-height: 1.45;
      }

      .composer {
        border-top: 1px solid var(--border);
        padding: 14px 18px 18px 18px;
        background: rgba(15, 22, 41, 0.55);
        backdrop-filter: blur(10px);
      }
      .composerInner {
        width: min(840px, 100%);
        margin: 0 auto;
        display: grid;
        grid-template-columns: 1fr auto;
        gap: 12px;
        align-items: end;
      }
      .input {
        resize: none;
        border: 1px solid var(--border);
        background: rgba(255, 255, 255, 0.02);
        border-radius: 14px;
        padding: 12px 12px;
        color: var(--text);
        outline: none;
        font: 14px/1.4 var(--sans);
        min-height: 46px;
        max-height: 180px;
      }
      .input:focus {
        border-color: rgba(99, 102, 241, 0.45);
        box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.12);
      }
      .send {
        height: 46px;
        padding: 0 14px;
        border-radius: 14px;
        cursor: pointer;
        border: 1px solid rgba(37, 99, 235, 0.35);
        background: rgba(37, 99, 235, 0.28);
        color: var(--text);
        font-weight: 650;
      }
      .send:disabled {
        cursor: not-allowed;
        opacity: 0.55;
      }
      .footnote {
        width: min(840px, 100%);
        margin: 10px auto 0 auto;
        font-size: 12px;
        color: var(--muted);
      }

      @media (max-width: 980px) {
        .shell {
          grid-template-columns: 1fr;
        }
        .sidebar {
          display: none;
        }
      }
    `
  ]
})
export class ChatPageComponent {
  protected draft = '';

  private readonly conversationKey = 'db-rag.conversation_id';
  protected readonly conversationId = signal<string>(localStorage.getItem(this.conversationKey) ?? '');
  protected readonly messages = signal<UiMessage[]>([]);
  protected readonly busy = signal(false);
  protected readonly apiPill = computed(() => '/v1/chat');

  constructor(private readonly api: ChatApiService) {
    effect(() => {
      const id = this.conversationId();
      if (id) localStorage.setItem(this.conversationKey, id);
    });
  }

  protected trackById = (_: number, m: UiMessage) => m.id;

  protected prefill(text: string) {
    this.draft = text;
  }

  protected newChat() {
    this.conversationId.set('');
    localStorage.removeItem(this.conversationKey);
    this.messages.set([]);
    this.draft = '';
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
      text: 'Thinking…',
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
      this.messages.update((xs) =>
        xs.map((m) =>
          m.id === assistantId
            ? {
                ...m,
                text: res.answer,
                sources: res.sources,
                pending: false
              }
            : m
        )
      );
    } catch (err) {
      this.messages.update((xs) =>
        xs.map((m) =>
          m.id === assistantId
            ? {
                ...m,
                text:
                  'Request failed. Make sure the API is running:\n\n' +
                  'cd apps/api && go run ./cmd/api\n\n' +
                  'Error: ' +
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
}
