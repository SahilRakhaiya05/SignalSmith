import type { ReactNode } from "react";

interface ChartShellProps {
  children: ReactNode;
  height?: number;
}

export function ChartShell({ children, height = 220 }: ChartShellProps) {
  return (
    <div className="chart-shell" style={{ height }}>
      {children}
    </div>
  );
}