import { Link } from "react-router-dom";

interface DataExplainerProps {
  compact?: boolean;
}

const STEPS = [
  {
    title: "Baseline index",
    body: "Your real Splunk telemetry (e.g. signalsmith_baseline). SignalSmith reads it via MCP or REST — production data is never changed in place.",
  },
  {
    title: "Agent analysis",
    body: "A sample is exported locally. Agents profile noise, map protected detections, and generate safe reduction policies.",
  },
  {
    title: "Candidate index",
    body: "Policies produce a reduced signalsmith_candidate index so you can compare volume side-by-side before any production rollout.",
  },
  {
    title: "Shadow validation",
    body: "Every saved search replays on baseline vs candidate. Optimization only proceeds when detections still fire and protected events are preserved.",
  },
];

export function DataExplainer({ compact }: DataExplainerProps) {
  return (
    <section className={`data-explainer ${compact ? "data-explainer--compact" : ""}`}>
      <header className="data-explainer__head">
        <div>
          <h2>How the data works</h2>
          <p>
            SignalSmith uses a safe shadow pipeline: read → analyze → compare → validate → approve.
            Charts and metrics only appear after live Splunk queries finish, so you always see a complete picture.
          </p>
        </div>
        {!compact && (
          <Link to="/data-flow" className="btn btn-secondary btn-sm">
            Full data flow
          </Link>
        )}
      </header>
      <div className="data-explainer__grid">
        {STEPS.map((step, i) => (
          <article key={step.title} className="data-explainer__step">
            <span className="data-explainer__num">{i + 1}</span>
            <div>
              <h3>{step.title}</h3>
              <p>{step.body}</p>
            </div>
          </article>
        ))}
      </div>
      <footer className="data-explainer__footer">
        <span className="data-badge data-badge--live">Live</span> Queried from Splunk now
        <span className="data-explainer__sep">·</span>
        <span className="data-badge data-badge--modeled">Modeled</span> Scaled from session totals when candidate index is empty
        <span className="data-explainer__sep">·</span>
        <Link to="/validation">Validation</Link> proves detections still work
      </footer>
    </section>
  );
}