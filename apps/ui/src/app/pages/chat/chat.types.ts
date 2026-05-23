import { Source } from '../../services/chat-api.service';

export type Role = 'user' | 'assistant';

export type Tab = {
  title: string;
  content: string;
};

export type UiMessage = {
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
