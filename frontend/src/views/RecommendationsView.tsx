import { Link } from "react-router-dom";
import { useSession } from "../context/SessionContext";
import { PageHeader } from "../components/ui/PageHeader";
import { PageLoadGate } from "../components/ui/PageLoadGate";
import { CardGridSkeleton, PageHeaderSkeleton } from "../components/ui/Skeleton";
import { EmptyState } from "../components/ui/EmptyState";

function PoliciesSkeleton() {
  return (
    <div className="page-skeleton">
      <PageHeaderSkeleton />
      <CardGridSkeleton count={4} />
    </div>
  );
}

export function RecommendationsView() {
  const { proposal, sessionLoading } = useSession();

  return (
    <PageLoadGate loading={sessionLoading} skeleton={<PoliciesSkeleton />}>
      <PageHeader
        title="Policies"
        description="Filtering and sampling recommendations with SPL evidence and risk assessment."
      />

      {proposal ? (
        <div className="card-grid">
          {proposal.recommendations.map((rec) => (
            <div key={rec.id} className="rec-card">
              <h4>{rec.action.toUpperCase()}: {rec.id}</h4>
              <p className="muted">{rec.reasoning}</p>
              <div className="action-row" style={{ marginTop: 0 }}>
                <span>Events: <strong>{rec.affected_event_count.toLocaleString()}</strong></span>
                <span>Reduction: <strong>{rec.estimated_reduction.toLocaleString()}</strong></span>
                <span className={`risk-${rec.risk_level}`}>Risk: {rec.risk_level}</span>
              </div>
              <div className="spl-code">{rec.spl_query}</div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState
          title="No policies yet"
          description="Complete the analyze step to generate optimization recommendations."
          action={<Link to="/workflow" className="btn btn-primary">Open pipeline</Link>}
        />
      )}
    </PageLoadGate>
  );
}