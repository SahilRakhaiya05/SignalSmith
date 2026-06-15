export interface HealthResponse {
  status: string;
  service: string;
  splunk_connection?: string;
  splunk_connected?: boolean;
  /** @deprecated legacy API field */
  mode?: string;
  tagline: string;
  version?: string;
}

export interface PolicyRecommendation {
  id: string;
  action: string;
  condition: string;
  affected_event_count: number;
  estimated_reduction: number;
  risk_level: string;
  reasoning: string;
  spl_query: string;
  affected_saved_searches: string[];
  approval_status: string;
}

export interface Proposal {
  id: string;
  analysis_id: string;
  status: string;
  version: number;
  recommendations: PolicyRecommendation[];
  total_reduction_estimate: number;
  total_reduction_percent: number;
  notes: string;
}

export interface AgentAction {
  timestamp: string;
  agent: string;
  action: string;
  source: string;
  detail: string;
  status: string;
}

export interface Analysis {
  id: string;
  status: string;
  mode: string;
  progress: number;
  message: string;
  baseline_event_count: number;
  baseline_bytes: number;
  services: string[];
  event_types: string[];
  saved_searches: Array<{ id: string; name: string; description: string }>;
  reducible_estimate: number;
  profile_summary: Record<string, unknown>;
  protection_map: Array<{ rule_id: string; reason: string; event_count: number; percent?: number }>;
  agent_timeline: AgentAction[];
}

export interface SearchCoverageResult {
  search_id: string;
  search_name: string;
  baseline_count: number;
  candidate_count: number;
  baseline_triggered: boolean;
  candidate_triggered: boolean;
  passed: boolean;
  importance: string;
  detail: string;
  validation_method?: string;
}

export interface Validation {
  id: string;
  proposal_id: string;
  run_number: number;
  status: string;
  mode: string;
  baseline_event_count: number;
  candidate_event_count: number;
  event_reduction_percent: number;
  byte_reduction_percent: number;
  coverage_percent: number;
  protected_events_lost: number;
  tests_passed: number;
  tests_total: number;
  final_risk_level: string;
  coverage_results: SearchCoverageResult[];
  failure_reason: string | null;
  revision_applied: boolean;
  revision_detail: string | null;
}

export interface AuditEntry {
  id: string;
  timestamp: string;
  actor: string;
  action: string;
  source: string;
  input_summary: string;
  output_summary: string;
  analysis_id: string | null;
  proposal_id: string | null;
}

import type { PipelineStepId, WorkflowSnapshot } from "./lib/workflow";

export interface SessionStatus {
  has_data: boolean;
  splunk_connected?: boolean;
  splunk_connection?: string;
  /** @deprecated legacy API field */
  runtime_mode?: string;
  baseline_event_count: number;
  baseline_bytes: number;
  candidate_event_count: number;
  candidate_bytes: number;
  splunk_index_counts?: Record<string, number>;
  data_source?: string;
  analysis: Analysis | null;
  proposal: Proposal | null;
  validations: Validation[];
}

export interface JobRecord {
  id: string;
  name: string;
  status: string;
  progress: number;
  message: string;
  result?: Record<string, unknown>;
  error?: string;
}

export interface DataFlowInfo {
  source_label?: string;
  dataset_generated?: string;
  splunk_connection_meta?: string;
  baseline_index?: string;
  candidate_index?: string;
  local_baseline_events?: number;
  local_candidate_events?: number;
  local_baseline_bytes?: number;
  local_candidate_bytes?: number;
  splunk_baseline_events?: number;
  splunk_candidate_events?: number;
}

export interface IntegrationStatus {
  splunk_connection: string;
  data_flow?: DataFlowInfo;
  splunk: {
    host: string;
    api_port?: number;
    api_scheme?: string;
    api_url?: string;
    web_port?: number;
    web_scheme?: string;
    web_url?: string;
    mcp_endpoint?: string;
    hec_port?: number;
    baseline_index?: string;
    candidate_index?: string;
    mode: string;
    rest_api: { reachable: boolean };
    hec: { configured: boolean; reachable: boolean };
    indexes: Record<string, { exists: boolean; event_count?: number }>;
    ingest_mode: string;
  };
  mcp: {
    mode: string;
    available: boolean;
    endpoint?: string;
    server_name?: string | null;
    server_version?: string | null;
    tools?: string[];
    official_tools?: string[];
    last_error?: string | null;
    status_note?: string | null;
    uses_splunk_api?: boolean;
    app_7931?: {
      splunkbase_app_id: string;
      splunkbase_url: string;
      installed: boolean;
      app_name?: string | null;
      version?: string | null;
      mcp_endpoint: string;
      mcp_reachable: boolean;
      mcp_server_name?: string;
      install_steps?: string[];
    };
    recent_calls?: Array<{
      tool: string;
      source: string;
      success: boolean;
      summary: string;
      duration_ms: number;
    }>;
  };
  ai?: {
    configured: boolean;
    available: boolean;
    model?: string | null;
    provider?: string | null;
    display_name?: string | null;
    auth_ok?: boolean;
    auth_hint?: string | null;
    key_type?: "standard" | "auth" | null;
    setup_url?: string;
    gcp_credentials_url?: string;
  };
  splunk_dashboard?: {
    name: string;
    label: string;
    deployed: boolean;
    url: string;
    browse_url?: string;
    splunk_web: string;
    app: string;
  };
  splunk_auth?: {
    authenticated: boolean;
    username?: string | null;
    source?: "session" | "env";
    web_url?: string;
    api_url?: string;
  };
  saved_searches: number;
  data_source?: string;
  connection_detail?: {
    mode: string;
    query_engine: string;
    reason: string;
    mcp_installed: boolean;
    mcp_reachable: boolean;
    indexes_live: boolean;
    telemetry_origin: string;
  };
}

export interface ComparisonSummary {
  analysis_id: string;
  baseline: { events: number; bytes: number };
  candidate: { events: number; bytes: number };
  event_reduction_percent: number;
  byte_reduction_percent: number;
  coverage_percent: number;
  by_service: Record<string, number>;
  by_scenario: Record<string, number>;
}

export interface LiveAnalytics {
  source: string;
  mcp_mode: string;
  official_mcp: boolean;
  query_source?: string;
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
}

export interface SessionContextValue {
  splunkConnection: string;
  splunkConnected: boolean;
  splunkUser: string | null;
  splunkAuthed: boolean;
  completeSplunkAuth: () => void;
  logoutSplunk: () => void;
  apiOnline: boolean;
  loading: boolean;
  initializing: boolean;
  sessionLoading: boolean;
  error: string | null;
  progress: string;
  jobProgress: number;
  analysis: Analysis | null;
  proposal: Proposal | null;
  validations: Validation[];
  audit: AuditEntry[];
  serviceData: Array<{ service: string; count: number }>;
  categoryData: Array<{ category: string; count: number }>;
  comparison: ComparisonSummary | null;
  integrations: IntegrationStatus | null;
  splunkCounts: Record<string, number>;
  liveAnalytics: LiveAnalytics | null;
  liveAnalyticsLoading: boolean;
  lastRefreshed: string | null;
  workflowSnapshot: WorkflowSnapshot;
  refreshSession: () => Promise<void>;
  loadSession: (analysisId: string) => Promise<void>;
  runStep: (fn: () => Promise<void>, label: string) => Promise<void>;
  runFullPipeline: () => Promise<void>;
  runWorkflowStep: (step: PipelineStepId) => Promise<void>;
  setError: (e: string | null) => void;
}