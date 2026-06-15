import type { LucideIcon } from "lucide-react";
import {
  BarChart3,
  Bot,
  CheckCircle2,
  Database,
  GitBranch,
  History,
  LayoutDashboard,
  LayoutGrid,
  Play,
  Search,
  Settings2,
  Shield,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Terminal,
  TrendingDown,
} from "lucide-react";

const ICONS: Record<string, LucideIcon> = {
  dashboard: LayoutDashboard,
  assistant: Sparkles,
  pipeline: Play,
  analytics: BarChart3,
  policies: Settings2,
  validation: ShieldCheck,
  outcomes: TrendingDown,
  agents: Bot,
  protection: Shield,
  detections: Search,
  approval: CheckCircle2,
  history: History,
  query: Terminal,
  splunkDash: LayoutGrid,
  settings: SlidersHorizontal,
  dataFlow: GitBranch,
  database: Database,
};

export type NavIconName = keyof typeof ICONS;

export function NavIcon({ name, size = 17 }: { name: NavIconName; size?: number }) {
  const Icon = ICONS[name] ?? LayoutDashboard;
  return <Icon size={size} strokeWidth={2} aria-hidden className="nav-icon-svg" />;
}