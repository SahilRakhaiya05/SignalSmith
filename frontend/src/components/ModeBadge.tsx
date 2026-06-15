import { connectionClass, connectionLabel } from "../utils/connectionDisplay";

export function ModeBadge({ mode }: { mode: string }) {
  const cls = connectionClass(mode);
  const label = connectionLabel(mode);
  return <span className={`mode-badge ${cls}`}>{label}</span>;
}