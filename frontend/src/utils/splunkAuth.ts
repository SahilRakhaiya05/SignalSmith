const STORAGE_KEY = "signalsmith_splunk_auth";

export interface SplunkAuthRecord {
  username: string;
  password: string;
}

export function getSplunkAuth(): SplunkAuthRecord | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as SplunkAuthRecord;
    if (parsed.username && parsed.password) return parsed;
  } catch {
    /* ignore */
  }
  return null;
}

export function setSplunkAuth(username: string, password: string): void {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ username, password }));
}

export function clearSplunkAuth(): void {
  sessionStorage.removeItem(STORAGE_KEY);
}

export function splunkAuthHeaders(): Record<string, string> {
  const auth = getSplunkAuth();
  if (!auth) return {};
  return {
    "X-Splunk-User": auth.username,
    "X-Splunk-Pass": auth.password,
  };
}