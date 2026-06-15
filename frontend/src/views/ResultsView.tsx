import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Link } from "react-router-dom";
import { useSession } from "../context/SessionContext";
import { PageHeader } from "../components/ui/PageHeader";
import { PageLoadGate } from "../components/ui/PageLoadGate";
import { GenericPageSkeleton } from "../components/ui/Skeleton";
import { MetricCard } from "../components/ui/MetricCard";
import { EmptyState } from "../components/ui/EmptyState";
import { ChartShell } from "../components/ui/ChartShell";
import { CHART, tooltipStyle } from "../utils/chartTheme";
import { buildServiceComparison } from "../utils/comparison";
import {
  AxisBottomTick,
  AxisCategoryTick,
  CHART_MARGIN,
  legendProps,
} from "../utils/chartHelpers";

export function ResultsView() {
  const { validations, comparison, splunkCounts, sessionLoading } = useSession();
  const final = validations.find((v) => v.run_number === 2) ?? validations[validations.length - 1];

  const { rows: serviceCompare, candidateIsModeled } = buildServiceComparison(comparison, []);

  const indexCompare = [
    { label: "Session baseline", value: comparison?.baseline.events || 0, source: "session" },
    { label: "Session candidate", value: comparison?.candidate.events || 0, source: "session" },
    { label: "Splunk baseline", value: splunkCounts["signalsmith_baseline"] || 0, source: "splunk" },
    { label: "Splunk candidate", value: splunkCounts["signalsmith_candidate"] || 0, source: "splunk" },
  ].filter((d) => d.value > 0);

  return (
    <PageLoadGate loading={sessionLoading} skeleton={<GenericPageSkeleton />}>
      <PageHeader
        title="Outcomes"
        description="Evidence-backed optimization results from shadow validation against live Splunk indexes."
      />

      {final ? (
        <>
          {final.status === "passed" && (
            <div className="alert alert-success">
              All {final.tests_total} detections passed. {final.protected_events_lost === 0 ? "Zero protected events lost." : ""}
            </div>
          )}
          {final.status === "failed" && final.failure_reason && (
            <div className="alert alert-warning">{final.failure_reason}</div>
          )}

          <div className="metrics-grid-pro">
            <MetricCard label="Event reduction" value={`${final.event_reduction_percent.toFixed(1)}%`} highlight trend="up" />
            <MetricCard label="Byte reduction" value={`${final.byte_reduction_percent.toFixed(1)}%`} />
            <MetricCard label="Coverage" value={`${final.coverage_percent.toFixed(1)}%`} />
            <MetricCard label="Tests" value={`${final.tests_passed}/${final.tests_total}`} />
            <MetricCard label="Protected lost" value={final.protected_events_lost} trend={final.protected_events_lost === 0 ? "up" : "down"} />
            <MetricCard label="Risk" value={final.final_risk_level} />
          </div>

          <div className="charts-row">
            {serviceCompare.length > 0 && serviceCompare.some((r) => r.candidate > 0) && (
              <div className="chart-card">
                <h3>Service volume comparison</h3>
                <p className="chart-card__subtitle">
                  {candidateIsModeled ? (
                    <>
                      <span className="data-badge data-badge--modeled">Modeled</span> Candidate scaled to session totals
                    </>
                  ) : (
                    <>
                      <span className="data-badge data-badge--live">Live</span> Session data
                    </>
                  )}
                </p>
                <ChartShell height={240}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={serviceCompare} margin={CHART_MARGIN.bar}>
                      <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} />
                      <XAxis dataKey="service" tick={AxisBottomTick} interval={0} height={52} />
                      <YAxis tick={{ fill: CHART.tick, fontSize: 10 }} width={40} />
                      <Tooltip contentStyle={tooltipStyle} />
                      <Legend {...legendProps} />
                      <Bar dataKey="baseline" fill={CHART.blue} name="Baseline" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="candidate" fill={CHART.cyan} name="Candidate" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </ChartShell>
              </div>
            )}
            {indexCompare.length > 0 && (
              <div className="chart-card">
                <h3>Index event counts</h3>
                <p className="chart-card__subtitle">
                  <span className="data-badge data-badge--live">Live</span> Session files + Splunk indexes
                </p>
                <ChartShell height={240}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={indexCompare} layout="vertical" margin={CHART_MARGIN.barVertical}>
                      <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} horizontal={false} />
                      <XAxis type="number" tick={{ fill: CHART.tick, fontSize: 10 }} />
                      <YAxis type="category" dataKey="label" width={108} tick={AxisCategoryTick} />
                      <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => v.toLocaleString()} />
                      <Bar dataKey="value" fill={CHART.purple} radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </ChartShell>
              </div>
            )}
          </div>
        </>
      ) : (
        <EmptyState
          title="No outcomes yet"
          description="Complete the pipeline through validation to see reduction metrics and coverage evidence."
          action={<Link to="/workflow" className="btn btn-primary">Open pipeline</Link>}
        />
      )}
    </PageLoadGate>
  );
}