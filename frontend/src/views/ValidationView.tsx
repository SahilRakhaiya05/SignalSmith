import { Link } from "react-router-dom";
import { useSession } from "../context/SessionContext";
import { PageHeader } from "../components/ui/PageHeader";
import { PageLoadGate } from "../components/ui/PageLoadGate";
import { GenericPageSkeleton } from "../components/ui/Skeleton";
import { EmptyState } from "../components/ui/EmptyState";

export function ValidationView() {
  const { validations, sessionLoading } = useSession();
  const latest = validations[validations.length - 1];
  const first = validations.find((v) => v.run_number === 1) ?? latest;
  const second = validations.find((v) => v.run_number === 2);
  const display = second ?? first;

  return (
    <PageLoadGate loading={sessionLoading} skeleton={<GenericPageSkeleton />}>
      <PageHeader title="Shadow validation" />

      {latest && (
        <div className="validation-summary">
          <div>
            <span>Status</span>
            <strong className={latest.status === "passed" ? "status-pass" : "status-fail"}>{latest.status}</strong>
          </div>
          <div>
            <span>Detections</span>
            <strong>
              {latest.tests_passed}/{latest.tests_total}
            </strong>
          </div>
          <div>
            <span>Coverage</span>
            <strong>{latest.coverage_percent}%</strong>
          </div>
          <div>
            <span>Reduction</span>
            <strong>{latest.event_reduction_percent}%</strong>
          </div>
          <div>
            <span>Protected lost</span>
            <strong>{latest.protected_events_lost}</strong>
          </div>
        </div>
      )}

      {first?.status === "failed" && first.failure_reason && (
        <div className="alert-banner alert-banner--warning">{first.failure_reason}</div>
      )}
      {second?.revision_detail && <div className="alert-banner alert-banner--info">{second.revision_detail}</div>}

      {display?.coverage_results?.length ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Detection</th>
                <th>Baseline hits</th>
                <th>Candidate hits</th>
                {second ? <th>Before revise</th> : null}
                <th>Method</th>
                <th>Result</th>
              </tr>
            </thead>
            <tbody>
              {display.coverage_results.map((r) => {
                const before = second?.coverage_results.find((s) => s.search_id === r.search_id)
                  ?? first?.coverage_results.find((s) => s.search_id === r.search_id);
                return (
                  <tr key={r.search_id}>
                    <td>{r.search_name}</td>
                    <td>{r.baseline_count.toLocaleString()}</td>
                    <td>{r.candidate_count.toLocaleString()}</td>
                    {second ? <td>{before?.candidate_count.toLocaleString() ?? "—"}</td> : null}
                    <td>
                      <span className="source-tag" title={r.detail}>
                        {r.validation_method || "local"}
                      </span>
                    </td>
                    <td className={r.passed ? "status-pass" : "status-fail"}>{r.passed ? "PASS" : "FAIL"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState
          title="No validation yet"
          description="Run the validate step in the pipeline."
          action={
            <Link to="/workflow" className="btn btn-primary">
              Pipeline
            </Link>
          }
        />
      )}
    </PageLoadGate>
  );
}