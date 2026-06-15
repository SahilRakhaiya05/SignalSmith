import { Link, useNavigate } from "react-router-dom";
import { useSession } from "../context/SessionContext";
import { ModeBadge } from "../components/ModeBadge";
import { PageHeader } from "../components/ui/PageHeader";
import { PageLoadGate } from "../components/ui/PageLoadGate";
import { GenericPageSkeleton } from "../components/ui/Skeleton";
import { splunkWebBase } from "../utils/splunkUrls";

export function SettingsView() {
  const navigate = useNavigate();
  const { integrations, splunkConnection, splunkUser, sessionLoading, logoutSplunk } = useSession();
  const splunk = integrations?.splunk;
  const dashboard = integrations?.splunk_dashboard;
  const ai = integrations?.ai;
  const engine =
    integrations?.connection_detail?.query_engine === "mcp"
      ? "MCP"
      : integrations?.connection_detail?.query_engine === "splunk_api"
        ? "Splunk API"
        : "Offline";

  return (
    <PageLoadGate loading={sessionLoading} skeleton={<GenericPageSkeleton />}>
      <PageHeader title="Settings" />

      <div className="settings-grid panel-pro">
        <table>
          <tbody>
            <tr>
              <td>Splunk user</td>
              <td><strong>{splunkUser || "—"}</strong></td>
            </tr>
            <tr>
              <td>Connection</td>
              <td>
                <ModeBadge mode={splunkConnection} />
              </td>
            </tr>
            <tr>
              <td>Query engine</td>
              <td>{engine}</td>
            </tr>
            <tr>
              <td>Splunk Web</td>
              <td>
                <a href={splunkWebBase(integrations) || "#"} target="_blank" rel="noreferrer">
                  {splunkWebBase(integrations) || "—"}
                </a>
              </td>
            </tr>
            <tr>
              <td>API</td>
              <td>
                <code>{splunk?.api_url || "—"}</code>
              </td>
            </tr>
            <tr>
              <td>SignalSmith Mentor</td>
              <td>{ai?.available ? "Online" : ai?.configured ? "Offline · SPL mode" : "SPL mode only"}</td>
            </tr>
            <tr>
              <td>Dashboard</td>
              <td>
                {dashboard?.deployed ? (
                  <a href={dashboard.url} target="_blank" rel="noreferrer">
                    {dashboard.label} · open
                  </a>
                ) : (
                  <Link to="/splunk-dashboard">Deploy dashboard</Link>
                )}
              </td>
            </tr>
            <tr>
              <td>Session</td>
              <td>
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={() => {
                    logoutSplunk();
                    navigate("/login");
                  }}
                >
                  Sign out
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {splunk && (
        <div className="panel-pro panel-pro--compact">
          <h3>Indexes</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Index</th>
                  <th>Status</th>
                  <th>Events</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(splunk.indexes || {}).map(([name, info]) => (
                  <tr key={name}>
                    <td>
                      <code>{name}</code>
                    </td>
                    <td>{info.exists ? "Ready" : "Missing"}</td>
                    <td>{info.event_count?.toLocaleString() ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </PageLoadGate>
  );
}