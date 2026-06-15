const CHAT_KEY = "signalsmith_assistant_chat";

export interface StoredChatMessage {
  role: "user" | "assistant";
  content: string;
}

export function loadChatMessages(): StoredChatMessage[] {
  try {
    const raw = sessionStorage.getItem(CHAT_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as StoredChatMessage[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveChatMessages(messages: StoredChatMessage[]): void {
  sessionStorage.setItem(CHAT_KEY, JSON.stringify(messages.slice(-50)));
}

export function clearChatMessages(): void {
  sessionStorage.removeItem(CHAT_KEY);
}