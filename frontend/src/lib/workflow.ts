export const PIPELINE_STEPS = [
  { id: "bootstrap", label: "Bootstrap", short: "Load Splunk data" },
  { id: "analyze", label: "Analyze", short: "Run agents" },
  { id: "apply", label: "Apply", short: "Build candidate" },
  { id: "validate", label: "Validate", short: "Shadow replay" },
  { id: "revise", label: "Revise", short: "Fix regressions" },
  { id: "approve", label: "Approve", short: "Export policy" },
] as const;

export type PipelineStepId = (typeof PIPELINE_STEPS)[number]["id"];

export interface WorkflowSnapshot {
  hasBootstrap: boolean;
  hasAnalysis: boolean;
  hasProposal: boolean;
  proposalApplied: boolean;
  hasValidation: boolean;
  validationFailed: boolean;
  validationPassed: boolean;
  proposalApproved: boolean;
}

export function getWorkflowSnapshot(input: {
  analysis: { status: string } | null;
  proposal: { status: string } | null;
  validations: Array<{ status: string; tests_passed: number; tests_total: number }>;
}): WorkflowSnapshot {
  const latest = input.validations[input.validations.length - 1];
  return {
    hasBootstrap: Boolean(input.analysis),
    hasAnalysis: input.analysis?.status === "completed",
    hasProposal: Boolean(input.proposal),
    proposalApplied: input.proposal?.status === "applied" || input.proposal?.status === "approved",
    hasValidation: input.validations.length > 0,
    validationFailed: latest?.status === "failed",
    validationPassed: latest?.status === "passed" || (latest != null && latest.tests_passed === latest.tests_total),
    proposalApproved: input.proposal?.status === "approved",
  };
}

export function isStepComplete(step: PipelineStepId, s: WorkflowSnapshot): boolean {
  switch (step) {
    case "bootstrap":
      return s.hasBootstrap;
    case "analyze":
      return s.hasAnalysis;
    case "apply":
      return s.proposalApplied;
    case "validate":
      return s.hasValidation;
    case "revise":
      return s.validationPassed;
    case "approve":
      return s.proposalApproved;
    default:
      return false;
  }
}

export function canRunStep(step: PipelineStepId, s: WorkflowSnapshot): boolean {
  switch (step) {
    case "bootstrap":
      return true;
    case "analyze":
      return true;
    case "apply":
      return s.hasAnalysis && s.hasProposal;
    case "validate":
      return s.proposalApplied;
    case "revise":
      return s.hasValidation && s.validationFailed;
    case "approve":
      return s.validationPassed;
    default:
      return false;
  }
}