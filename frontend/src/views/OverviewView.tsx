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
import { Link } from "react-router-dom";
import { useSession } from "../context/SessionContext";
import { MetricCard } from "../components/ui/MetricCard";
import { PageLoadGate } from "../components/ui/PageLoadGate";
import { CommandCenterSkeleton } from "../components/ui/Skeleton";
import { ChartShell } from "../components/ui/ChartShell";

import { LiveChartCard } from "../components/dashboard/LiveChartCard";
import { formatBytes } from "../utils";
import { CHART, tooltipStyle } from "../utils/chartTheme";
import {
  AxisBottomTick,
  AxisCategoryTick,
  CHART_MARGIN,
  axisCategoryWidth,
  legendProps,
  pieLegendProps,
} from "../utils/chartHelpers";

function querySourceLabel(live: { official_mcp?: boolean; query_source?: string; source?: string } | null) {
  if (!live) return "Splunk";
  if (live.official_mcp) return "MCP";
  return live.query_source === "mcp" ? "MCP" : "Splunk API";
}

export function OverviewView() {
  const {
    analysis,
    splunkConnected,
    comparison,
    validations,
    integrations,
    workflowSnapshot,
    liveAnalytics,
    sessionLoading,
    loading,
    runFullPipeline,
  } = useSession();

  const live = liveAnalytics;
  const source = querySourceLabel(live);
  const baseline = live?.baseline_events ?? 0;
  const candidate = live?.candidate_events ?? 0;
  const reduction = live?.reduction_percent ?? comparison?.event_reduction_percent ?? null;
  const latestVal = validations[validations.length - 1];
  const coverage = latestVal?.coverage_percent ?? comparison?.coverage_percent ?? null;
  const indexChart = live?.charts.index_comparison ?? [];
  const serviceChart = live?.charts.events_by_service ?? [];
  const scenarioChart = live?.charts.events_by_scenario ?? [];
  const levelChart = live?.charts.events_by_level ?? [];
  const compareChart = live?.charts.service_comparison ?? [];
  const healthChart = live?.charts.health_check_noise ?? [];
  const serviceLabels = serviceChart.map((r) => r.service);
  const hasCharts = indexChart.length > 0 || serviceChart.length > 0;

  return (
    <PageLoadGate loading={sessionLoading} skeleton={<CommandCenterSkeleton />}>
      <div className="command-center">
        <header className="command-center__header">
          <div>
            <h1>Command Center</h1>
            <p>Index analytics and optimization outcomes</p>
          </div>
          <div className="command-center__actions">
            <Link to="/data-flow" className="btn btn-secondary btn-sm">Data flow</Link>
            <Link to="/assistant" className="btn btn-secondary btn-sm">Mentor</Link>
            <Link to="/workflow" className="btn btn-secondary btn-sm">Pipeline</Link>
            <button type="button" className="btn btn-primary btn-sm" disabled={loading || !splunkConnected} onClick={runFullPipeline}>
              Run pipeline
            </button>
          </div>
        </header>

        <div className="metrics-grid-pro">
          <MetricCard label="Baseline index" value={baseline.toLocaleString()} sub={live?.baseline_index} highlight icon="database" />
          <MetricCard label="Candidate index" value={candidate > 0 ? candidate.toLocaleString() : "—"} sub={live?.candidate_index} icon="analytics" />
          <MetricCard
            label="Reduction"
            value={reduction != null ? `${Number(reduction).toFixed(1)}%` : "—"}
            sub="live SPL"
            trend={reduction != null && reduction > 0 ? "up" : undefined}
            icon="outcomes"
          />
          <MetricCard label="Coverage" value={coverage != null ? `${coverage}%` : "—"} sub="validation" icon="validation" />
          <MetricCard label="Services" value={serviceChart.length || "—"} sub="in baseline" icon="agents" />
          <MetricCard
            label="Detections"
            value={integrations?.saved_searches ?? "—"}
            sub={workflowSnapshot.proposalApproved ? "approved" : workflowSnapshot.hasAnalysis ? "in progress" : "idle"}
          />
        </div>

        {hasCharts && (
          <section className="command-center__viz">
            <div className="command-center__viz-grid">
              <LiveChartCard title="Index volume" source={source} description="Baseline vs candidate event counts" empty={!indexChart.length}>
                <ChartShell height={220}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart margin={CHART_MARGIN.pie}>
                      <Pie data={indexChart} dataKey="value" nameKey="name" cx="50%" cy="46%" innerRadius={42} outerRadius={68} paddingAngle={2}>
                        {indexChart.map((_, i) => (
                          <Cell key={i} fill={i === 0 ? CHART.blue : CHART.cyan} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(v: number) => v.toLocaleString()} contentStyle={tooltipStyle} />
                      <Legend {...pieLegendProps} />
                    </PieChart>
                  </ResponsiveContainer>
                </ChartShell>
              </LiveChartCard>

              <LiveChartCard title="Volume by service" source={source} description="Top services in baseline index" empty={!serviceChart.length}>
                <ChartShell height={220}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={serviceChart} layout="vertical" margin={{ ...CHART_MARGIN.barVertical, left: 4 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} horizontal={false} />
                      <XAxis type="number" tick={{ fill: CHART.tick, fontSize: 10 }} />
                      <YAxis
                        type="category"
                        dataKey="service"
                        width={axisCategoryWidth(serviceLabels)}
                        tick={AxisCategoryTick}
                      />
                      <Tooltip contentStyle={tooltipStyle} />
                      <Bar dataKey="count" fill={CHART.blue} radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </ChartShell>
              </LiveChartCard>

              <LiveChartCard title="Scenario mix" source={source} description="Security scenario breakdown" empty={!scenarioChart.length}>
                <ChartShell height={220}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={scenarioChart} margin={CHART_MARGIN.bar}>
                      <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} />
                      <XAxis dataKey="scenario" tick={AxisBottomTick} interval={0} height={52} />
                      <YAxis tick={{ fill: CHART.tick, fontSize: 10 }} width={36} />
                      <Tooltip contentStyle={tooltipStyle} />
                      <Bar dataKey="count" fill={CHART.cyan} radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </ChartShell>
              </LiveChartCard>

              <LiveChartCard title="Log levels" source={source} description="Severity distribution" empty={!levelChart.length}>
                <ChartShell height={220}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart margin={CHART_MARGIN.pie}>
                      <Pie data={levelChart} dataKey="count" nameKey="level" cx="50%" cy="46%" outerRadius={68}>
                        {levelChart.map((_, i) => (
                          <Cell key={i} fill={CHART.colors[i % CHART.colors.length]} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={tooltipStyle} />
                      <Legend {...pieLegendProps} />
                    </PieChart>
                  </ResponsiveContainer>
                </ChartShell>
              </LiveChartCard>
            </div>

            {compareChart.some((r) => r.candidate > 0) && (
              <LiveChartCard title="Baseline vs candidate by service" source={source} description="Side-by-side volume after policies are applied">
                <ChartShell height={240}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={compareChart} margin={CHART_MARGIN.bar}>
                      <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} />
                      <XAxis dataKey="service" tick={AxisBottomTick} interval={0} height={52} />
                      <YAxis tick={{ fill: CHART.tick, fontSize: 10 }} width={40} />
                      <Tooltip contentStyle={tooltipStyle} />
                      <Legend {...legendProps} />
                      <Bar dataKey="baseline" fill={CHART.blue} name="Baseline" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="candidate" fill={CHART.green} name="Candidate" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </ChartShell>
              </LiveChartCard>
            )}

            {healthChart.length > 0 && (
              <LiveChartCard title="Health check noise" source={source} description="High-volume health-check traffic — common reduction target">
                <ChartShell height={200}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={healthChart} margin={CHART_MARGIN.bar}>
                      <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} />
                      <XAxis dataKey="service" tick={AxisBottomTick} interval={0} height={48} />
                      <YAxis tick={{ fill: CHART.tick, fontSize: 10 }} width={36} />
                      <Tooltip contentStyle={tooltipStyle} />
                      <Bar dataKey="count" fill={CHART.orange} radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </ChartShell>
              </LiveChartCard>
            )}
          </section>
        )}

        {!hasCharts && !splunkConnected && (
          <div className="command-center__empty">
            <p>Splunk is offline. Start Splunk and refresh to load live index analytics.</p>
            <Link to="/settings" className="btn btn-secondary btn-sm">Integrations</Link>
          </div>
        )}

        {analysis && (
          <section className="command-center__session">
            <h2>Optimization session</h2>
            <div className="command-center__session-grid">
              <article>
                <span>Profiled</span>
                <strong>{formatBytes(analysis.baseline_bytes)}</strong>
                <p>{analysis.baseline_event_count.toLocaleString()} events</p>
              </article>
              <article>
                <span>Reducible</span>
                <strong>{analysis.reducible_estimate.toLocaleString()}</strong>
                <p>events identified</p>
              </article>
              <article>
                <span>Protected</span>
                <strong>{analysis.protection_map?.length ?? 0}</strong>
                <p>detection rules</p>
              </article>
              <article>
                <span>Policies</span>
                <strong>{workflowSnapshot.proposalApproved ? "Approved" : "Pending"}</strong>
                <p>
                  <Link to="/recommendations">View policies</Link>
                </p>
              </article>
            </div>
          </section>
        )}
      </div>
    </PageLoadGate>
  );
}