import {
  Area,
  AreaChart,
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
import { PageHeader } from "../components/ui/PageHeader";
import { PageLoadGate } from "../components/ui/PageLoadGate";
import { ChartShell } from "../components/ui/ChartShell";
import { AnalyticsPageSkeleton } from "../components/ui/Skeleton";
import { EmptyState } from "../components/ui/EmptyState";
import { CHART, tooltipStyle } from "../utils/chartTheme";
import { buildServiceComparison } from "../utils/comparison";
import {
  AxisBottomTick,
  CHART_MARGIN,
  legendProps,
  pieLegendProps,
} from "../utils/chartHelpers";

export function AnalyticsView() {
  const { serviceData, categoryData, splunkCounts, comparison, validations, sessionLoading } = useSession();

  const indexData = [
    { name: "Baseline", value: splunkCounts["signalsmith_baseline"] || 0, fill: CHART.blue },
    { name: "Candidate", value: splunkCounts["signalsmith_candidate"] || 0, fill: CHART.cyan },
  ].filter((d) => d.value > 0);

  const { rows: compareData, candidateIsModeled } = buildServiceComparison(comparison, serviceData);

  const finalVal = validations[validations.length - 1];
  const coverageData =
    finalVal?.coverage_results?.map((r) => ({
      name: r.search_name.split(" ")[0],
      baseline: r.baseline_count,
      candidate: r.candidate_count,
      passed: r.passed ? 1 : 0,
    })) || [];

  const hasData = indexData.length > 0 || serviceData.length > 0 || coverageData.length > 0;

  return (
    <PageLoadGate loading={sessionLoading} skeleton={<AnalyticsPageSkeleton />}>
      <PageHeader
        title="Analytics"
        description="Session profiles, Splunk index counts, and validation replay — live data from your pipeline run."
      />

      <div className="charts-row">
        {indexData.length > 0 && (
          <div className="chart-card">
            <h3>Splunk index volume</h3>
            <p className="chart-card__subtitle">
              <span className="data-badge data-badge--live">Live</span> Queried from Splunk REST API
            </p>
            <ChartShell height={260}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart margin={CHART_MARGIN.pie}>
                  <Pie data={indexData} dataKey="value" nameKey="name" cx="50%" cy="46%" innerRadius={48} outerRadius={76} paddingAngle={3}>
                    {indexData.map((entry, i) => (
                      <Cell key={i} fill={entry.fill} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => v.toLocaleString()} contentStyle={tooltipStyle} />
                  <Legend {...pieLegendProps} />
                </PieChart>
              </ResponsiveContainer>
            </ChartShell>
          </div>
        )}

        {compareData.length > 0 && compareData.some((r) => r.candidate > 0) && (
          <div className="chart-card">
            <h3>Baseline vs candidate by service</h3>
            <p className="chart-card__subtitle">
              {candidateIsModeled ? (
                <>
                  <span className="data-badge data-badge--modeled">Modeled</span> Candidate scaled to session totals
                </>
              ) : (
                <>
                  <span className="data-badge data-badge--live">Live</span> From session comparison
                </>
              )}
            </p>
            <ChartShell height={260}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={compareData} margin={CHART_MARGIN.bar}>
                  <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} />
                  <XAxis dataKey="service" tick={AxisBottomTick} interval={0} height={52} />
                  <YAxis tick={{ fill: CHART.tick, fontSize: 10 }} width={40} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend {...legendProps} />
                  <Bar dataKey="baseline" fill={CHART.blue} radius={[4, 4, 0, 0]} name="Baseline" />
                  <Bar dataKey="candidate" fill={CHART.cyan} radius={[4, 4, 0, 0]} name="Candidate" />
                </BarChart>
              </ResponsiveContainer>
            </ChartShell>
          </div>
        )}
      </div>

      <div className="charts-row">
        {categoryData.length > 0 && (
          <div className="chart-card">
            <h3>Scenario distribution</h3>
            <p className="chart-card__subtitle">
              <span className="data-badge data-badge--live">Live</span> Baseline telemetry profile
            </p>
            <ChartShell height={260}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={categoryData} margin={CHART_MARGIN.bar}>
                  <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} />
                  <XAxis dataKey="category" tick={AxisBottomTick} interval={0} height={52} />
                  <YAxis tick={{ fill: CHART.tick, fontSize: 10 }} width={40} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Area type="monotone" dataKey="count" stroke={CHART.purple} fill="#7c3aed22" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </ChartShell>
          </div>
        )}

        {coverageData.length > 0 && (
          <div className="chart-card">
            <h3>Validation coverage</h3>
            <p className="chart-card__subtitle">
              <span className="data-badge data-badge--live">Live</span> Splunk SPL replay results
            </p>
            <ChartShell height={260}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={coverageData} margin={CHART_MARGIN.bar}>
                  <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} />
                  <XAxis dataKey="name" tick={AxisBottomTick} interval={0} height={52} />
                  <YAxis tick={{ fill: CHART.tick, fontSize: 10 }} width={40} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend {...legendProps} />
                  <Bar dataKey="baseline" fill={CHART.blue} name="Baseline hits" />
                  <Bar dataKey="candidate" fill={CHART.green} name="Candidate hits" />
                </BarChart>
              </ResponsiveContainer>
            </ChartShell>
          </div>
        )}
      </div>

      {!hasData && (
        <EmptyState
          title="No analytics data"
          description="Bootstrap from Splunk and run the pipeline to populate index metrics and charts."
          action={<Link to="/workflow" className="btn btn-primary">Open pipeline</Link>}
        />
      )}
    </PageLoadGate>
  );
}