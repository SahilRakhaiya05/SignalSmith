import { Link } from "react-router-dom";
import { useSession } from "../context/SessionContext";
import { PageHeader } from "../components/ui/PageHeader";
import { PageLoadGate } from "../components/ui/PageLoadGate";
import { GenericPageSkeleton } from "../components/ui/Skeleton";
import { PIPELINE_STEPS, canRunStep, isStepComplete } from "../lib/workflow";

const STEP_DETAILS: Record<string, { desc: string }> = {
  bootstrap: { desc: "Export events from the Splunk baseline index." },
  analyze: { desc: "Discovery, profiling, protection mapping, and policy generation agents." },
  apply: { desc: "Apply filtering policies and ingest the optimized candidate dataset to Splunk." },
  validate: { desc: "Replay saved searches with real SPL against baseline and candidate indexes." },
  revise: { desc: "Automatically adjust policies when validation detects coverage regressions." },
  approve: { desc: "Human approval gate with OpenTelemetry collector YAML export." },
};

export function WorkflowView() {
  const { loading, runWorkflowStep, workflowSnapshot, sessionLoading } = useSession();

  return (
    <PageLoadGate loading={sessionLoading} skeleton={<GenericPageSkeleton />}>
      <PageHeader
        title="Optimization pipeline"
        description="Run each step in order. Progress appears once at the top of the page."
        actions={<Link to="/" className="btn btn-ghost btn-sm">← Home</Link>}
      />

      <div className="pipeline-grid">
        {PIPELINE_STEPS.map((step, i) => {
          const done = isStepComplete(step.id, workflowSnapshot);
          const enabled = canRunStep(step.id, workflowSnapshot);
          const detail = STEP_DETAILS[step.id];
          return (
            <article key={step.id} className={`pipeline-card ${done ? "done" : ""} ${!enabled && !done ? "locked" : ""}`}>
              <div className="pipeline-card__head">
                <span className="pipeline-card__step">Step {i + 1}</span>
                <h3>{step.label}</h3>
                {done && <span className="pipeline-card__badge pipeline-card__badge--done">Complete</span>}
                {!done && !enabled && <span className="pipeline-card__badge pipeline-card__badge--locked">Locked</span>}
              </div>
              <p>{detail.desc}</p>
              <button
                type="button"
                className={`btn ${done ? "btn-secondary" : "btn-primary"}`}
                disabled={loading || !enabled}
                onClick={() => runWorkflowStep(step.id)}
              >
                {done ? "Re-run" : "Run step"}
              </button>
            </article>
          );
        })}
      </div>
    </PageLoadGate>
  );
}