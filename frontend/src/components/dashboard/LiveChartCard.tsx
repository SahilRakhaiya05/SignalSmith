import type { ReactNode } from "react";

interface LiveChartCardProps {
  title: string;
  source: string;
  description?: string;
  children: ReactNode;
  empty?: boolean;
  emptyLabel?: string;
}

export function LiveChartCard({
  title,
  source,
  description,
  children,
  empty,
  emptyLabel = "No data from Splunk",
}: LiveChartCardProps) {
  return (
    <article className="live-chart-card">
      <header className="live-chart-card__head">
        <div className="live-chart-card__title-wrap">
          <h3 title={title}>{title}</h3>
          {description && <p className="live-chart-card__desc">{description}</p>}
        </div>
        <span className="live-chart-card__source">{source}</span>
      </header>
      {empty ? <p className="live-chart-card__empty">{emptyLabel}</p> : children}
    </article>
  );
}