import type { NavIconName } from "../components/nav/NavIcon";

export type NavItem = {
  to: string;
  label: string;
  section: string;
  icon: NavIconName;
  highlight?: boolean;
  keywords?: string[];
};

export const NAV_SECTIONS = [
  { id: "start", label: "Start" },
  { id: "optimize", label: "Optimize" },
  { id: "intel", label: "Intel" },
  { id: "govern", label: "Govern" },
  { id: "platform", label: "Platform" },
] as const;

export const APP_NAV: NavItem[] = [
  { to: "/", label: "Command Center", section: "start", icon: "dashboard", keywords: ["home", "overview", "metrics", "charts"] },
  { to: "/data-flow", label: "Data Flow", section: "start", icon: "dataFlow", keywords: ["pipeline", "ingest", "telemetry", "path"] },
  { to: "/assistant", label: "Mentor", section: "start", icon: "assistant", highlight: true, keywords: ["mentor", "chat", "spl", "guide", "pipeline", "query"] },
  { to: "/workflow", label: "Pipeline", section: "optimize", icon: "pipeline", keywords: ["bootstrap", "analyze", "run", "steps"] },
  { to: "/analytics", label: "Analytics", section: "optimize", icon: "analytics", keywords: ["charts", "index", "volume"] },
  { to: "/recommendations", label: "Policies", section: "optimize", icon: "policies", keywords: ["recommendations", "rules", "reduction"] },
  { to: "/validation", label: "Validation", section: "optimize", icon: "validation", keywords: ["shadow", "coverage", "detections"] },
  { to: "/results", label: "Outcomes", section: "optimize", icon: "outcomes", keywords: ["results", "reduction", "evidence"] },
  { to: "/analysis", label: "Agent Activity", section: "intel", icon: "agents", keywords: ["agents", "timeline", "profiler"] },
  { to: "/protection", label: "Protection Map", section: "intel", icon: "protection", keywords: ["protected", "rules", "safety"] },
  { to: "/searches", label: "Detections", section: "intel", icon: "detections", keywords: ["saved searches", "spl", "catalog"] },
  { to: "/approval", label: "Approval", section: "govern", icon: "approval", keywords: ["approve", "otel", "export", "yaml"] },
  { to: "/history", label: "Run History", section: "govern", icon: "history", keywords: ["sessions", "past", "runs"] },
  { to: "/splunk-dashboard", label: "Dashboard", section: "platform", icon: "splunkDash", keywords: ["splunk", "deploy", "panels"] },
  { to: "/settings", label: "Settings", section: "platform", icon: "settings", keywords: ["integrations", "connection", "api", "login"] },
];

export function searchAppNav(query: string): NavItem[] {
  const q = query.trim().toLowerCase();
  if (!q) return APP_NAV;
  return APP_NAV.filter((item) => {
    const haystack = [item.label, item.to, item.section, ...(item.keywords || [])].join(" ").toLowerCase();
    return haystack.includes(q);
  });
}

export const PAGE_TITLES: Record<string, string> = Object.fromEntries(
  APP_NAV.map((item) => [item.to, item.label])
);