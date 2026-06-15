import { useCallback, useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, downloadText } from "../api";
import { useSession } from "../context/SessionContext";
import { PageHeader } from "../components/ui/PageHeader";
import { PageLoadGate } from "../components/ui/PageLoadGate";
import { DashboardPageSkeleton } from "../components/ui/Skeleton";
import { ChartShell } from "../components/ui/ChartShell";
import { CHART, tooltipStyle } from "../utils/chartTheme";
import {
  AxisBottomTick,
  CHART_MARGIN,
  pieLegendProps,
} from "../utils/chartHelpers";
import { SplCodeBlock } from "../components/SplCodeBlock";
import { splunkDashboardsUrl, splunkDashboardUrl, splunkWebBase } from "../utils/splunkUrls";

const PANEL_META: Record<string, { title: string; splunkView: string }> = {
  index_comparison: { title: "Index volume", splunkView: "Pie chart in Splunk dashboard" },
  events_by_service: { title: "Top services by volume", splunkView: "Bar chart — matches AI SPL stats by service" },
  events_by_scenario: { title: "Security scenarios", splunkView: "Scenario breakdown panel" },
  events_by_level: { title: "Log levels", splunkView: "Severity distribution panel" },
  health_check_noise: { title: "Health-check noise", splunkView: "Noise reduction target panel" },
  service_comparison: { title: "Baseline vs candidate", splunkView: "Side-by-side service comparison" },
};

