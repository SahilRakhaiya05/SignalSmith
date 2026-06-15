import { useSession } from "../context/SessionContext";
import { PIPELINE_STEPS, canRunStep, isStepComplete } from "../lib/workflow";

export function WorkflowStepper() {
  const { loading, runWorkflowStep, workflowSnapshot } = useSession();

  return (
    <nav className="pipeline-stepper" aria-label="Optimization pipeline">
      {PIPELINE_STEPS.map((step, i) => {
        const done = isStepComplete(step.id, workflowSnapshot);
        const enabled = canRunStep(step.id, workflowSnapshot);
        return (
          <div key={step.id} className={`pipeline-step ${done ? "done" : ""} ${enabled ? "enabled" : "locked"}`}>
            <button
              type="button"
              className="pipeline-step__btn"
              disabled={loading || !enabled}
              onClick={() => runWorkflowStep(step.id)}
              title={step.short}
              aria-label={`Step ${i + 1}: ${step.label}`}
            >
              <span className="pipeline-step__num">{done ? "✓" : i + 1}</span>
              <span className="pipeline-step__label">{step.label}</span>
            </button>
          </div>
        );
      })}
    </nav>
  );
}