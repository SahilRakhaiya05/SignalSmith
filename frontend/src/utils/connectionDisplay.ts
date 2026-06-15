const LABELS: Record<string, string> = {
  splunk_mcp: "Splunk MCP",
  splunk_api: "Splunk API",
  offline: "Offline",
  mcp: "Splunk MCP",
  rest: "Splunk API",
  fallback: "Offline",
};

const CLASSES: Record<string, string> = {
  splunk_mcp: "mcp",
  splunk_api: "splunk",
  offline: "offline",
  mcp: "mcp",
  rest: "splunk",
  fallback: "offline",
};

export function connectionLabel(mode: string): string {
  return LABELS[mode] || "Offline";
}

export function connectionClass(mode: string): string {
  return CLASSES[mode] || "offline";
}

export function isSplunkOnline(mode: string): boolean {
  return mode !== "offline" && mode !== "fallback";
}