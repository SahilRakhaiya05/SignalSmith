import { Link } from "react-router-dom";
import { useSession } from "../context/SessionContext";
import { PageHeader } from "../components/ui/PageHeader";
import { PageLoadGate } from "../components/ui/PageLoadGate";
import { GenericPageSkeleton } from "../components/ui/Skeleton";
import { EmptyState } from "../components/ui/EmptyState";

export function ProtectionView() {
  const { analysis, sessionLoading } = useSession();

  return (
    <PageLoadGate loading={sessionLoading} skeleton={<GenericPageSkeleton />}>
      <PageHeader
        title="Protection map"
        description="Events and patterns that must never be dropped or sampled away during optimization."
      />

      {analysis?.protection_map?.length ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Rule</th><th>Reason</th><th>Events</th><th>% of total</th></tr>
            </thead>
            <tbody>
              {analysis.protection_map.map((rule) => (
                <tr key={rule.rule_id}>
                  <td><code>{rule.rule_id}</code></td>
                  <td>{rule.reason}</td>
                  <td>{rule.event_count.toLocaleString()}</td>
                  <td>{rule.percent ?? "—"}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState
          title="No protection rules"
          description="Run analysis to build the protection map from your baseline telemetry."
          action={<Link to="/workflow" className="btn btn-primary">Open pipeline</Link>}
        />
      )}
    </PageLoadGate>
  );
}