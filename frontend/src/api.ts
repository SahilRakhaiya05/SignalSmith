import type {
  Analysis,
  AuditEntry,
  ComparisonSummary,
  HealthResponse,
  IntegrationStatus,
  JobRecord,
  Proposal,
  SessionStatus,
  Validation,
} from "./types";

import { splunkAuthHeaders } from "./utils/splunkAuth";

const API_URL = import.meta.env.VITE_API_URL || "";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...splunkAuthHeaders(),
      ...options?.headers,
    },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    try {
      const json = JSON.parse(text) as { detail?: string };
      if (typeof json.detail === "string") {
        throw new Error(json.detail);
      }
    } catch (parseErr) {
      if (parseErr instanceof Error && parseErr.message !== text) {
        throw parseErr;
      }
    }
    throw new Error(text || `Request failed: ${response.status}`);
  }
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.text() as Promise<T>;
}

export const api = {
  health: () => request<HealthResponse>("/api/health"),
  getStatus: () => request<SessionStatus>("/api/session/status"),
  bootstrap: () =>
    request<{ exported_events: number; splunk_event_count: number; export_source: string }>(
      "/api/session/bootstrap",
      { method: "POST", body: "{}" }
    ),
  runFullSession: (asyncJob = true) =>
    request<
      | {
          analysis_id: string;
          proposal_id: string;
          validation_status: string;
          event_reduction_percent: number;
          coverage_percent: number;
        }
      | { job_id: string; status: string }
    >(`/api/session/run${asyncJob ? "?async_job=true" : ""}`, { method: "POST" }),
  resetSession: () => request<{ status: string }>("/api/session/reset", { method: "POST" }),
  getIntegrations: () => request<IntegrationStatus>("/api/integrations/status"),
  getComparison: (analysisId: string) => request<ComparisonSummary>(`/api/comparison/${analysisId}`),
  listAnalyses: () => request<{ analyses: Array<{ id: string; status: string; mode: string; baseline_event_count: number; reducible_estimate: number }> }>("/api/analyses"),
  getSavedSearches: () => request<{ saved_searches: Array<{ id: string; name: string; description: string; spl_template: string; importance: string }> }>("/api/saved-searches"),
  ingestCandidate: (asyncJob = false) =>
    request<{ job_id?: string }>(`/api/session/ingest-candidate${asyncJob ? "?async_job=true" : ""}`, { method: "POST" }),
  getJob: (jobId: string) => request<JobRecord>(`/api/jobs/${jobId}`),
  startAnalysis: () =>
    request<{ analysis_id: string; status: string }>("/api/analysis/start", { method: "POST" }),
  getAnalysis: (id: string) => request<Analysis>(`/api/analysis/${id}`),
  getAnalysisEvents: (id: string) =>
    request<{
      service_distribution: Array<{ service: string; count: number; percent: number }>;
      category_distribution: Array<{ category: string; count: number; percent: number }>;
    }>(`/api/analysis/${id}/events`),
  getProposal: (analysisId: string) => request<Proposal>(`/api/proposals/${analysisId}`),
  applyProposal: (proposalId: string) =>
    request<{ candidate_event_count: number }>(`/api/proposals/${proposalId}/apply`, { method: "POST" }),
  runValidation: (proposalId: string) =>
    request<Validation>(`/api/validation/${proposalId}/run`, { method: "POST" }),
  reviseValidation: (validationId: string) =>
    request<{ proposal: Proposal; validation: Validation }>(`/api/validation/${validationId}/revise`, { method: "POST" }),
  approveProposal: (proposalId: string) =>
    request<{ status: string }>(`/api/proposals/${proposalId}/approve`, { method: "POST" }),
  rejectProposal: (proposalId: string) =>
    request<{ status: string }>(`/api/proposals/${proposalId}/reject`, { method: "POST" }),
  exportOtel: (proposalId: string) => request<string>(`/api/proposals/${proposalId}/export/otel`),
  exportRollback: (proposalId: string) => request<string>(`/api/proposals/${proposalId}/export/rollback`),
  getAudit: () => request<{ entries: AuditEntry[] }>("/api/audit"),
  getMcpStatus: () => request<Record<string, unknown>>("/api/mcp/status"),
  getMcpTools: () => request<{ tools: Array<{ name: string; description?: string }>; mode: string; official_mcp: boolean }>("/api/mcp/tools"),
  callMcpTool: (name: string, toolArgs?: Record<string, unknown>) =>
    request<{ tool: string; source: string; result: unknown }>("/api/mcp/tools/call", {
      method: "POST",
      body: JSON.stringify({ name, arguments: toolArgs }),
    }),
  generateSpl: (query: string) =>
    request<{ spl: string; source: string; query: string; official_mcp: boolean }>("/api/mcp/generate-spl", {
      method: "POST",
      body: JSON.stringify({ query }),
    }),
  runMcpQuery: (query: string) =>
    request<{ source: string; result: unknown; query: string }>("/api/mcp/run-query", {
      method: "POST",
      body: JSON.stringify({ query }),
    }),
  getSplunkMcpApp: () =>
    request<{
      splunkbase_app_id: string;
      splunkbase_url: string;
      installed: boolean;
      app_name?: string | null;
      version?: string | null;
      mcp_endpoint: string;
      mcp_reachable: boolean;
      mcp_server_name?: string;
      install_steps: string[];
    }>("/api/splunk/mcp-app"),
  getSplunkDashboard: () =>
    request<{
      name: string;
      label: string;
      deployed: boolean;
      url: string;
      browse_url?: string;
      splunk_web: string;
      app: string;
    }>("/api/splunk/dashboard"),
  getSplunkDashboardXml: () => request<string>("/api/splunk/dashboard/xml"),
  deploySplunkDashboard: () =>
    request<{ status: string; name: string; url: string; browse_url?: string; message: string }>("/api/splunk/dashboard/deploy", {
      method: "POST",
    }),
  getSplunkLiveAnalytics: () =>
    request<{
      source: string;
      mcp_mode: string;
      official_mcp: boolean;
      baseline_index: string;
      candidate_index: string;
      baseline_events: number;
      candidate_events: number;
      reduction_percent: number | null;
      charts: {
        index_comparison: Array<{ name: string; value: number }>;
        events_by_service: Array<{ service: string; count: number }>;
        events_by_scenario: Array<{ scenario: string; count: number }>;
        events_by_level: Array<{ level: string; count: number }>;
        health_check_noise?: Array<{ service: string; count: number }>;
        service_comparison?: Array<{ service: string; baseline: number; candidate: number }>;
      };
      query_source?: string;
      panels: Record<string, { spl: string; rows: unknown[]; source?: string; error?: string }>;
    }>("/api/splunk/analytics/live"),
  getAgents: () =>
    request<{
      agents: Array<{
        id: string;
        name: string;
        phase: string;
        track: string;
        description: string;
        capabilities: string[];
        human_in_loop: boolean;
        ran_in_session?: boolean;
        action_count?: number;
      }>;
      timeline_actions: number;
      active_agents: number;
    }>("/api/agents"),
  getAiStatus: () =>
    request<{
      configured: boolean;
      available: boolean;
      model?: string;
      provider?: string;
      auth_ok?: boolean;
      auth_hint?: string;
      key_type?: "standard" | "auth" | null;
      setup_url?: string;
      gcp_credentials_url?: string;
    }>("/api/ai/status"),
  aiChat: (message: string, history?: Array<{ role: string; content: string }>) =>
    request<{ reply: string; model: string; source: string }>("/api/ai/chat", {
      method: "POST",
      body: JSON.stringify({ message, history, include_session: true }),
    }),
  aiExplain: (topic: string) =>
    request<{ reply: string; model: string; source: string }>("/api/ai/explain", {
      method: "POST",
      body: JSON.stringify({ topic, include_session: true }),
    }),
  splunkAuthStatus: () =>
    request<{
      authenticated: boolean;
      username?: string;
      source?: string;
      connection?: string;
      web_url?: string;
      api_url?: string;
      host?: string;
    }>("/api/splunk/auth/status"),
  splunkLogin: (username: string, password: string) =>
    request<{
      authenticated: boolean;
      username: string;
      splunk_connected: boolean;
      connection?: string;
      server_name?: string;
    }>("/api/splunk/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
};

export function downloadText(filename: string, content: string) {
  const blob = new Blob([content], { type: "text/yaml" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}