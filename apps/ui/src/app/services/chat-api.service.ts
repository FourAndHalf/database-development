import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

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

export type Conversation = {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
};

@Injectable({ providedIn: 'root' })
export class ChatApiService {
  constructor(private readonly http: HttpClient) {}

  chat(body: ChatMessage): Observable<ChatResponse> {
    return this.http.post<ChatResponse>('/v1/chat', body);
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