export function SplunkDashboardView() {
  const { integrations, splunkConnected, sessionLoading, runStep, refreshSession } = useSession();
  const [live, setLive] = useState<Awaited<ReturnType<typeof api.getSplunkLiveAnalytics>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [deploying, setDeploying] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const dashboard = integrations?.splunk_dashboard;

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getSplunkLiveAnalytics();
      setLive(data);
    } catch {
      setLive(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const deployDashboard = () =>
    runStep(async () => {
      setDeploying(true);
      setMessage(null);
      try {
        const r = await api.deploySplunkDashboard();
        setMessage(r.message);
        await refreshSession();
        await refresh();
      } finally {
        setDeploying(false);
      }
    }, "Deploy dashboard");

  const indexChart = live?.charts?.index_comparison || [];
  const serviceChart = live?.charts?.events_by_service || [];
  const scenarioChart = live?.charts?.events_by_scenario || [];
  const levelChart = live?.charts?.events_by_level || [];

  const dashUrl = splunkDashboardUrl(integrations) || dashboard?.url;
  const browseUrl = splunkDashboardsUrl(integrations) || dashboard?.browse_url || "";

  const pageLoading = sessionLoading || loading;

  return (
    <PageLoadGate loading={pageLoading} skeleton={<DashboardPageSkeleton />}>
      <PageHeader
        title="Dashboard"
        description="Live Splunk dashboard panels — same SPL queries used in Command Center, deployable to Splunk Web."
        actions={
          <div className="btn-row">
            <button
              type="button"
              className="btn btn-primary btn-sm"
              disabled={deploying || !splunkConnected}
              onClick={deployDashboard}
            >
              {dashboard?.deployed ? "Update in Splunk" : "Deploy to Splunk"}
            </button>
            {dashboard?.deployed && (
              <a href={browseUrl} target="_blank" rel="noreferrer" className="btn btn-secondary btn-sm">
                Open in Splunk
              </a>
            )}
          </div>
        }
      />

      {message && <div className="alert-banner alert-banner--info">{message}</div>}

      {!dashboard?.deployed && (
        <div className="alert-banner alert-banner--info">
          Deploy to Splunk or download XML.
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            style={{ marginLeft: "0.5rem" }}
            onClick={() =>
              runStep(async () => {
                const xml = await api.getSplunkDashboardXml();
                downloadText("signalsmith_operations.xml", xml);
              }, "Download")
            }
          >
            Download XML
          </button>
        </div>
      )}

      {dashboard?.deployed && (
        <div className="splunk-preview-banner">
          <div>
            <strong>{dashboard.label}</strong>
            <p>
              Search → Dashboards → <code>{dashboard.label}</code>
            </p>
          </div>
          <div className="btn-row">
            <a href={browseUrl} target="_blank" rel="noreferrer" className="btn btn-primary btn-sm">
              Open dashboards
            </a>
            {dashUrl && (
              <a href={dashUrl} target="_blank" rel="noreferrer" className="btn btn-ghost btn-sm">
                Direct link
              </a>
            )}
          </div>
        </div>
      )}

      {live && (
        <>
          <div className="charts-row">
            {indexChart.length > 0 && (
              <div className="chart-card">
                <h3>Index volume</h3>
                <ChartShell height={260}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart margin={CHART_MARGIN.pie}>
                      <Pie data={indexChart} dataKey="value" nameKey="name" cx="50%" cy="46%" innerRadius={48} outerRadius={76} paddingAngle={3}>
                        {indexChart.map((_, i) => (
                          <Cell key={i} fill={i === 0 ? CHART.blue : CHART.cyan} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(v: number) => v.toLocaleString()} contentStyle={tooltipStyle} />
                      <Legend {...pieLegendProps} />
                    </PieChart>
                  </ResponsiveContainer>
                </ChartShell>
              </div>
            )}

            {serviceChart.length > 0 && (
              <div className="chart-card">
                <h3>Events by service</h3>
                <ChartShell height={260}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={serviceChart} margin={CHART_MARGIN.bar}>
                      <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} />
                      <XAxis dataKey="service" tick={AxisBottomTick} interval={0} height={52} />
                      <YAxis tick={{ fill: CHART.tick, fontSize: 10 }} width={40} />
                      <Tooltip contentStyle={tooltipStyle} />
                      <Bar dataKey="count" fill={CHART.blue} radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </ChartShell>
              </div>
            )}
          </div>

          <div className="charts-row">
            {scenarioChart.length > 0 && (
              <div className="chart-card">
                <h3>Scenarios</h3>
                <ChartShell height={260}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={scenarioChart} margin={CHART_MARGIN.bar}>
                      <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} />
                      <XAxis dataKey="scenario" tick={AxisBottomTick} interval={0} height={52} />
                      <YAxis tick={{ fill: CHART.tick, fontSize: 10 }} width={40} />
                      <Tooltip contentStyle={tooltipStyle} />
                      <Bar dataKey="count" fill={CHART.purple} radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </ChartShell>
              </div>
            )}

            {levelChart.length > 0 && (
              <div className="chart-card">
                <h3>Log levels</h3>
                <ChartShell height={260}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart margin={CHART_MARGIN.pie}>
                      <Pie data={levelChart} dataKey="count" nameKey="level" cx="50%" cy="46%" outerRadius={76}>
                        {levelChart.map((_, i) => (
                          <Cell key={i} fill={[CHART.blue, CHART.green, CHART.orange, CHART.red][i % 4]} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={tooltipStyle} />
                      <Legend {...pieLegendProps} />
                    </PieChart>
                  </ResponsiveContainer>
                </ChartShell>
              </div>
            )}
          </div>

          <div className="panel-pro">
            <h3>Panel queries</h3>
            <div className="dashboard-panel-grid">
              {Object.entries(live.panels || {}).map(([key, panel]) => {
                const meta = PANEL_META[key] || { title: key.replace(/_/g, " "), splunkView: "Dashboard panel" };
                return (
                  <article key={key} className="dashboard-panel-card">
                    <h4>{meta.title}</h4>
                    <p>{meta.splunkView}</p>
                    <SplCodeBlock code={panel.spl} integrations={integrations} />
                    <span className="muted">
                      {panel.rows?.length ?? 0} rows · {panel.source || live.source}
                      {panel.error ? ` · ${panel.error}` : ""}
                    </span>
                  </article>
                );
              })}
            </div>
          </div>
        </>
      )}

      {!live && (
        <p className="muted">
          Analytics unavailable. Check connection in{" "}
          <a href={splunkWebBase(integrations) || "#"} target="_blank" rel="noreferrer">
            Splunk Web
          </a>
          .
        </p>
      )}
    </PageLoadGate>
  );
}