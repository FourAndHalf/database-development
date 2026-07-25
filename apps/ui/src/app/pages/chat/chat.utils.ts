import { Tab } from './chat.types';

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
