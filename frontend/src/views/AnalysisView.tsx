import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useSession } from "../context/SessionContext";
import { PageHeader } from "../components/ui/PageHeader";
import { EmptyState } from "../components/ui/EmptyState";
import { PageLoadGate } from "../components/ui/PageLoadGate";
import { AnalysisPageSkeleton } from "../components/ui/Skeleton";

interface AgentInfo {
  id: string;
  name: string;
  phase: string;
  track: string;
  description: string;
  capabilities: string[];
  human_in_loop: boolean;
  ran_in_session?: boolean;
  action_count?: number;
}

const TRACK_LABELS: Record<string, string> = {
  observability: "Observability",
  security: "Security",
  platform: "Platform",
};

export function AnalysisView() {
  const { analysis, sessionLoading } = useSession();
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [meta, setMeta] = useState<{ timeline_actions?: number; active_agents?: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [agentFilter, setAgentFilter] = useState("all");
  const [search, setSearch] = useState("");

  useEffect(() => {
    api
      .getAgents()
      .then((r) => {
        setAgents(r.agents);
        setMeta(r);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [analysis?.id]);

  const filteredTimeline = useMemo(() => {
    const items = analysis?.agent_timeline || [];
    const q = search.trim().toLowerCase();
    return items.filter((item) => {
      const agentMatch = agentFilter === "all" || item.agent.toLowerCase().includes(agentFilter.toLowerCase());
      const searchMatch =
        !q ||
        item.agent.toLowerCase().includes(q) ||
        item.action.toLowerCase().includes(q) ||
        item.detail.toLowerCase().includes(q);
      return agentMatch && searchMatch;
    });
  }, [analysis?.agent_timeline, agentFilter, search]);

  const pageLoading = sessionLoading || loading;

  return (
    <PageLoadGate loading={pageLoading} skeleton={<AnalysisPageSkeleton />}>
      <PageHeader
        title="Agent activity"
        description="Coordinated agents for discovery, profiling, protection mapping, policy generation, validation, and revision."
        actions={<Link to="/workflow" className="btn btn-secondary btn-sm">Open pipeline</Link>}
      />

      {meta && meta.timeline_actions != null && (
        <div className="session-banner">
          <span className="session-banner__label">Current session</span>
          <p>
            {meta.active_agents ?? 0} agents engaged · {meta.timeline_actions} actions logged
          </p>
        </div>
      )}



      {agents.length > 0 && (
        <section className="panel-pro">
          <h3>Agent roster</h3>
          <p className="panel-pro__desc">Eight coordinated agents aligned with Splunk MCP, SignalSmith Mentor, and human-in-the-loop governance.</p>
          <div className="agent-grid">
            {agents.map((agent) => (
              <article key={agent.id} className={`agent-card ${agent.ran_in_session ? "agent-card--active" : ""}`}>
                <div className="agent-card__head">
                  <h4>{agent.name}</h4>
                  <span className={`agent-card__track agent-card__track--${agent.track}`}>{TRACK_LABELS[agent.track]}</span>
                </div>
                <p>{agent.description}</p>
                <div className="agent-card__tags">
                  <span className="agent-card__phase">{agent.phase}</span>
                  {agent.human_in_loop && <span className="agent-card__human">Human review</span>}
                  {agent.ran_in_session && <span className="agent-card__ran">Ran ({agent.action_count || 0})</span>}
                </div>
                <ul className="agent-card__caps">
                  {agent.capabilities.slice(0, 3).map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </section>
      )}

      <section className="panel-pro">
        <div className="panel-pro__toolbar">
          <h3>Activity timeline</h3>
          <div className="panel-pro__filters">
            <input
              type="search"
              className="search-input"
              placeholder="Search actions…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              aria-label="Search agent timeline"
            />
            <select className="select-input" value={agentFilter} onChange={(e) => setAgentFilter(e.target.value)} aria-label="Filter by agent">
              <option value="all">All agents</option>
              {agents.map((a) => (
                <option key={a.id} value={a.name.split(" ")[0]}>{a.name}</option>
              ))}
            </select>
          </div>
        </div>

        {filteredTimeline.length > 0 ? (
          <div className="timeline">
            {filteredTimeline.map((item, i) => (
              <div className="timeline-item" key={i}>
                <div className="timeline-time">{new Date(item.timestamp).toLocaleTimeString()}</div>
                <div>
                  <div className="timeline-agent">{item.agent} — {item.action}</div>
                  <div className="timeline-detail">{item.detail}</div>
                </div>
                <span className="source-tag">{item.source}</span>
              </div>
            ))}
          </div>
        ) : analysis?.agent_timeline?.length ? (
          <p className="muted">No timeline entries match your search.</p>
        ) : (
          <EmptyState
            title="No agent activity yet"
            description="Run the pipeline to activate discovery, profiling, protection mapping, and policy agents against live Splunk data."
            action={<Link to="/workflow" className="btn btn-primary">Start pipeline</Link>}
          />
        )}
      </section>
    </PageLoadGate>
  );
}