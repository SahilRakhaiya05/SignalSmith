import type { ComparisonSummary } from "../types";

export interface ServiceCompareRow {
  service: string;
  baseline: number;
  candidate: number;
}

export function buildServiceComparison(
  comparison: ComparisonSummary | null,
  serviceData: Array<{ service: string; count: number }>
): { rows: ServiceCompareRow[]; candidateIsModeled: boolean } {
  if (comparison?.by_service && Object.keys(comparison.by_service).length > 0) {
    const hasCandidate = comparison.candidate.events > 0 && comparison.baseline.events > 0;
    const ratio = hasCandidate ? comparison.candidate.events / comparison.baseline.events : 0;
    const rows = Object.entries(comparison.by_service).map(([service, baseline]) => ({
      service: service.replace("-service", ""),
      baseline,
      candidate: hasCandidate ? Math.round(baseline * ratio) : 0,
    }));
    return { rows, candidateIsModeled: hasCandidate };
  }

  const rows = serviceData.map((s) => ({
    service: s.service.replace("-service", ""),
    baseline: s.count,
    candidate: 0,
  }));
  return { rows, candidateIsModeled: false };
}