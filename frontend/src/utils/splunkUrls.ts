import type { IntegrationStatus } from "../types";

export function splunkWebBase(integrations?: IntegrationStatus | null): string {
  const splunk = integrations?.splunk;
  if (splunk?.web_url) return splunk.web_url;
  if (!splunk?.host || !splunk?.web_port) return "";
  const scheme = splunk.web_scheme || "http";
  return `${scheme}://${splunk.host}:${splunk.web_port}`;
}

export function splunkDashboardsUrl(integrations?: IntegrationStatus | null): string {
  const base = integrations?.splunk_dashboard?.browse_url || integrations?.splunk_dashboard?.splunk_web;
  if (base?.includes("/dashboards")) return base;
  const web = splunkWebBase(integrations);
  return web ? `${web}/en-US/app/search/dashboards` : "";
}

export function splunkDashboardUrl(integrations?: IntegrationStatus | null): string {
  return integrations?.splunk_dashboard?.url || "";
}