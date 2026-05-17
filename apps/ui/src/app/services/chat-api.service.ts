import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

export type Source = {
  paper_id: string;
  title: string;
  page: number;
  snippet: string;
  url?: string;
};

export type ChatMessage = {
  conversation_id?: string;
  message: string;
};

export type ChatResponse = {
  conversation_id: string;
  answer: string;
  sources?: Source[];
  latency_ms: number;
  mock: boolean;
};

@Injectable({ providedIn: 'root' })
export class ChatApiService {
  constructor(private readonly http: HttpClient) {}

  chat(body: ChatMessage): Observable<ChatResponse> {
    return this.http.post<ChatResponse>('/v1/chat', body);
  }
}

