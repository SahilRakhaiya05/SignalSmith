import { Link } from "react-router-dom";
import { useSession } from "../context/SessionContext";
import { PageHeader } from "../components/ui/PageHeader";
import { PageLoadGate } from "../components/ui/PageLoadGate";
import { MetricCard } from "../components/ui/MetricCard";
import { DataFlowSkeleton } from "../components/ui/Skeleton";
import { PIPELINE_STEPS, isStepComplete } from "../lib/workflow";
import { isSplunkOnline } from "../utils/connectionDisplay";

const FLOW_STAGES = [
  {
    id: "ingest",
    title: "1. Source telemetry",
    desc: "Applications send logs to Splunk. SignalSmith reads from your baseline index — production data is never changed in place.",
    sources: ["Splunk indexes", "HEC ingest", "Synthetic demo data"],
  },
  {
    id: "bootstrap",
    title: "2. Bootstrap & export",
    desc: "Pipeline exports a sample (up to 25k events) from the baseline index via SPL/MCP, stores it locally for agent analysis.",
    sources: ["splunk_run_query / REST", "Local baseline_events.json"],
  },
  {
    id: "analyze",
    title: "3. Agent analysis",
    desc: "Discovery, profiler, protection map, and policy generator agents identify noise and build safe reduction rules.",
    sources: ["Saved searches catalog", "Profile statistics", "Protection rules"],
  },
  {
    id: "candidate",
    title: "4. Candidate index",
    desc: "Policies are applied to create a reduced candidate dataset. This is written to signalsmith_candidate in Splunk for live comparison.",
    sources: ["candidate_events.json", "Splunk candidate index"],
  },
  {
    id: "validate",
    title: "5. Shadow validation",
    desc: "Saved searches replay against baseline vs candidate. All detections must still trigger before approval.",
    sources: ["Replay validator", "Coverage report", "Live MCP counts"],
  },
  {
    id: "export",
    title: "6. Approve & deploy",
    desc: "Human approval unlocks OpenTelemetry collector YAML for production rollout at the source.",
    sources: ["OTel YAML", "Rollback YAML", "Audit trail"],
  },
];

