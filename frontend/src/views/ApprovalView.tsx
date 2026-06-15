import { useState } from "react";
import { Link } from "react-router-dom";
import { api, downloadText } from "../api";
import { useSession } from "../context/SessionContext";
import { PageHeader } from "../components/ui/PageHeader";
import { PageLoadGate } from "../components/ui/PageLoadGate";
import { GenericPageSkeleton } from "../components/ui/Skeleton";
import { EmptyState } from "../components/ui/EmptyState";

export function ApprovalView() {
  const { proposal, validations, audit, loading, sessionLoading, runStep, refreshSession } = useSession();
  const [otelYaml, setOtelYaml] = useState("");
  const [rollbackYaml, setRollbackYaml] = useState("");

  const passedValidation = validations.some(
    (v) => v.status === "passed" || (v.tests_passed === v.tests_total && v.protected_events_lost === 0)
  );
  const latestValidation = validations[validations.length - 1];

  return (
    <PageLoadGate loading={sessionLoading} skeleton={<GenericPageSkeleton />}>
      {!proposal ? (
        <>
          <PageHeader title="Approval" description="Human approval gate before deploying telemetry policies to collectors." />
          <EmptyState
            title="No proposal ready"
            description="Complete analysis and validation before requesting approval."
            action={<Link to="/workflow" className="btn btn-primary">Open pipeline</Link>}
          />
        </>
      ) : (
        <>
          <PageHeader
            title="Approval & export"
            description="Review validation evidence and export OpenTelemetry collector configuration."
            badge={
              proposal.status === "approved" ? (
                <span className="data-badge data-badge--live">Approved</span>
              ) : undefined
            }
          />

          <div className="alert alert-warning">Review and test in a staging collector before production deployment.</div>

          <div className="checklist-pro">
            <label><input type="checkbox" readOnly checked={proposal.recommendations.length > 0} /> Policy recommendations generated</label>
            <label><input type="checkbox" readOnly checked={!!latestValidation} /> Shadow validation executed</label>
            <label><input type="checkbox" readOnly checked={passedValidation} /> All saved searches pass</label>
            <label><input type="checkbox" readOnly checked={(latestValidation?.protected_events_lost ?? 1) === 0} /> Zero protected events lost</label>
            <label><input type="checkbox" /> Tested in staging collector</label>
            <label><input type="checkbox" /> Rollback plan documented</label>
          </div>

          <div className="action-row">
            <button
              type="button"
              className="btn btn-success"
              disabled={loading || proposal.status === "approved" || !passedValidation}
              onClick={() => runStep(async () => { await api.approveProposal(proposal.id); await refreshSession(); }, "Approve")}
            >
              Approve
            </button>
            <button
              type="button"
              className="btn btn-danger"
              disabled={loading}
              onClick={() => runStep(async () => { await api.rejectProposal(proposal.id); await refreshSession(); }, "Reject")}
            >
              Reject
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              disabled={loading}
              onClick={() =>
                runStep(async () => {
                  const y = await api.exportOtel(proposal.id);
                  setOtelYaml(y);
                  downloadText(`signalsmith-${proposal.id}-otel.yaml`, y);
                }, "Export")
              }
            >
              Download OTEL YAML
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              disabled={loading}
              onClick={() =>
                runStep(async () => {
                  const y = await api.exportRollback(proposal.id);
                  setRollbackYaml(y);
                  downloadText(`signalsmith-${proposal.id}-rollback.yaml`, y);
                }, "Export")
              }
            >
              Download rollback
            </button>
          </div>

          {otelYaml && <pre className="yaml-preview">{otelYaml.slice(0, 1500)}...</pre>}
          {rollbackYaml && <pre className="yaml-preview">{rollbackYaml.slice(0, 800)}...</pre>}

          <h3 className="section-title">Audit trail</h3>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Source</th><th>Output</th></tr></thead>
              <tbody>
                {audit.length > 0 ? (
                  audit.map((e) => (
                    <tr key={e.id}>
                      <td>{new Date(e.timestamp).toLocaleString()}</td>
                      <td>{e.actor}</td>
                      <td>{e.action}</td>
                      <td><code>{e.source}</code></td>
                      <td className="truncate">{e.output_summary}</td>
                    </tr>
                  ))
                ) : (
                  <tr><td colSpan={5} className="muted">No audit entries yet.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </PageLoadGate>
  );
}