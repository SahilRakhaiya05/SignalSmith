import type { ReactNode } from "react";

export function Skeleton({ className = "", style }: { className?: string; style?: React.CSSProperties }) {
  return <div className={`skeleton ${className}`.trim()} style={style} aria-hidden="true" />;
}

export function SkeletonText({ width = "100%", height = "0.85rem" }: { width?: string | number; height?: string | number }) {
  return <Skeleton className="skeleton--text" style={{ width, height }} />;
}

export function PageHeaderSkeleton({ description = true, actions = false }: { description?: boolean; actions?: boolean }) {
  return (
    <header className="page-header-ui skeleton-header">
      <div className="page-header-ui__text">
        <SkeletonText width="12rem" height="1.35rem" />
        {description && <SkeletonText width="22rem" height="0.8rem" />}
      </div>
      {actions && <Skeleton style={{ width: "7rem", height: "2rem", borderRadius: "8px" }} />}
    </header>
  );
}

export function MetricsGridSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="metrics-grid-pro">
      {Array.from({ length: count }).map((_, i) => (
        <article key={i} className="skeleton-metric">
          <SkeletonText width="5rem" height="0.7rem" />
          <SkeletonText width="4.5rem" height="1.4rem" />
          <SkeletonText width="3.5rem" height="0.65rem" />
        </article>
      ))}
    </div>
  );
}

export function ChartGridSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="command-center__viz-grid skeleton-chart-grid">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="skeleton-chart-card">
          <SkeletonText width="6rem" height="0.8rem" />
          <Skeleton className="skeleton-chart-card__body" />
        </div>
      ))}
    </div>
  );
}

export function TableSkeleton({ rows = 6, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <div className="skeleton-table-wrap">
      <div className="skeleton-table">
        <div className="skeleton-table__head">
          {Array.from({ length: cols }).map((_, i) => (
            <Skeleton key={i} style={{ height: "0.75rem", flex: 1 }} />
          ))}
        </div>
        {Array.from({ length: rows }).map((_, r) => (
          <div key={r} className="skeleton-table__row">
            {Array.from({ length: cols }).map((_, c) => (
              <Skeleton key={c} style={{ height: "0.7rem", flex: c === 0 ? 1.4 : 1 }} />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

export function CardGridSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="card-grid">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="skeleton-card">
          <SkeletonText width="70%" height="0.9rem" />
          <SkeletonText width="100%" height="0.7rem" />
          <SkeletonText width="90%" height="0.7rem" />
          <Skeleton style={{ height: "4rem", marginTop: "0.5rem" }} />
        </div>
      ))}
    </div>
  );
}

export function PanelSkeleton({ title = true, lines = 4 }: { title?: boolean; lines?: number }) {
  return (
    <div className="panel-pro skeleton-panel">
      {title && <SkeletonText width="8rem" height="0.95rem" />}
      {Array.from({ length: lines }).map((_, i) => (
        <SkeletonText key={i} width={i === lines - 1 ? "60%" : "100%"} height="0.75rem" />
      ))}
    </div>
  );
}

export function CommandCenterSkeleton() {
  return (
    <div className="command-center page-skeleton">
      <header className="command-center__header">
        <div>
          <SkeletonText width="10rem" height="1.4rem" />
          <SkeletonText width="14rem" height="0.8rem" />
        </div>
        <div className="command-center__actions">
          <Skeleton style={{ width: "5.5rem", height: "2rem", borderRadius: "8px" }} />
          <Skeleton style={{ width: "5.5rem", height: "2rem", borderRadius: "8px" }} />
          <Skeleton style={{ width: "6.5rem", height: "2rem", borderRadius: "8px" }} />
        </div>
      </header>
      <MetricsGridSkeleton count={6} />
      <ChartGridSkeleton count={4} />
      <PanelSkeleton lines={3} />
    </div>
  );
}

export function DataFlowSkeleton() {
  return (
    <div className="page-skeleton">
      <PageHeaderSkeleton description actions />
      <PanelSkeleton lines={2} />
      <div className="skeleton-data-flow-path">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="skeleton-data-flow-node" />
        ))}
      </div>
      <div className="data-flow-grid">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="skeleton-data-flow-card" />
        ))}
      </div>
      <PanelSkeleton lines={5} />
    </div>
  );
}

export function AnalyticsPageSkeleton() {
  return (
    <div className="page-skeleton">
      <PageHeaderSkeleton description={false} />
      <ChartGridSkeleton count={2} />
      <ChartGridSkeleton count={2} />
    </div>
  );
}

export function DashboardPageSkeleton() {
  return (
    <div className="page-skeleton">
      <PageHeaderSkeleton description={false} actions />
      <ChartGridSkeleton count={2} />
      <ChartGridSkeleton count={2} />
      <CardGridSkeleton count={4} />
    </div>
  );
}

export function AnalysisPageSkeleton() {
  return (
    <div className="page-skeleton">
      <PageHeaderSkeleton description actions />
      <Skeleton className="skeleton-banner" />
      <CardGridSkeleton count={8} />
      <PanelSkeleton lines={6} />
    </div>
  );
}

export function GenericPageSkeleton() {
  return (
    <div className="page-skeleton">
      <PageHeaderSkeleton />
      <MetricsGridSkeleton count={4} />
      <PanelSkeleton lines={5} />
    </div>
  );
}

export function AssistantPageSkeleton() {
  return (
    <div className="assistant-page page-skeleton">
      <div className="assistant-layout skeleton-assistant-layout">
        <aside className="assistant-sidebar skeleton-assistant-sidebar">
          <SkeletonText width="5rem" height="0.9rem" />
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} style={{ height: "2rem", borderRadius: "999px" }} />
          ))}
          <Skeleton style={{ height: "5rem", marginTop: "1rem" }} />
        </aside>
        <section className="assistant-chat skeleton-assistant-chat">
          <Skeleton style={{ height: "4rem", width: "40%" }} />
          <Skeleton style={{ flex: 1, minHeight: "12rem" }} />
          <Skeleton style={{ height: "3.5rem" }} />
        </section>
      </div>
    </div>
  );
}

const ROUTE_SKELETONS: Record<string, () => ReactNode> = {
  "/": () => <CommandCenterSkeleton />,
  "/data-flow": () => <DataFlowSkeleton />,
  "/assistant": () => <AssistantPageSkeleton />,
  "/analytics": () => <AnalyticsPageSkeleton />,
  "/splunk-dashboard": () => <DashboardPageSkeleton />,
  "/analysis": () => <AnalysisPageSkeleton />,
  "/searches": () => (
    <div className="page-skeleton">
      <PageHeaderSkeleton />
      <Skeleton style={{ height: "2.5rem", marginBottom: "1rem" }} />
      <CardGridSkeleton count={6} />
    </div>
  ),
  "/history": () => (
    <div className="page-skeleton">
      <PageHeaderSkeleton />
      <TableSkeleton rows={8} cols={6} />
    </div>
  ),
};

export function RouteSkeleton({ pathname }: { pathname: string }) {
  const render = ROUTE_SKELETONS[pathname] || (() => <GenericPageSkeleton />);
  return <>{render()}</>;
}