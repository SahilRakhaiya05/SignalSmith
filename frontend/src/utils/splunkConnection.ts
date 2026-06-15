import type { HealthResponse, IntegrationStatus, SessionStatus } from "../types";

type LegacyStatus = Partial<SessionStatus> & { runtime_mode?: string };
type LegacyHealth = Partial<HealthResponse> & { mode?: string };
type LegacyIntegrations = IntegrationStatus | (IntegrationStatus & { runtime_mode?: string }) | null;

export function resolveSplunkConnection(
  status: LegacyStatus,
  integrations: LegacyIntegrations,
  health?: LegacyHealth
): { connection: string; connected: boolean } {
  if (status.splunk_connection && status.splunk_connection !== "offline") {
    return {
      connection: normalizeConnection(status.splunk_connection),
      connected: status.splunk_connected !== false,
    };
  }

  if (integrations?.splunk_connection && integrations.splunk_connection !== "offline") {
    return {
      connection: normalizeConnection(integrations.splunk_connection),
      connected: true,
    };
  }

  if (integrations?.mcp?.available) {
    return { connection: "splunk_mcp", connected: true };
  }

  if (integrations?.splunk?.rest_api?.reachable) {
    return { connection: "splunk_api", connected: true };
  }

  const legacyMode =
    status.runtime_mode ||
    health?.mode ||
    (integrations as { runtime_mode?: string } | null)?.runtime_mode;

  if (legacyMode === "mcp" || legacyMode === "splunk_mcp") {
    return { connection: "splunk_mcp", connected: true };
  }

  if (legacyMode === "rest" || legacyMode === "splunk_api") {
    return { connection: "splunk_api", connected: true };
  }

  if (health?.splunk_connected || status.splunk_connected) {
    return { connection: "splunk_api", connected: true };
  }

  return { connection: "offline", connected: false };
}

function normalizeConnection(value: string): string {
  if (value === "rest") return "splunk_api";
  if (value === "mcp") return "splunk_mcp";
  if (value === "fallback") return "offline";
  return value;
}