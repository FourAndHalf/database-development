import { WritableSignal } from '@angular/core';
import { UiMessage, Tab } from './chat.types';

export function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 18) return 'Good afternoon';
  return 'Good evening';
}

export function parseChatResponse(answer: string): { mainText: string; parsedTabs: Tab[] } {
  let mainText = answer;
  let parsedTabs: Tab[] = [];
  try {
    const structured = JSON.parse(answer);
    if (structured.main && Array.isArray(structured.tabs)) {
      mainText = structured.main;
      parsedTabs = [{ title: 'Overview', content: structured.main }, ...structured.tabs];
    }
  } catch (e) {
    // Return default if parsing fails
  }
  return { mainText, parsedTabs };
}

export function simulateTypewriterEffect(
  messagesSignal: WritableSignal<UiMessage[]>,
  messageId: string,
  text: string
) {
  const CHARS_PER_TICK = 5;
  let i = 0;
  const interval = setInterval(() => {
    messagesSignal.update(xs => xs.map(m => m.id === messageId ? { ...m, displayedText: text.substring(0, i) } : m));
    i += CHARS_PER_TICK;
    if (i > text.length) {
      clearInterval(interval);
      messagesSignal.update(xs => xs.map(m => m.id === messageId ? { ...m, isTyping: false } : m));
    }
  }, 20);
}
