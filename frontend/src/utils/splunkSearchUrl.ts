import type { IntegrationStatus } from "../types";
import { splunkWebBase } from "./splunkUrls";

export function splunkSearchUrl(spl: string, integrations?: IntegrationStatus | null): string {
  const base = splunkWebBase(integrations);
  if (!base) return "";
  const q = spl.trim().startsWith("search") ? spl.trim() : `search ${spl.trim()}`;
  return `${base}/en-US/app/search/search?q=${encodeURIComponent(q)}`;
}