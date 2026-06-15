import type { ReactElement } from "react";

export const CHART_MARGIN = {
  default: { top: 8, right: 12, left: 4, bottom: 4 },
  bar: { top: 8, right: 12, left: 4, bottom: 28 },
  barVertical: { top: 8, right: 16, left: 4, bottom: 4 },
  pie: { top: 4, right: 8, left: 8, bottom: 4 },
} as const;

export const legendProps = {
  wrapperStyle: {
    fontSize: "10px",
    lineHeight: "1.3",
    paddingTop: "4px",
    maxWidth: "100%",
  },
  iconSize: 8,
};

export const pieLegendProps = {
  layout: "horizontal" as const,
  align: "center" as const,
  verticalAlign: "bottom" as const,
  wrapperStyle: {
    fontSize: "10px",
    lineHeight: "1.35",
    paddingTop: "6px",
    width: "100%",
    maxWidth: "100%",
    overflow: "hidden",
  },
  iconSize: 8,
};

export function truncateLabel(value: string, max = 14): string {
  const text = String(value ?? "");
  if (text.length <= max) return text;
  return `${text.slice(0, max - 1)}…`;
}

export function axisCategoryWidth(labels: string[], min = 56, max = 96): number {
  if (!labels.length) return min;
  const longest = Math.max(...labels.map((l) => String(l).length));
  return Math.min(max, Math.max(min, longest * 6.5));
}

interface AxisTickProps {
  x?: number;
  y?: number;
  payload?: { value: string };
}

export function AxisCategoryTick({ x = 0, y = 0, payload }: AxisTickProps): ReactElement {
  const label = truncateLabel(payload?.value ?? "", 16);
  return (
    <g transform={`translate(${x},${y})`}>
      <text x={0} y={0} dy={4} textAnchor="end" fill="#64748b" fontSize={10}>
        {label}
        <title>{payload?.value}</title>
      </text>
    </g>
  );
}

export function AxisBottomTick({ x = 0, y = 0, payload }: AxisTickProps): ReactElement {
  const label = truncateLabel(payload?.value ?? "", 12);
  return (
    <g transform={`translate(${x},${y})`}>
      <text x={0} y={0} dy={12} textAnchor="end" fill="#64748b" fontSize={9} transform="rotate(-22)">
        {label}
        <title>{payload?.value}</title>
      </text>
    </g>
  );
}