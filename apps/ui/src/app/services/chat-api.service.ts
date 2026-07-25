import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { AuthService } from './auth.service';

export type RealtimeMetrics = {
  uptime_s: number;
};

export type DailyMetric = {
  id: number;
  metric_date: string;
  total_queries: number;
  successful_queries: number;
  failed_queries: number;
  failure_rate: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  avg_latency_ms: number;
  min_latency_ms: number;
  max_latency_ms: number;
};

export type DashboardMetrics = {
  realtime: RealtimeMetrics;
  today: DailyMetric | null;
  history: DailyMetric[];
  date: string;
};

export type Source = {
  paper_id: string;
  title: string;
  page: number;
  snippet: string;
  url?: string;
};

export type HistoryTurn = {
  role: 'user' | 'assistant';
  text: string;
};

export type ChatMessage = {
  conversation_id?: string;
  message: string;
  model?: string;
  history?: HistoryTurn[];
};

export type ChatResponse = {
  conversation_id: string;
  answer: string;
  sources?: Source[];
  latency_ms: number;
  mock: boolean;
};

export type ChatStreamEvent =
  | { type: 'token'; text: string }
  | ({ type: 'final' } & ChatResponse)
  | { type: 'error'; detail: string };

export type Conversation = {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
};

@Injectable({ providedIn: 'root' })
export class ChatApiService {
  private readonly auth = inject(AuthService);

  constructor(private readonly http: HttpClient) {}

  chat(body: ChatMessage): Observable<ChatResponse> {
    return this.http.post<ChatResponse>('/v1/chat', body);
  }

  /**
   * Streams the chat response over SSE via fetch(), since HttpClient doesn't
   * expose incremental body chunks. Bypasses HttpClient's interceptor pipeline,
   * so the auth header is attached manually here to match authInterceptor.
   */
  async *chatStream(body: ChatMessage, signal?: AbortSignal): AsyncGenerator<ChatStreamEvent> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    const token = this.auth.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await fetch('/v1/chat', {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
      signal,
    });
    if (!res.ok || !res.body) {
      throw new Error(`chat request failed: ${res.status}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });

      let idx: number;
      while ((idx = buf.indexOf('\n\n')) !== -1) {
        const frame = buf.slice(0, idx);
        buf = buf.slice(idx + 2);

        let event = 'message';
        let data = '';
        for (const line of frame.split('\n')) {
          if (line.startsWith('event: ')) event = line.slice(7);
          else if (line.startsWith('data: ')) data += line.slice(6);
        }
        if (!data) continue;

        const parsed = JSON.parse(data);
        if (event === 'token') yield { type: 'token', text: parsed.text };
        else if (event === 'final') yield { type: 'final', ...parsed };
        else if (event === 'error') yield { type: 'error', detail: parsed.detail };
      }
    }
  }

  getHistory(userId: string): Observable<Conversation[]> {
    return this.http.get<Conversation[]>(`/v1/users/${userId}/history`);
  }

  deleteChat(userId: string, conversationId: string): Observable<any> {
    return this.http.delete(`/v1/users/${userId}/chats/${conversationId}`);
  }

  getMessages(conversationId: string): Observable<any[]> {
    return this.http.get<any[]>(`/v1/chat/${conversationId}`);
  }

  getDashboardMetrics(): Observable<DashboardMetrics> {
    return this.http.get<DashboardMetrics>('/v1/metrics/dashboard');
  }

  searchPapers(query: string, page: number, pageSize: number): Observable<any> {
    return this.http.get<any>(`/v1/papers?q=${encodeURIComponent(query)}&page=${page}&pageSize=${pageSize}`);
  }

  deletePaper(id: string): Observable<any> {
    return this.http.delete(`/v1/papers/${id}`);
  }

  uploadPaper(data: FormData): Observable<any> {
    return this.http.post(`/v1/papers`, data);
  }
}