export function DataFlowView() {
  const {
    integrations,
    splunkConnection,
    splunkCounts,
    liveAnalytics,
    analysis,
    proposal,
    validations,
    audit,
    comparison,
    workflowSnapshot,
    loading,
    sessionLoading,
    runFullPipeline,
  } = useSession();

  const baselineIndex = integrations?.splunk?.baseline_index || "signalsmith_baseline";
  const candidateIndex = integrations?.splunk?.candidate_index || "signalsmith_candidate";
  const baselineSplunk = splunkCounts[baselineIndex] || liveAnalytics?.baseline_events || 0;
  const candidateSplunk = splunkCounts[candidateIndex] || liveAnalytics?.candidate_events || 0;
  const dataFlow = integrations?.data_flow;
  const online = isSplunkOnline(splunkConnection);
  const localBaseline = dataFlow?.local_baseline_events || analysis?.baseline_event_count || 0;
  const localCandidate = dataFlow?.local_candidate_events || 0;
  const reduction =
    comparison?.event_reduction_percent ??
    (localBaseline > 0 && localCandidate > 0
      ? Math.round(100 * (1 - localCandidate / localBaseline))
      : liveAnalytics?.reduction_percent ?? null);

  const stepsDone = PIPELINE_STEPS.filter((s) => isStepComplete(s.id, workflowSnapshot)).length;
  const pipelinePct = Math.round((stepsDone / PIPELINE_STEPS.length) * 100);
  const latestVal = validations[validations.length - 1];
  const displayVal = validations.find((v) => v.run_number === 2) ?? latestVal;

  const recentDataOps = audit
    .filter((e) =>
      ["bootstrap", "apply_proposal", "ingest_candidate", "run_validation", "generate_spl", "chat"].some((a) =>
        e.action.includes(a)
      )
    )
    .slice(0, 10);

  return (
    <PageLoadGate loading={sessionLoading} skeleton={<DataFlowSkeleton />}>
      <PageHeader
        title="Data Flow"
        description="End-to-end path from Splunk baseline → agent policies → candidate index → shadow validation → approval."
        actions={
          <div className="btn-row">
            <Link to="/assistant" className="btn btn-secondary btn-sm">
              Ask Mentor
            </Link>
            <Link to="/splunk-dashboard" className="btn btn-secondary btn-sm">
              Splunk dashboard
            </Link>
            <Link to="/workflow" className="btn btn-secondary btn-sm">
              Pipeline steps
            </Link>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              disabled={loading || !online}
              onClick={runFullPipeline}
            >
              Run pipeline
            </button>
          </div>
        }
      />

      <div className="data-flow-summary">
        <MetricCard
          label="Baseline (Splunk)"
          value={baselineSplunk.toLocaleString()}
          sub={baselineIndex}
          highlight
          icon="database"
        />
        <MetricCard
          label="Session export"
          value={localBaseline.toLocaleString()}
          sub="baseline_events.json"
          icon="dataFlow"
        />
        <MetricCard
          label="Candidate (Splunk)"
          value={candidateSplunk > 0 ? candidateSplunk.toLocaleString() : "—"}
          sub={candidateIndex}
          icon="analytics"
        />
        <MetricCard
          label="Reduction"
          value={reduction != null ? `${Number(reduction).toFixed(1)}%` : "—"}
          sub="after policies"
          trend={reduction != null && reduction > 0 ? "up" : undefined}
          icon="outcomes"
        />
        <MetricCard
          label="Pipeline"
          value={`${stepsDone}/${PIPELINE_STEPS.length}`}
          sub={`${pipelinePct}% complete`}
          icon="pipeline"
        />
        <MetricCard
          label="Connection"
          value={splunkConnection === "splunk_mcp" ? "MCP" : online ? "Splunk" : "Offline"}
          sub={dataFlow?.source_label || "—"}
          icon="splunkDash"
        />
      </div>

      <div className="data-flow-diagram panel-pro">
        <div className="data-flow-diagram__head">
          <h3>Live data path</h3>
          <span className={`data-flow-live-badge ${online ? "on" : "off"}`}>
            {online ? "Splunk connected" : "Splunk offline"}
          </span>
        </div>
        <div className="data-flow-path">
          <div className="data-flow-node">
            <span className="data-flow-node__tag">Source</span>
            <strong>Apps & services</strong>
            <p>Logs, metrics, traces</p>
          </div>
          <div className="data-flow-arrow" aria-hidden="true" />
          <div className="data-flow-node data-flow-node--splunk">
            <span className="data-flow-node__tag">Splunk</span>
            <strong>{baselineIndex}</strong>
            <p>{baselineSplunk.toLocaleString()} events</p>
          </div>
          <div className="data-flow-arrow" aria-hidden="true" />
          <div className="data-flow-node data-flow-node--local">
            <span className="data-flow-node__tag">Session</span>
            <strong>baseline_events.json</strong>
            <p>{localBaseline.toLocaleString()} exported</p>
          </div>
          <div className="data-flow-arrow" aria-hidden="true" />
          <div className="data-flow-node data-flow-node--agents">
            <span className="data-flow-node__tag">Agents</span>
            <strong>Analysis & policies</strong>
            <p>{analysis?.status === "completed" ? `${proposal?.recommendations?.length ?? 0} policies` : "Pending"}</p>
          </div>
          <div className="data-flow-arrow" aria-hidden="true" />
          <div className="data-flow-node data-flow-node--splunk">
            <span className="data-flow-node__tag">Splunk</span>
            <strong>{candidateIndex}</strong>
            <p>{candidateSplunk > 0 ? `${candidateSplunk.toLocaleString()} events` : "After apply"}</p>
          </div>
          <div className="data-flow-arrow" aria-hidden="true" />
          <div className="data-flow-node data-flow-node--export">
            <span className="data-flow-node__tag">Export</span>
            <strong>OTel YAML</strong>
            <p>{proposal?.status === "approved" ? "Ready" : "After approval"}</p>
          </div>
        </div>
      </div>

      <div className="panel-pro data-flow-progress-panel">
        <div className="data-flow-progress-panel__head">
          <h3>Pipeline progress</h3>
          <span>{pipelinePct}%</span>
        </div>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${pipelinePct}%` }} />
        </div>
        <div className="data-flow-steps">
          {PIPELINE_STEPS.map((step) => (
            <div key={step.id} className={`data-flow-step-row ${isStepComplete(step.id, workflowSnapshot) ? "done" : ""}`}>
              <span className="data-flow-step-row__dot" />
              <div>
                <strong>{step.label}</strong>
                <span>{step.short}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="data-flow-grid">
        {FLOW_STAGES.map((stage) => {
          const stepId = stage.id === "ingest" ? null : stage.id === "export" ? "approve" : stage.id;
          const done = stepId ? isStepComplete(stepId as (typeof PIPELINE_STEPS)[number]["id"], workflowSnapshot) : online;
          return (
            <article key={stage.id} className={`data-flow-card ${done ? "done" : ""}`}>
              <div className="data-flow-card__head">
                <h3>{stage.title}</h3>
                <span className={`data-flow-card__status ${done ? "on" : "off"}`}>{done ? "Complete" : "Waiting"}</span>
              </div>
              <p>{stage.desc}</p>
              <ul>
                {stage.sources.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
            </article>
          );
        })}
      </div>

      {displayVal?.coverage_results?.length ? (
        <div className="panel-pro">
          <div className="panel-pro__head-row">
            <h3>Shadow validation</h3>
            <Link to="/validation" className="btn btn-ghost btn-sm">
              Full report
            </Link>
          </div>
          <p className="panel-pro__desc">
            {displayVal.tests_passed}/{displayVal.tests_total} detections passed · {displayVal.coverage_percent}% coverage ·{" "}
            {displayVal.protected_events_lost} protected events lost · {displayVal.event_reduction_percent}% reduction
          </p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Detection</th>
                  <th>Baseline</th>
                  <th>Candidate</th>
                  <th>Method</th>
                  <th>Result</th>
                </tr>
              </thead>
              <tbody>
                {displayVal.coverage_results.map((r) => (
                  <tr key={r.search_id}>
                    <td>{r.search_name}</td>
                    <td>{r.baseline_count.toLocaleString()}</td>
                    <td>{r.candidate_count.toLocaleString()}</td>
                    <td>
                      <span className="source-tag">{r.validation_method || "local"}</span>
                    </td>
                    <td className={r.passed ? "status-pass" : "status-fail"}>{r.passed ? "PASS" : "FAIL"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      {recentDataOps.length > 0 && (
        <div className="panel-pro">
          <h3>Recent data operations</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Actor</th>
                  <th>Action</th>
                  <th>Source</th>
                  <th>Result</th>
                </tr>
              </thead>
              <tbody>
                {recentDataOps.map((e) => (
                  <tr key={e.id}>
                    <td>{new Date(e.timestamp).toLocaleString()}</td>
                    <td>{e.actor}</td>
                    <td>
                      <code>{e.action}</code>
                    </td>
                    <td>{e.source}</td>
                    <td className="truncate">{e.output_summary}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="data-flow-safety panel-pro">
        <h3>Safety guarantees</h3>
        <ul>
          <li>Baseline production indexes are read-only — SignalSmith never deletes source telemetry.</li>
          <li>Candidate index is a shadow copy for comparison before any collector rollout.</li>
          <li>Every saved search must pass replay before approval; failed runs trigger automatic policy revise.</li>
          <li>Protected events (detection-critical traces) are counted and reported in validation.</li>
        </ul>
      </div>
    </PageLoadGate>
  );
}