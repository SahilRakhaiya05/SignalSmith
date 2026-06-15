import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useSession } from "../context/SessionContext";
import { PageHeader } from "../components/ui/PageHeader";
import { PageLoadGate } from "../components/ui/PageLoadGate";
import { PageHeaderSkeleton, TableSkeleton } from "../components/ui/Skeleton";
import { EmptyState } from "../components/ui/EmptyState";

function HistorySkeleton() {
  return (
    <div className="page-skeleton">
      <PageHeaderSkeleton />
      <TableSkeleton rows={8} cols={6} />
    </div>
  );
}

export function HistoryView() {
  const [items, setItems] = useState<Array<{ id: string; status: string; mode: string; baseline_event_count: number; reducible_estimate: number }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const { loadSession, sessionLoading } = useSession();
  const navigate = useNavigate();

  useEffect(() => {
    setLoading(true);
    api
      .listAnalyses()
      .then((r) => setItems(r.analyses))
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, []);

  const openSession = async (id: string) => {
    setLoadingId(id);
    try {
      await loadSession(id);
      navigate("/analysis");
    } finally {
      setLoadingId(null);
    }
  };

  return (
    <PageLoadGate loading={loading || sessionLoading} skeleton={<HistorySkeleton />}>
      <PageHeader
        title="Run history"
        description="Past optimization sessions. Select a run to load its analysis into the active session."
      />

      {error && <div className="alert-banner alert-banner--danger">{error}</div>}

      {!error && items.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Analysis ID</th><th>Status</th><th>Mode</th><th>Events</th><th>Reducible</th><th></th></tr>
            </thead>
            <tbody>
              {items.map((a) => (
                <tr key={a.id}>
                  <td><code>{a.id.slice(0, 12)}…</code></td>
                  <td>{a.status}</td>
                  <td><span className="source-tag">{a.mode}</span></td>
                  <td>{a.baseline_event_count?.toLocaleString()}</td>
                  <td>{a.reducible_estimate?.toLocaleString()}</td>
                  <td>
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      disabled={loadingId === a.id}
                      onClick={() => openSession(a.id)}
                    >
                      {loadingId === a.id ? "Loading…" : "Load session"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!error && items.length === 0 && (
        <EmptyState title="No runs yet" description="Complete a pipeline run to see session history here." />
      )}
    </PageLoadGate>
  );
}