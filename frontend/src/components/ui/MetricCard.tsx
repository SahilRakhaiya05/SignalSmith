import type { ReactNode } from "react";
import type { NavIconName } from "../nav/NavIcon";
import { NavIcon } from "../nav/NavIcon";

interface MetricCardProps {
  label: string;
  value: ReactNode;
  sub?: string;
  highlight?: boolean;
  trend?: "up" | "down" | "neutral";
  icon?: NavIconName;
}

export function MetricCard({ label, value, sub, highlight, trend, icon }: MetricCardProps) {
  return (
    <article className={`metric-ui ${highlight ? "metric-ui--highlight" : ""}`}>
      <div className="metric-ui__head">
        {icon && (
          <span className="metric-ui__icon" aria-hidden>
            <NavIcon name={icon} size={14} />
          </span>
        )}
        <span className="metric-ui__label" title={label}>{label}</span>
      </div>
      <div className={`metric-ui__value ${trend ? `metric-ui__value--${trend}` : ""}`}>{value}</div>
      {sub && <span className="metric-ui__sub" title={sub}>{sub}</span>}
    </article>
  );
}