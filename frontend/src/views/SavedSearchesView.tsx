import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { PageHeader } from "../components/ui/PageHeader";
import { PageLoadGate } from "../components/ui/PageLoadGate";
import { CardGridSkeleton, PageHeaderSkeleton, Skeleton } from "../components/ui/Skeleton";
import { EmptyState } from "../components/ui/EmptyState";

function SearchesSkeleton() {
  return (
    <div className="page-skeleton">
      <PageHeaderSkeleton />
      <Skeleton style={{ height: "2.5rem", marginBottom: "1rem" }} />
      <CardGridSkeleton count={6} />
    </div>
  );
}

export function SavedSearchesView() {
  const [searches, setSearches] = useState<Array<{ id: string; name: string; description: string; spl_template: string; importance: string; trigger_threshold?: number }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [importance, setImportance] = useState("all");

  useEffect(() => {
    setLoading(true);
    api
      .getSavedSearches()
      .then((r) => setSearches(r.saved_searches))
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return searches.filter((s) => {
      const importanceMatch = importance === "all" || s.importance === importance;
      const searchMatch =
        !q ||
        s.name.toLowerCase().includes(q) ||
        s.description.toLowerCase().includes(q) ||
        s.spl_template.toLowerCase().includes(q) ||
        s.id.toLowerCase().includes(q);
      return importanceMatch && searchMatch;
    });
  }, [searches, query, importance]);

  return (
    <PageLoadGate loading={loading} skeleton={<SearchesSkeleton />}>
      <PageHeader
        title="Detections"
        description="Operational and security saved searches validated during shadow replay — search and filter the detection catalog."
      />

      <div className="panel-pro__toolbar panel-pro__toolbar--standalone">
        <input
          type="search"
          className="search-input search-input--wide"
          placeholder="Search detections by name, SPL, or description…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Search detections"
        />
        <select className="select-input" value={importance} onChange={(e) => setImportance(e.target.value)} aria-label="Filter by importance">
          <option value="all">All importance</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
        </select>
        <span className="search-count">{filtered.length} of {searches.length}</span>
      </div>

      {error && <div className="alert-banner alert-banner--danger">{error}</div>}

      {!error && filtered.length > 0 && (
        <div className="card-grid">
          {filtered.map((s) => (
            <div key={s.id} className="rec-card">
              <h4>{s.name}</h4>
              <p className="muted">{s.description}</p>
              <span className={`risk-${s.importance === "critical" ? "high" : "medium"}`}>{s.importance}</span>
              <div className="spl-code">{s.spl_template}</div>
            </div>
          ))}
        </div>
      )}

      {!error && searches.length > 0 && filtered.length === 0 && (
        <EmptyState title="No matches" description="Try a different search term or importance filter." />
      )}

      {!error && searches.length === 0 && (
        <EmptyState title="No detections configured" description="The detection catalog could not be loaded from the platform." />
      )}
    </PageLoadGate>
  );
}