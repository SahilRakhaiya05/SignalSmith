import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { api } from "../api";
import { canRunStep, getWorkflowSnapshot, type PipelineStepId } from "../lib/workflow";
import type { Analysis, AuditEntry, ComparisonSummary, IntegrationStatus, LiveAnalytics, Proposal, SessionContextValue, Validation } from "../types";
import { resolveSplunkConnection } from "../utils/splunkConnection";
import { clearSplunkAuth, getSplunkAuth } from "../utils/splunkAuth";

const SessionContext = createContext<SessionContextValue | null>(null);

async function pollJob(jobId: string, onProgress: (p: number, m: string) => void): Promise<void> {
  for (let i = 0; i < 600; i++) {
    const job = await api.getJob(jobId);
    onProgress(job.progress || 0, job.message || "");
    if (job.status === "completed") return;
    if (job.status === "failed") throw new Error(job.error || "Job failed");
    await new Promise((r) => setTimeout(r, 800));
  }
  throw new Error("Job timed out");
}

async function waitForJob(jobId: string, onProgress: (p: number, m: string) => void): Promise<void> {
  if (getSplunkAuth()) {
    return pollJob(jobId, onProgress);
  }
  return new Promise((resolve, reject) => {
    const es = new EventSource(`${import.meta.env.VITE_API_URL || ""}/api/jobs/${jobId}/stream`);
    es.onmessage = (ev) => {
      const job = JSON.parse(ev.data);
      onProgress(job.progress || 0, job.message || "");
      if (job.status === "completed") {
        es.close();
        resolve();
      }
      if (job.status === "failed") {
        es.close();
        reject(new Error(job.error || "Job failed"));
      }
    };
    es.onerror = () => {
      es.close();
      reject(new Error("Job stream disconnected"));
    };
  });
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [splunkConnection, setSplunkConnection] = useState("offline");
  const [splunkConnected, setSplunkConnected] = useState(false);
  const [apiOnline, setApiOnline] = useState(true);
  const [booting, setBooting] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState("");
  const [jobProgress, setJobProgress] = useState(0);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [validations, setValidations] = useState<Validation[]>([]);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [serviceData, setServiceData] = useState<Array<{ service: string; count: number }>>([]);
  const [categoryData, setCategoryData] = useState<Array<{ category: string; count: number }>>([]);
  const [comparison, setComparison] = useState<ComparisonSummary | null>(null);
  const [integrations, setIntegrations] = useState<IntegrationStatus | null>(null);
  const [splunkCounts, setSplunkCounts] = useState<Record<string, number>>({});
  const [liveAnalytics, setLiveAnalytics] = useState<LiveAnalytics | null>(null);
  const [liveAnalyticsLoading, setLiveAnalyticsLoading] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState<string | null>(null);
  const [splunkAuthed, setSplunkAuthed] = useState(() => Boolean(getSplunkAuth()));
  const [splunkUser, setSplunkUser] = useState<string | null>(() => getSplunkAuth()?.username ?? null);
  const stepInFlight = useRef(false);

  const workflowSnapshot = useMemo(
    () => getWorkflowSnapshot({ analysis, proposal, validations }),
    [analysis, proposal, validations]
  );

  const hydrateFromStatus = useCallback(async (analysisId: string) => {
    const events = await api.getAnalysisEvents(analysisId);
    setServiceData(events.service_distribution.map((d) => ({ service: d.service, count: d.count })));
    setCategoryData(events.category_distribution.map((d) => ({ category: d.category, count: d.count })));
    try {
      setComparison(await api.getComparison(analysisId));
    } catch {
      setComparison(null);
    }
    try {
      setAudit((await api.getAudit()).entries);
    } catch {
      setAudit([]);
    }
  }, []);

  const fetchLiveAnalytics = useCallback(async (connected: boolean) => {
    if (!connected) {
      setLiveAnalytics(null);
      return;
    }
    setLiveAnalyticsLoading(true);
    try {
      setLiveAnalytics(await api.getSplunkLiveAnalytics());
    } catch {
      setLiveAnalytics(null);
    } finally {
      setLiveAnalyticsLoading(false);
    }
  }, []);

  const refreshSession = useCallback(async () => {
    setRefreshing(true);
    try {
      const [status, ints] = await Promise.all([api.getStatus(), api.getIntegrations()]);
      const resolved = resolveSplunkConnection(status, ints);
      setSplunkConnection(resolved.connection);
      setSplunkConnected(resolved.connected);
      setIntegrations(ints);
      if (ints.splunk_auth?.username) {
        setSplunkUser(ints.splunk_auth.username);
      } else if (getSplunkAuth()?.username) {
        setSplunkUser(getSplunkAuth()!.username);
      }
      setSplunkCounts(status.splunk_index_counts || {});
      setApiOnline(true);
      await fetchLiveAnalytics(resolved.connected);
      if (status.analysis) {
        setAnalysis(status.analysis);
        await hydrateFromStatus(status.analysis.id);
      } else {
        setAnalysis(null);
        setServiceData([]);
        setCategoryData([]);
        setComparison(null);
      }
      setProposal(status.proposal || null);
      setValidations(status.validations?.length ? status.validations : []);
      setLastRefreshed(new Date().toLocaleTimeString());
    } catch {
      setApiOnline(false);
      try {
        const h = await api.health();
        const resolved = resolveSplunkConnection({}, null, h);
        setSplunkConnection(resolved.connection);
        setSplunkConnected(resolved.connected);
        setApiOnline(true);
      } catch {
        setSplunkConnection("offline");
        setSplunkConnected(false);
      }
    } finally {
      setBooting(false);
      setRefreshing(false);
    }
  }, [hydrateFromStatus, fetchLiveAnalytics]);

  useEffect(() => {
    refreshSession();
  }, [refreshSession]);

  const runStep = async (fn: () => Promise<void>, label: string) => {
    if (stepInFlight.current) return;
    stepInFlight.current = true;
    setLoading(true);
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError(`${label}: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      stepInFlight.current = false;
      setLoading(false);
      setProgress("");
      setJobProgress(0);
    }
  };

  const runWorkflowStep = async (step: PipelineStepId) => {
    if (!canRunStep(step, workflowSnapshot)) {
      setError(`Complete prior pipeline steps before running "${step}".`);
      return;
    }
    await runStep(async () => {
      setProgress(`Running ${step}...`);
      switch (step) {
        case "bootstrap": {
          const r = await api.bootstrap();
          setProgress(`Loaded ${r.exported_events.toLocaleString()} events from Splunk (${r.splunk_event_count.toLocaleString()} in index)`);
          break;
        }
        case "analyze": {
          const start = await api.startAnalysis();
          setAnalysis(await api.getAnalysis(start.analysis_id));
          setProposal(await api.getProposal(start.analysis_id));
          break;
        }
        case "apply": {
          if (!proposal) throw new Error("No policy proposal available");
          await api.applyProposal(proposal.id);
          const job = await api.ingestCandidate(true);
          if (job.job_id) {
            await waitForJob(job.job_id, (p, m) => {
              setJobProgress(p);
              setProgress(m);
            });
          }
          break;
        }
        case "validate": {
          if (!proposal) throw new Error("No policy proposal available");
          setValidations([await api.runValidation(proposal.id)]);
          break;
        }
        case "revise": {
          const v1 = validations[0];
          if (!v1) throw new Error("Run validation first");
          const revised = await api.reviseValidation(v1.id);
          setProposal(revised.proposal);
          setValidations([v1, revised.validation]);
          break;
        }
        case "approve": {
          if (!proposal) throw new Error("No policy proposal available");
          await api.approveProposal(proposal.id);
          setProposal({ ...proposal, status: "approved" });
          break;
        }
      }
      await refreshSession();
    }, step);
  };

  const loadSession = useCallback(
    async (analysisId: string) => {
      setLoading(true);
      setRefreshing(true);
      setError(null);
      try {
        const a = await api.getAnalysis(analysisId);
        setAnalysis(a);
        await hydrateFromStatus(analysisId);
        try {
          setProposal(await api.getProposal(analysisId));
        } catch {
          setProposal(null);
        }
        setValidations([]);
        setLastRefreshed(new Date().toLocaleTimeString());
      } catch (e) {
        setError(`Load session: ${e instanceof Error ? e.message : String(e)}`);
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [hydrateFromStatus]
  );

  const completeSplunkAuth = useCallback(() => {
    const auth = getSplunkAuth();
    setSplunkAuthed(Boolean(auth));
    setSplunkUser(auth?.username ?? null);
    void refreshSession();
  }, [refreshSession]);

  const logoutSplunk = useCallback(() => {
    clearSplunkAuth();
    setSplunkAuthed(false);
    setSplunkUser(null);
    void refreshSession();
  }, [refreshSession]);

  const runFullPipeline = () =>
    runStep(async () => {
      setProgress("Starting full pipeline...");
      const started = await api.runFullSession(true);
      if ("job_id" in started && started.job_id) {
        await waitForJob(started.job_id, (p, m) => {
          setJobProgress(p);
          setProgress(m || "Running pipeline...");
        });
      } else if ("event_reduction_percent" in started) {
        setProgress(
          `Pipeline complete — ${started.event_reduction_percent}% reduction, ${started.coverage_percent}% detection coverage`
        );
      }
      await refreshSession();
    }, "Full pipeline");

  const value: SessionContextValue = {
    splunkConnection,
    splunkConnected,
    splunkUser,
    splunkAuthed,
    completeSplunkAuth,
    logoutSplunk,
    apiOnline,
    loading,
    initializing: booting,
    sessionLoading: booting || refreshing || (splunkConnected && liveAnalyticsLoading),
    error,
    progress,
    jobProgress,
    analysis,
    proposal,
    validations,
    audit,
    serviceData,
    categoryData,
    comparison,
    integrations,
    splunkCounts,
    liveAnalytics,
    liveAnalyticsLoading,
    lastRefreshed,
    workflowSnapshot,
    refreshSession,
    loadSession,
    runStep,
    runFullPipeline,
    runWorkflowStep,
    setError,
  };

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used within SessionProvider");
  return ctx;
}